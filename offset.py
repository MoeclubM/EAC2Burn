import os
import re
import wave

def frames_to_mmssff(frame_count: int, framerate: int) -> str:
    """将音频帧数转换为CUE文件的 MM:SS:FF 格式 (75 FF = 1秒)."""
    if framerate == 0 or frame_count < 0:
        return "00:00:00"
    total_seconds = frame_count / framerate
    minutes = int(total_seconds / 60)
    seconds = int(total_seconds % 60)
    frames = int(((total_seconds - minutes * 60 - seconds) * 75) + 0.5)
    
    if frames >= 75:
        seconds += 1
        frames -= 75
        if seconds >= 60:
            minutes += 1
            seconds -= 60
            
    return f"{minutes:02d}:{seconds:02d}:{frames:02d}"

def mmssff_to_frames(time_str: str, framerate: int) -> int:
    """将CUE文件的 MM:SS:FF 格式转换为音频帧数."""
    match = re.match(r'(\d+):(\d+):(\d+)', time_str)
    if not match:
        return 0
    minutes, seconds, frames = map(int, match.groups())
    total_seconds = minutes * 60 + seconds + frames / 75.0
    return int(total_seconds * framerate)

def apply_write_offset(cue_path: str, offset_samples: int):
    """
    对标准的CUE/WAV整轨文件进行预处理，以模拟写入偏移校正。
    """
    if not os.path.exists(cue_path):
        print(f"错误: CUE文件未找到 -> {cue_path}")
        return

    base_dir = os.path.dirname(cue_path)
    
    # --- 1. 解析原始CUE文件 ---
    print("步骤 1: 解析原始CUE文件...")
    with open(cue_path, 'r', encoding='utf-8-sig') as f:
        original_cue_lines = f.readlines()

    source_wav_filename = None
    for line in original_cue_lines:
        if line.strip().startswith("FILE"):
            match = re.search(r'FILE\s+"([^"]+)"', line)
            if match:
                source_wav_filename = match.group(1)
                break
    
    if not source_wav_filename:
        print("错误: 在CUE文件中未找到FILE指令。")
        return

    source_wav_path = os.path.join(base_dir, source_wav_filename)
    if not os.path.exists(source_wav_path):
        print(f"错误: 找不到源WAV文件 -> {source_wav_path}")
        return

    output_filename_base = os.path.splitext(source_wav_filename)[0]
    output_wav_path = os.path.join(base_dir, f"{output_filename_base}_offset_corrected.wav")
    output_cue_path = os.path.join(base_dir, f"{output_filename_base}_offset_corrected.cue")

    # --- 2. 处理WAV文件 ---
    print(f"步骤 2: 正在处理WAV文件以应用偏移 {offset_samples} 个采样点...")
    
    with wave.open(source_wav_path, 'rb') as source_wav:
        params = source_wav.getparams()
        frame_size = params.sampwidth * params.nchannels
        silence_frame = b'\x00' * frame_size

        with wave.open(output_wav_path, 'wb') as output_wav:
            output_wav.setparams(params)

            if offset_samples > 0:
                # 正偏移: 在文件开头添加静音
                print(f"  -> 正偏移: 在开头添加 {offset_samples} 帧静音...")
                for _ in range(offset_samples):
                    output_wav.writeframes(silence_frame)
                # 写入原始音频
                output_wav.writeframes(source_wav.readframes(params.nframes))

            elif offset_samples < 0:
                # 负偏移: 从文件开头删除采样
                trim_frames = abs(offset_samples)
                print(f"  -> 负偏移: 从开头删除 {trim_frames} 帧...")
                if trim_frames >= params.nframes:
                    print("错误: 偏移量大于文件总长度！")
                    return
                # 跳转到偏移后的位置
                source_wav.setpos(trim_frames)
                # 写入剩余的音频
                output_wav.writeframes(source_wav.readframes(params.nframes - trim_frames))
            
            else: # offset_samples == 0
                print("  -> 零偏移: 直接复制文件...")
                output_wav.writeframes(source_wav.readframes(params.nframes))

    print("WAV文件处理完成。")

    # --- 3. 生成新的、经过偏移校正的CUE文件 ---
    print(f"步骤 3: 正在生成经过偏移校正的新CUE文件...")
    
    with open(output_cue_path, 'w', encoding='utf-8') as f:
        for line in original_cue_lines:
            stripped_line = line.strip()
            if stripped_line.startswith("FILE"):
                # 替换为新的文件名
                f.write(f'FILE "{os.path.basename(output_wav_path)}" WAVE\n')
            elif stripped_line.startswith("INDEX"):
                # 校正时间戳
                match = re.search(r'(INDEX\s+\d+)\s+([0-9:]{8})', stripped_line)
                if match:
                    prefix, time_str = match.groups()
                    original_frames = mmssff_to_frames(time_str, params.framerate)
                    
                    # 应用偏移
                    corrected_frames = original_frames + offset_samples
                    # 确保时间戳不为负
                    corrected_frames = max(0, corrected_frames)
                    
                    new_time_str = frames_to_mmssff(corrected_frames, params.framerate)
                    indent = line[:len(line) - len(line.lstrip())] # 保留原始缩进
                    f.write(f'{indent}{prefix} {new_time_str}\n')
                else:
                    f.write(line)
            else:
                f.write(line)

    print("新的CUE文件生成完成。")
    print("\n处理成功！现在您可以使用新的 `_offset_corrected.cue` 文件进行刻录。")

# --- 如何使用 ---
if __name__ == '__main__':
    # ##################################################################
    # ##                                                              ##
    # ##  请在这里修改您的CUE文件路径和驱动器的写入偏移量               ##
    # ##                                                              ##
    # ##################################################################
    
    # 1. 指向您的标准CUE文件（整轨镜像）
    #    例如: "D:\\Rips\\My Album\\merged.cue"
    CUE_FILE_PATH = "burn_merged.cue"  # <--- 修改这里

    # 2. 填入您刻录机的写入偏移量（以采样点为单位）
    #    - 在网上搜索您驱动器型号的偏移量, 例如 "EAC drive database"。
    #    - 正数: 在音频前添加静音
    #    - 负数: 从音频前删除数据
    WRITE_OFFSET_SAMPLES = 667  # <--- 修改这里 (示例值)

    apply_write_offset(CUE_FILE_PATH, WRITE_OFFSET_SAMPLES)