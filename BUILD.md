# 构建 Windows 可执行程序
# Build Windows Executable

## 环境准备 (Prerequisites)

1. 安装 Python 3.8 或更高版本 (Install Python 3.8 or higher)
2. 安装依赖 (Install dependencies):
   ```bash
   pip install -r requirements.txt
   ```

## 构建方法 (Build Steps)

### 方法1: 使用 build_exe.bat (Windows)

双击运行 `build_exe.bat` 文件，或在命令行执行:
```cmd
build_exe.bat
```

### 方法2: 手动构建 (Manual Build)

在命令行执行以下命令 (Run the following command):

```bash
pyinstaller --onefile --windowed --name "PhotoOrganizer" organize_photos_gui.py
```

参数说明 (Parameters):
- `--onefile`: 打包为单个可执行文件 (Package as single executable)
- `--windowed`: 不显示命令行窗口 (No console window)
- `--name`: 可执行文件名称 (Executable name)

## 输出位置 (Output Location)

构建完成后，可执行文件位于:
After build, the executable is located at:
```
dist/PhotoOrganizer.exe
```

## 使用说明 (Usage)

1. 双击运行 `PhotoOrganizer.exe` (Double-click to run PhotoOrganizer.exe)
2. 选择源目录和目标目录 (Select source and destination directories)
3. 可选: 勾选"复制模式"保留原文件 (Optional: Check "Copy mode" to keep original files)
4. 点击"开始整理"按钮 (Click "Start" button)

## 功能特性 (Features)

- 支持图片格式: .jpg, .jpeg, .png (Supported image formats)
- 支持视频格式: .mp4, .mov, .avi (Supported video formats)
- 自动读取 EXIF 拍摄时间 (Auto-read EXIF shooting time)
- 按年/月/日目录结构整理 (Organize by Year/Month/Day structure)
- 自动去重 (基于文件大小和拍摄时间) (Auto deduplication)
- 自动重命名冲突文件 (Auto rename conflicting files)
