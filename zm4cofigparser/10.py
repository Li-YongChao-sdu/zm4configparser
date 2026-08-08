import struct
import zlib
import os
import re

# 1. 读取你的 cg1.swf 文件
with open("cg1.swf", "rb") as f:
    data = f.read()

# 2. 读取头部：前3字节是魔数(mo2)，接着2字节是块数量(251)
magic = data[0:3]
block_count = struct.unpack(">H", data[3:5])[0]
print(f"识别到格式: {magic.decode()}, 块数量: {block_count}")

# 3. 读取所有块的长度（目录）
offset = 5
lengths = []
for _ in range(block_count):
    size = struct.unpack(">I", data[offset:offset+4])[0]
    lengths.append(size)
    offset += 4

# 4. 创建输出文件夹
os.makedirs("output", exist_ok=True)

# 5. 开始逐个处理
for i, comp_len in enumerate(lengths):
    # 读取压缩的数据块
    comp_data = data[offset:offset+comp_len]
    offset += comp_len
    
    try:
        # 解压缩（注意：因为是无头zlib，用 -15 参数）
        decomp = zlib.decompress(comp_data, -15)
    except Exception as e:
        print(f"第 {i} 块解压失败: {e}")
        continue
    
    # 解析解压后的数据结构
    pos = 0
    # 2字节：文件名长度
    name_len = struct.unpack(">H", decomp[pos:pos+2])[0]
    pos += 2
    # 读取原始文件名（UTF-8编码）
    raw_name = decomp[pos:pos+name_len].decode("utf-8", errors="ignore")
    pos += name_len
    # 2字节：标志位（1表示AMF对象，其他表示文本/二进制）
    flag = struct.unpack(">H", decomp[pos:pos+2])[0]
    pos += 2
    # 剩余的实际数据
    content = decomp[pos:]
    
    # 处理文件名：去掉路径符号，防止系统报错
    safe_name = raw_name.replace("/", "_").replace("\\", "_")
    safe_name = re.sub(r'[\\/*?:"<>|\x00-\x1f]', '_', safe_name)
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', safe_name)

    if not safe_name:
        safe_name = f"block_{i:03d}"
    
    # 根据数据类型决定保存后缀
    if flag == 1:
        ext = ".amf"  # 特殊配置对象，先存二进制
    else:
        # 尝试检测是否为常见图片/音频格式，自动添加后缀
        if content.startswith(b'\xFF\xD8\xFF'):
            ext = ".jpg"
        elif content.startswith(b'\x89PNG'):
            ext = ".png"
        elif content.startswith(b'<') or content.startswith(b'{'):
            ext = ".txt"
        else:
            ext = ".bin"
    
    # 写入文件
    with open(f"output/{i:03d}_{safe_name}{ext}", "wb") as out:
        out.write(content)
    
    print(f"✅ 解出: {i:03d}_{safe_name}{ext} (原始大小: {len(content)} 字节)")

print(f"\n🎉 全部完成！文件已解压到 output 文件夹")