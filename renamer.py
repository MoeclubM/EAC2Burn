import os
import shutil
import re

# 定义目标目录 burn 在当前目录的上级目录下
burn_dir = os.path.abspath(os.path.join(os.getcwd(), '..', 'burn'))
os.makedirs(burn_dir, exist_ok=True)

# 获取当前目录下所有的 .wav 文件，按自然顺序排序
wav_files = sorted([f for f in os.listdir('.') if f.lower().endswith('.wav') and re.match(r'^\d{2}\..*\.wav$', f)])

# 创建原始文件名到新文件名的映射字典
mapping = {}

# 遍历排序后的 wav 文件并复制重命名到 burn 目录
for idx, filename in enumerate(wav_files, start=1):
    # 生成新的文件名，例如 01.wav, 02.wav ...
    new_name = f"{idx:02d}.wav"
    # 构建目标文件路径
    dst_path = os.path.join(burn_dir, new_name)
    # 复制文件到 burn 并重命名
    shutil.copy2(filename, dst_path)
    # 记录原文件名与新文件名的对应关系
    mapping[filename] = new_name

# 查找当前目录下的第一个 .cue 文件
cue_file = next((f for f in os.listdir('.') if f.lower().endswith('.cue')), None)

# 如果找到了 cue 文件
if cue_file:
    cue_content = None
    cue_encoding = None
    # 尝试多种编码读取 cue 文件内容
    for encoding in ['utf-8', 'shift_jis', 'gbk', 'latin1']:
        try:
            with open(cue_file, 'r', encoding=encoding) as f:
                cue_content = f.read()
            cue_encoding = encoding
            print(f"成功使用编码 {encoding} 读取 CUE 文件")
            break
        except UnicodeDecodeError:
            continue

    if cue_content is None:
        raise UnicodeDecodeError("无法识别 CUE 文件的编码格式，请手动检查文件编码。")

    # 清除 FILE 行中路径，仅保留文件名
    cue_content = re.sub(r'(?i)(FILE\s+")[^"/\\]*[\\/]([^"\\/]+)(")', r'\1\2\3', cue_content)

    # 替换 cue 文件中引用的 wav 文件名
    for original, new in mapping.items():
        original_basename = os.path.basename(original)
        cue_content = cue_content.replace(original_basename, new)

    # 修改后的 cue 文件保存为 burn.cue，使用原编码
    cue_dst_path = os.path.join(burn_dir, 'burn.cue')
    with open(cue_dst_path, 'w', encoding=cue_encoding) as f:
        f.write(cue_content)

    print(f"已复制并更新 CUE 文件: {cue_file} -> {cue_dst_path}")
else:
    print("未找到 .cue 文件，跳过该步骤。")

# 输出完成信息
print(f"完成：已将 {len(mapping)} 个 WAV 文件复制到 '{burn_dir}' 并重命名。")
