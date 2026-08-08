import os
import json
import xml.etree.ElementTree as ET

# 输出目录（就是你刚才解压出来那个文件夹）
OUTPUT_DIR = "output"

def xml_to_dict(element):
    """把 XML 节点转成 Python 字典（处理 Flash 特有的属性结构）"""
    # 1. 先拿属性
    data = dict(element.attrib)
    
    # 2. 如果有文本内容，单独存为 "#text"
    if element.text and element.text.strip():
        data["#text"] = element.text.strip()
    
    # 3. 递归处理子节点
    children = {}
    for child in element:
        child_data = xml_to_dict(child)
        tag = child.tag
        
        # 如果同一个标签出现多次，合并成数组
        if tag in children:
            if not isinstance(children[tag], list):
                children[tag] = [children[tag]]
            children[tag].append(child_data)
        else:
            children[tag] = child_data
    
    # 把子节点合并到数据里
    if children:
        data.update(children)
    
    # 如果只有一个文本内容且没有属性和子节点，直接返回文本
    if len(data) == 1 and "#text" in data:
        return data["#text"]
    
    return data

# 开始遍历 output 文件夹
for filename in os.listdir(OUTPUT_DIR):
    if not filename.endswith(".txt"):
        continue
    
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    # 读取文件内容
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read().strip()
    
    # 只处理看起来像 XML 的文件（开头是 <）
    if not content.startswith("<"):
        continue
    
    try:
        # 解析 XML
        root = ET.fromstring(content)
        # 转成 JSON 结构
        json_data = xml_to_dict(root)
        
        # 保存为 JSON 文件（覆盖同名 .json）
        json_path = filepath.replace(".txt", ".json")
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(json_data, jf, indent=2, ensure_ascii=False)
        
        print(f"✅ 转换成功: {filename} -> {os.path.basename(json_path)}")
    except Exception as e:
        print(f"❌ 转换失败: {filename} (错误: {e})")

print("\n🎉 全部转换完成！去 output 文件夹看 .json 文件吧。")