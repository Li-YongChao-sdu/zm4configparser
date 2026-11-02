# -*- coding: utf-8 -*-
"""
造梦西游4 配置文件解包工具（改进版）
一键完成：SWF块解压 → XML导出 → JSON转换

用法:
    python zm4_config_unpack.py <swf路径> [输出目录]

示例:
    python zm4_config_unpack.py cg1_20260921_1_2.swf
    python zm4_config_unpack.py cg1.swf output_v583
"""
import struct
import zlib
import os
import sys
import re
import json
import xml.etree.ElementTree as ET


def parse_swf_blocks(swf_path):
    """解析SWF配置文件，返回解压后的块列表"""
    with open(swf_path, "rb") as f:
        data = f.read()

    # 头部：3字节魔数(mo2) + 2字节块数量(大端)
    magic = data[0:3]
    block_count = struct.unpack(">H", data[3:5])[0]
    print(f"格式: {magic.decode('ascii', errors='replace')}, 块数量: {block_count}")

    # 块长度表（大端，每个4字节）
    offset = 5
    lengths = []
    for _ in range(block_count):
        size = struct.unpack(">I", data[offset:offset+4])[0]
        lengths.append(size)
        offset += 4

    # 逐个解压
    blocks = []
    for i, comp_len in enumerate(lengths):
        comp_data = data[offset:offset+comp_len]
        offset += comp_len

        try:
            # 无头zlib解压
            decomp = zlib.decompress(comp_data, -15)
        except Exception as e:
            print(f"  块 {i:03d} 解压失败: {e}")
            blocks.append(None)
            continue

        # 解析块内结构：2字节文件名长度 + 文件名 + 2字节标志位 + 数据
        pos = 0
        name_len = struct.unpack(">H", decomp[pos:pos+2])[0]
        pos += 2
        raw_name = decomp[pos:pos+name_len].decode("utf-8", errors="ignore")
        pos += name_len
        flag = struct.unpack(">H", decomp[pos:pos+2])[0]
        pos += 2
        content = decomp[pos:]

        blocks.append({
            "index": i,
            "name": raw_name,
            "flag": flag,
            "content": content,
        })

    return blocks


def safe_filename(name, index):
    """生成安全的文件名"""
    safe = name.replace("/", "_").replace("\\", "_")
    safe = re.sub(r'[\\/*?:"<>|\x00-\x1f]', '_', safe)
    if not safe:
        safe = f"block_{index:03d}"
    return safe


def detect_extension(content, flag):
    """根据内容检测文件扩展名"""
    if flag == 1:
        return ".amf"  # AMF二进制对象
    if content.startswith(b'\xFF\xD8\xFF'):
        return ".jpg"
    elif content.startswith(b'\x89PNG'):
        return ".png"
    elif content[:1] in (b'<', b'{'):
        return ".txt"
    else:
        return ".bin"


def xml_to_dict(element):
    """XML节点转字典"""
    data = dict(element.attrib)
    if element.text and element.text.strip():
        data["#text"] = element.text.strip()

    children = {}
    for child in element:
        child_data = xml_to_dict(child)
        tag = child.tag
        if tag in children:
            if not isinstance(children[tag], list):
                children[tag] = [children[tag]]
            children[tag].append(child_data)
        else:
            children[tag] = child_data

    if children:
        data.update(children)

    if len(data) == 1 and "#text" in data:
        return data["#text"]
    return data


def sanitize_xml_tags(content):
    """预处理XML：把数字开头的标签名加下划线前缀（标准XML不允许数字开头标签）"""
    # 匹配 <123> 或 </123> 或 <123 ...>
    content = re.sub(r'<(/?)(\d)', r'<\1_\2', content)
    return content


def convert_txt_to_json(output_dir):
    """把output目录里的txt XML文件转成JSON"""
    converted = 0
    failed = 0
    for filename in sorted(os.listdir(output_dir)):
        if not filename.endswith(".txt"):
            continue

        filepath = os.path.join(output_dir, filename)
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read().strip()

        if not content.startswith("<"):
            continue

        try:
            # 预处理数字开头的标签
            content = sanitize_xml_tags(content)
            root = ET.fromstring(content)
            json_data = xml_to_dict(root)
            json_path = filepath.replace(".txt", ".json")
            with open(json_path, "w", encoding="utf-8") as jf:
                json.dump(json_data, jf, indent=2, ensure_ascii=False)
            converted += 1
        except Exception as e:
            print(f"  JSON转换失败: {filename} ({e})")
            failed += 1

    return converted, failed


def main():
    if len(sys.argv) < 2:
        print("用法: python zm4_config_unpack.py <swf路径> [输出目录]")
        print("示例: python zm4_config_unpack.py cg1_20260921_1_2.swf")
        sys.exit(1)

    swf_path = sys.argv[1]
    if not os.path.exists(swf_path):
        print(f"错误: 文件不存在 {swf_path}")
        sys.exit(1)

    # 输出目录：默认用SWF文件名（不带扩展名）
    if len(sys.argv) >= 3:
        output_dir = sys.argv[2]
    else:
        base = os.path.splitext(os.path.basename(swf_path))[0]
        output_dir = f"output_{base}"

    print(f"输入: {swf_path}")
    print(f"输出: {output_dir}")
    print("=" * 50)

    # 第一步：解析并解压块
    print("\n[1/3] 解析SWF块...")
    blocks = parse_swf_blocks(swf_path)
    valid_blocks = [b for b in blocks if b is not None]
    print(f"  成功解压 {len(valid_blocks)}/{len(blocks)} 个块")

    # 第二步：导出文件
    print(f"\n[2/3] 导出文件到 {output_dir}/ ...")
    os.makedirs(output_dir, exist_ok=True)

    type_count = {}
    for b in valid_blocks:
        safe_name = safe_filename(b["name"], b["index"])
        ext = detect_extension(b["content"], b["flag"])
        out_name = f"{b['index']:03d}_{safe_name}{ext}"
        out_path = os.path.join(output_dir, out_name)

        with open(out_path, "wb") as f:
            f.write(b["content"])

        type_count[ext] = type_count.get(ext, 0) + 1

    for ext, cnt in sorted(type_count.items()):
        print(f"  {ext}: {cnt} 个")

    # 第三步：XML转JSON
    print(f"\n[3/3] XML转JSON...")
    converted, failed = convert_txt_to_json(output_dir)
    print(f"  成功: {converted}, 失败: {failed}")

    print("\n" + "=" * 50)
    print(f"完成！输出目录: {os.path.abspath(output_dir)}")
    print(f"  - 原始文件: {len(valid_blocks)} 个")
    print(f"  - JSON文件: {converted} 个")
    if failed:
        print(f"  - 转换失败: {failed} 个（保留原始txt）")


if __name__ == "__main__":
    main()
