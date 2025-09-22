# EAC2Burn

一套用于辅助完美刻录 EAC 抓轨音轨的 Python 脚本合集。

---

## 脚本说明

### **1. `renamer.py` - 文件及CUE重命名工具**

此脚本用于标准化 EAC 分轨抓取（Track-Based Rips）的 `WAV` 文件名和 `.cue` 文件中的轨道信息。

**使用方法:**
1.  将 `renamer.py` 脚本复制到包含 EAC 抓取的分轨 `WAV` 文件和 `.cue` 文件的目录中。
2.  运行此脚本。
3.  脚本会自动处理文件，并将标准化后的 `WAV` 文件及 `.cue` 文件输出到上一级的 `burn` 文件夹内 (`../burn`)。
在抓取轨道前，您可以使用 [Music Hoarders Log Checker](https://logs.musichoarders.xyz/) 等工具为您的 EAC 抓取日志（log 文件）进行评分。这可以帮助您判断抓取设置是否理想，以免刻录错误抓取的内容。请注意，满分日志不绝对代表完美抓取，反之亦然。另外也可以使用cuetools将本地文件与在线数据库进行比对判断是否完整。

---

### **2. `eaccueconverter.py` - 非标准 CUE 转换工具**

此脚本的功能是将 EAC 生成的非标准、带间隙（Gaps Appended）分轨 CUE 文件转换为可直接用于刻录的标准 CUE 文件。该脚本的功能与 [CUETools](http://cue.tools/wiki/CUETools) 类似。经测试，其与 CUETools 的输出结果一致，因此您也可以选择使用 CUETools 作为替代方案。

**使用方法:**
1.  首先使用 `renamer.py` 脚本生成 `burn` 文件夹。
2.  在 `burn` 文件夹内直接运行 `eaccueconverter.py` 脚本。
3.  脚本会生成标准的 `.cue` 文件。

---

### **3. `offset.py` - 写入偏移量手动校正工具**

此脚本用于为 `WAV` 文件和 `.cue` 文件手动添加写入偏移量（Write Offset），用于不支持设置写入采样偏移的刻录软件。

**注意:**
此脚本未经实际测试，请谨慎使用（手动偏移裁剪会丢失部分数据，因此尽量使用无写入偏移的光驱）

---

### **4. `eaclogfix.py` - EAC 日志修复与重签名工具**

此脚本源自 [puddly/eac_logsigner](https://github.com/puddly/eac_logsigner) 如果您在抓取轨道时不慎将个人信息（如文件路径）记录到了 log 文件中，又不想花费时间重新抓取，可以使用此工具。

**功能:**
它允许您在手动编辑并移除 log 文件中的个人信息后，重新为该 log 文件生成有效的签名（checksum）。经过此脚本处理后的 log 文件，依然可以在 log 检测网站上通过验证并获得高分。这也从侧面说明，log 文件的评分仅作为参考，并非绝对标准。
