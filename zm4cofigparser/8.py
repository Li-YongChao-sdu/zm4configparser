import struct
import zlib
import lzma
import os

def analyze_block(data):
    """检测块是否可识别"""
    if len(data) < 4:
        return "太短"
    if data[:2] == b'\x78\x9C':
        try:
            zlib.decompress(data)
            return "zlib压缩"
        except:
            return "zlib头但解压失败"
    if data[:2] == b'\x5D\x00':
        try:
            lzma.decompress(data)
            return "LZMA压缩"
        except:
            return "LZMA头但解压失败"
    if data[:3] in (b'FWS', b'CWS'):
        return "SWF文件"
    if data[:2] == b'\x0A\x0B':
        return "AMF3对象"
    # 尝试异或解密检测
    for key in range(256):
        if len(data) > 2:
            test = bytes([b ^ key for b in data[:2]])
            if test == b'\x78\x9C':
                return f"可能是XOR加密，密钥0x{key:02X}"
    return "未知"

def extract_all_blocks(file_path):
    with open(file_path, 'rb') as f:
        data = f.read()

    # 1. 块数量
    block_count = data[0x04]
    print(f"块数量: {block_count}")

    # 2. 块大小表（大端序，从0x05开始）
    sizes = []
    for i in range(block_count):
        offset = 0x05 + i*4
        size = struct.unpack('>I', data[offset:offset+4])[0]
        sizes.append(size)

    # 3. 提取每个块
    os.makedirs('blocks', exist_ok=True)
    data_start = 0x05 + block_count*4
    total_extracted = 0

    for idx, size in enumerate(sizes):
        start = data_start + total_extracted
        block_data = data[start:start+size]
        total_extracted += size

        # 保存原始块
        with open(f'blocks/block_{idx:03d}.bin', 'wb') as f:
            f.write(block_data)

        # 分析
        info = analyze_block(block_data)
        print(f"块 {idx:03d}: 大小 {size:6d} 字节, 开头 {block_data[:4].hex()}, 推测: {info}")

    print(f"\n总提取: {total_extracted} 字节, 文件剩余: {len(data) - data_start} 字节")
    if total_extracted == len(data) - data_start:
        print("✅ 所有块提取完毕，大小匹配！")
    else:
        print("⚠️ 大小不匹配，请检查")

if __name__ == '__main__':
    extract_all_blocks('cg1.swf')