@echo off
echo ================================
echo 照片整理工具 - 构建可执行程序
echo Photo Organizer - Build Executable
echo ================================
echo.

echo 正在安装依赖... (Installing dependencies...)
pip install -r requirements.txt
if errorlevel 1 (
    echo 安装依赖失败 (Failed to install dependencies)
    pause
    exit /b 1
)

echo.
echo 正在构建可执行程序... (Building executable...)
pyinstaller --onefile --windowed --name "PhotoOrganizer" organize_photos_gui.py
if errorlevel 1 (
    echo 构建失败 (Build failed)
    pause
    exit /b 1
)

echo.
echo ================================
echo 构建成功! (Build successful!)
echo 可执行文件位于: dist\PhotoOrganizer.exe
echo Executable is at: dist\PhotoOrganizer.exe
echo ================================
pause
