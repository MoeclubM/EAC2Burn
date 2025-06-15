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

def process_eac_cue(cue_path: str):
    """
    处理EAC非标准CUE文件，自动检测编码，合并WAV并生成新CUE.
    """
    if not os.path.exists(cue_path):
        print(f"错误: CUE文件未找到 -> {cue_path}")
        return

    print("步骤 1: 自动检测文件编码并解析CUE文件...")
    encodings_to_try = ['utf-8-sig', 'shift_jis', 'gbk']
    file_content_lines = None
    detected_encoding = None

    for encoding in encodings_to_try:
        try:
            with open(cue_path, 'r', encoding=encoding) as f:
                file_content_lines = f.readlines()
            detected_encoding = encoding
            print(f"  -> 编码检测成功: {detected_encoding}")
            break 
        except UnicodeDecodeError:
            print(f"  -> 尝试 {encoding} 编码失败...")
            continue
        except Exception as e:
            print(f"读取文件时发生意外错误: {e}")
            return
    
    if file_content_lines is None:
        print("错误: 尝试了所有常用编码，都无法正确读取CUE文件。")
        return

    base_dir = os.path.dirname(cue_path)
    output_filename_base = os.path.splitext(os.path.basename(cue_path))[0]
    output_wav_path = os.path.join(base_dir, f"{output_filename_base}_merged.wav")
    output_cue_path = os.path.join(base_dir, f"{output_filename_base}_merged.cue")
    
    global_metadata = {"REM": [], "CATALOG": "", "PERFORMER": "", "TITLE": ""}
    tracks = []
    file_sequence = []
    
    current_track = None
    current_file = None
    for line in file_content_lines:
        line = line.strip()
        
        if current_track is None:
            if line.startswith("REM"): global_metadata["REM"].append(line)
            elif line.startswith("CATALOG"): global_metadata["CATALOG"] = line
            elif line.startswith("PERFORMER"): global_metadata["PERFORMER"] = line
            elif line.startswith("TITLE"): global_metadata["TITLE"] = line
        
        if line.startswith("FILE"):
            match = re.search(r'FILE\s+"([^"]+)"', line)
            if match:
                current_file = match.group(1)
                if current_file not in file_sequence:
                    file_sequence.append(current_file)

        elif line.startswith("TRACK"):
            match = re.search(r'TRACK\s+(\d+)', line)
            if match:
                if current_track: tracks.append(current_track)
                # <--- 修复 1: 初始化时增加isrc和rem_lines字段 ---
                current_track = {"number": match.group(1), "indices": [], "title": "", "performer": "", "isrc": "", "rem_lines": []}

        elif line.startswith("TITLE") and current_track is not None:
            match = re.search(r'TITLE\s+"([^"]+)"', line)
            if match: current_track["title"] = match.group(1)

        elif line.startswith("PERFORMER") and current_track is not None:
             match = re.search(r'PERFORMER\s+"([^"]+)"', line)
             if match: current_track["performer"] = match.group(1)

        # <--- 修复 2: 增加对ISRC码的解析 ---
        elif line.startswith("ISRC") and current_track is not None:
            match = re.search(r'ISRC\s+([A-Z0-9]+)', line)
            if match: current_track["isrc"] = match.group(1)

        # <--- 修复 3: 增加对轨道内REM注释的解析 ---
        elif line.startswith("REM") and current_track is not None:
            current_track["rem_lines"].append(line)

        elif line.startswith("INDEX") and current_track is not None:
            match = re.search(r'INDEX\s+(\d+)\s+([0-9:]{8})', line)
            if match:
                index_num, time_str = match.groups()
                current_track["indices"].append({ "number": index_num, "time": time_str, "source_file": current_file })

    if current_track: tracks.append(current_track)
        
    print(f"解析完成: 找到 {len(file_sequence)} 个WAV文件和 {len(tracks)} 个轨道。")

    print(f"\n步骤 2: 正在合并 {len(file_sequence)} 个WAV文件为 -> {os.path.basename(output_wav_path)}")
    
    first_wav_path = os.path.join(base_dir, file_sequence[0])
    if not os.path.exists(first_wav_path):
        print(f"错误：找不到第一个WAV文件 -> {first_wav_path}")
        return
        
    with wave.open(first_wav_path, 'rb') as first_wav:
        params = first_wav.getparams()
    
    with wave.open(output_wav_path, 'wb') as output_wav:
        output_wav.setparams(params)
        for filename in file_sequence:
            filepath = os.path.join(base_dir, filename)
            print(f"  -> 正在追加: {filename}")
            try:
                with wave.open(filepath, 'rb') as input_wav:
                    if (input_wav.getnchannels() != params.nchannels or 
                        input_wav.getsampwidth() != params.sampwidth or 
                        input_wav.getframerate() != params.framerate):
                        print(f"警告: 文件 {filename} 的核心音频参数与第一个文件不一致，可能导致问题。")
                    output_wav.writeframes(input_wav.readframes(input_wav.getnframes()))
            except FileNotFoundError:
                print(f"错误: 找不到文件 {filepath}，跳过。")
    
    print("WAV文件合并完成。")

    print(f"\n步骤 3: 正在生成新的标准CUE文件 -> {os.path.basename(output_cue_path)}")
    
    framerate = params.framerate
    file_offsets_in_frames = {}
    running_total_frames = 0
    
    for filename in file_sequence:
        file_offsets_in_frames[filename] = running_total_frames
        filepath = os.path.join(base_dir, filename)
        try:
            with wave.open(filepath, 'rb') as wav:
                running_total_frames += wav.getnframes()
        except FileNotFoundError: pass

    with open(output_cue_path, 'w', encoding='utf-8') as f:
        if global_metadata["REM"]: [f.write(rem + '\n') for rem in global_metadata["REM"]]
        if global_metadata["CATALOG"]: f.write(global_metadata["CATALOG"] + '\n')
        if global_metadata["PERFORMER"]: f.write(global_metadata["PERFORMER"] + '\n')
        if global_metadata["TITLE"]: f.write(global_metadata["TITLE"] + '\n')
            
        f.write(f'FILE "{os.path.basename(output_wav_path)}" WAVE\n')

        for track in tracks:
            f.write(f'  TRACK {int(track["number"]):02d} AUDIO\n')
            if track["title"]: f.write(f'    TITLE "{track["title"]}"\n')
            if track["performer"]: f.write(f'    PERFORMER "{track["performer"]}"\n')
            
            # <--- 修复 4: 补上写入轨道内REM和ISRC的逻辑 ---
            if track["rem_lines"]: [f.write(f'    {rem_line}\n') for rem_line in track["rem_lines"]]
            if track["isrc"]: f.write(f'    ISRC {track["isrc"]}\n')

            for index in track["indices"]:
                source_file = index["source_file"]
                time_in_source_file_frames = mmssff_to_frames(index["time"], framerate)
                absolute_frames = file_offsets_in_frames.get(source_file, 0) + time_in_source_file_frames
                new_time_str = frames_to_mmssff(absolute_frames, framerate)
                f.write(f'    INDEX {index["number"]} {new_time_str}\n')
    
    print("新的CUE文件生成完成。")
    print("\n处理成功！")

if __name__ == '__main__':
    cue_file_path = "burn.cue"
    process_eac_cue(cue_file_path)