#!/usr/bin/env python3
"""
Photo and Video Organizer - GUI Version

A graphical interface to manage and organize a large collection of photos and videos.
It scans a source directory, extracts shooting dates, deduplicates based on
file size and timestamp, and organizes files into a Year/Month/Day structure.
"""

import os
import shutil
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from PIL import Image

# Supported file extensions
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi'}
SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS


def get_exif_date(filepath):
    """
    Extract DateTimeOriginal from image EXIF data.
    
    Args:
        filepath: Path to the image file
        
    Returns:
        datetime object if found, None otherwise
    """
    # DateTimeOriginal tag ID
    DATE_TIME_ORIGINAL = 36867
    # Exif IFD tag ID
    EXIF_IFD = 34665
    
    try:
        with Image.open(filepath) as img:
            exif_data = img.getexif()
            if exif_data:
                # Try to get DateTimeOriginal from Exif IFD
                exif_ifd = exif_data.get_ifd(EXIF_IFD)
                if exif_ifd and DATE_TIME_ORIGINAL in exif_ifd:
                    value = exif_ifd[DATE_TIME_ORIGINAL]
                    # EXIF date format: "YYYY:MM:DD HH:MM:SS"
                    return datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
                
                # Fallback: check main EXIF data
                if DATE_TIME_ORIGINAL in exif_data:
                    value = exif_data[DATE_TIME_ORIGINAL]
                    return datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
    except Exception:
        pass
    return None


def get_file_modification_time(filepath):
    """
    Get file modification time as datetime.
    
    Args:
        filepath: Path to the file
        
    Returns:
        datetime object of file modification time
    """
    mtime = os.path.getmtime(filepath)
    return datetime.fromtimestamp(mtime)


def get_shooting_time(filepath):
    """
    Determine the shooting time for a file.
    
    For images: Try EXIF DateTimeOriginal first, fallback to modification time.
    For videos: Use file modification time.
    
    Args:
        filepath: Path to the file
        
    Returns:
        datetime object representing the shooting time
    """
    ext = Path(filepath).suffix.lower()
    
    if ext in IMAGE_EXTENSIONS:
        exif_date = get_exif_date(filepath)
        if exif_date:
            return exif_date
    
    return get_file_modification_time(filepath)


def get_file_size(filepath):
    """
    Get file size in bytes.
    
    Args:
        filepath: Path to the file
        
    Returns:
        File size in bytes
    """
    return os.path.getsize(filepath)


def scan_directory(source_dir):
    """
    Recursively scan a directory for supported image and video files.
    
    Args:
        source_dir: Path to the source directory
        
    Yields:
        Path objects for each supported file found
    """
    source_path = Path(source_dir)
    for filepath in source_path.rglob('*'):
        if filepath.is_file() and filepath.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield filepath


def generate_unique_filename(dest_path):
    """
    Generate a unique filename if the destination already exists.
    
    Appends _1, _2, etc. to the filename until a unique name is found.
    
    Args:
        dest_path: Original destination path
        
    Returns:
        Path object with unique filename
    """
    if not dest_path.exists():
        return dest_path
    
    stem = dest_path.stem
    suffix = dest_path.suffix
    parent = dest_path.parent
    
    counter = 1
    while True:
        new_name = f"{stem}_{counter}{suffix}"
        new_path = parent / new_name
        if not new_path.exists():
            return new_path
        counter += 1


class PhotoOrganizerGUI:
    """GUI class for the Photo Organizer application."""
    
    def __init__(self, root):
        """Initialize the GUI."""
        self.root = root
        self.root.title("照片视频整理工具 - Photo Organizer")
        self.root.geometry("700x550")
        self.root.minsize(600, 450)
        
        # Variables
        self.src_var = tk.StringVar()
        self.dest_var = tk.StringVar()
        self.copy_mode_var = tk.BooleanVar(value=False)
        self.is_running = False
        
        self._create_widgets()
        
    def _create_widgets(self):
        """Create all GUI widgets."""
        # Main frame with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        # Title
        title_label = ttk.Label(
            main_frame, 
            text="照片视频整理工具", 
            font=("Arial", 16, "bold")
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 15))
        
        # Source directory
        ttk.Label(main_frame, text="源目录 (Source):").grid(
            row=1, column=0, sticky="w", pady=5
        )
        src_entry = ttk.Entry(main_frame, textvariable=self.src_var, width=50)
        src_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(
            main_frame, text="浏览...", command=self._browse_src
        ).grid(row=1, column=2, pady=5)
        
        # Destination directory
        ttk.Label(main_frame, text="目标目录 (Dest):").grid(
            row=2, column=0, sticky="w", pady=5
        )
        dest_entry = ttk.Entry(main_frame, textvariable=self.dest_var, width=50)
        dest_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(
            main_frame, text="浏览...", command=self._browse_dest
        ).grid(row=2, column=2, pady=5)
        
        # Options frame
        options_frame = ttk.LabelFrame(main_frame, text="选项 (Options)", padding="5")
        options_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=10)
        
        ttk.Checkbutton(
            options_frame, 
            text="复制模式 (保留原文件) / Copy mode (keep original files)",
            variable=self.copy_mode_var
        ).pack(anchor="w")
        
        # Progress and log area
        log_frame = ttk.LabelFrame(main_frame, text="日志 (Log)", padding="5")
        log_frame.grid(row=4, column=0, columnspan=3, sticky="nsew", pady=10)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=15, width=70, state='disabled'
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            main_frame, variable=self.progress_var, maximum=100
        )
        self.progress_bar.grid(row=5, column=0, columnspan=3, sticky="ew", pady=5)
        
        # Status label
        self.status_var = tk.StringVar(value="就绪 (Ready)")
        status_label = ttk.Label(main_frame, textvariable=self.status_var)
        status_label.grid(row=6, column=0, columnspan=2, sticky="w")
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=7, column=0, columnspan=3, pady=10)
        
        self.start_btn = ttk.Button(
            buttons_frame, text="开始整理 (Start)", command=self._start_organizing
        )
        self.start_btn.pack(side="left", padx=5)
        
        ttk.Button(
            buttons_frame, text="清除日志 (Clear Log)", command=self._clear_log
        ).pack(side="left", padx=5)
        
        ttk.Button(
            buttons_frame, text="退出 (Exit)", command=self.root.quit
        ).pack(side="left", padx=5)
        
    def _browse_src(self):
        """Open dialog to select source directory."""
        directory = filedialog.askdirectory(title="选择源目录 (Select Source Directory)")
        if directory:
            self.src_var.set(directory)
            
    def _browse_dest(self):
        """Open dialog to select destination directory."""
        directory = filedialog.askdirectory(title="选择目标目录 (Select Destination Directory)")
        if directory:
            self.dest_var.set(directory)
            
    def _log(self, message):
        """Add message to log area."""
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        
    def _clear_log(self):
        """Clear the log area."""
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')
        
    def _start_organizing(self):
        """Start the organizing process in a separate thread."""
        src = self.src_var.get().strip()
        dest = self.dest_var.get().strip()
        
        # Validate inputs
        if not src:
            messagebox.showerror("错误 (Error)", "请选择源目录 (Please select source directory)")
            return
        if not dest:
            messagebox.showerror("错误 (Error)", "请选择目标目录 (Please select destination directory)")
            return
        if not os.path.isdir(src):
            messagebox.showerror("错误 (Error)", f"源目录不存在 (Source directory does not exist): {src}")
            return
            
        if self.is_running:
            messagebox.showwarning("警告 (Warning)", "任务正在进行中 (Task is already running)")
            return
            
        # Start organizing in background thread
        self.is_running = True
        self.start_btn.config(state='disabled')
        self.progress_var.set(0)
        self._clear_log()
        
        thread = threading.Thread(
            target=self._organize_thread,
            args=(src, dest, self.copy_mode_var.get())
        )
        thread.daemon = False  # Allow thread to complete before exit
        thread.start()
        
    def _organize_thread(self, src, dest, copy_mode):
        """Background thread for organizing photos."""
        try:
            source_dir = Path(src)
            dest_dir = Path(dest)
            
            # Track processed files by (size, timestamp) for deduplication
            processed_files = set()
            
            # Statistics
            stats = {
                'processed': 0,
                'skipped_duplicate': 0,
                'moved': 0,
                'copied': 0,
                'renamed': 0,
                'errors': 0
            }
            
            self._update_status("正在扫描文件... (Scanning files...)")
            self._log(f"源目录: {source_dir}")
            self._log(f"目标目录: {dest_dir}")
            self._log(f"模式: {'复制 (Copy)' if copy_mode else '移动 (Move)'}")
            self._log("-" * 50)
            
            # First, count total files for progress
            all_files = list(scan_directory(source_dir))
            total_files = len(all_files)
            
            if total_files == 0:
                self._log("未找到支持的文件 (No supported files found)")
                self._update_status("完成 (Done) - 未找到文件")
                return
                
            self._log(f"找到 {total_files} 个文件 (Found {total_files} files)")
            self._log("-" * 50)
            
            for i, filepath in enumerate(all_files):
                stats['processed'] += 1
                progress = (i + 1) / total_files * 100
                self._update_progress(progress)
                self._update_status(f"处理中: {i+1}/{total_files}")
                
                try:
                    # Get file info for deduplication
                    file_size = get_file_size(filepath)
                    shooting_time = get_shooting_time(filepath)
                    
                    # Create deduplication key
                    dedup_key = (file_size, shooting_time)
                    
                    # Check for duplicates
                    if dedup_key in processed_files:
                        self._log(f"跳过重复文件 (Skip duplicate): {filepath.name}")
                        stats['skipped_duplicate'] += 1
                        continue
                    
                    # Mark as processed
                    processed_files.add(dedup_key)
                    
                    # Create destination path: {dest}/{Year}/{Month}/{Day}/{filename}
                    year = str(shooting_time.year)
                    month = f"{shooting_time.month:02d}"
                    day = f"{shooting_time.day:02d}"
                    
                    dest_folder = dest_dir / year / month / day
                    dest_folder.mkdir(parents=True, exist_ok=True)
                    
                    dest_path = dest_folder / filepath.name
                    
                    # Handle filename collision
                    original_dest = dest_path
                    dest_path = generate_unique_filename(dest_path)
                    
                    if dest_path != original_dest:
                        stats['renamed'] += 1
                        self._log(f"重命名 (Renamed): {filepath.name} -> {dest_path.name}")
                    
                    # Move or copy the file
                    if copy_mode:
                        shutil.copy2(filepath, dest_path)
                        stats['copied'] += 1
                        self._log(f"复制 (Copied): {filepath.name} -> {dest_path.relative_to(dest_dir)}")
                    else:
                        shutil.move(filepath, dest_path)
                        stats['moved'] += 1
                        self._log(f"移动 (Moved): {filepath.name} -> {dest_path.relative_to(dest_dir)}")
                        
                except Exception as e:
                    self._log(f"错误 (Error) {filepath.name}: {e}")
                    stats['errors'] += 1
            
            # Print summary
            self._log("-" * 50)
            self._log("完成! 统计信息 (Done! Summary):")
            self._log(f"  处理文件总数 (Total processed): {stats['processed']}")
            self._log(f"  {'复制 (Copied)' if copy_mode else '移动 (Moved)'}: {stats['copied'] if copy_mode else stats['moved']}")
            self._log(f"  跳过重复 (Duplicates skipped): {stats['skipped_duplicate']}")
            self._log(f"  重命名 (Renamed): {stats['renamed']}")
            self._log(f"  错误 (Errors): {stats['errors']}")
            
            self._update_status("完成 (Done)")
            messagebox.showinfo("完成 (Done)", "文件整理完成! (File organization complete!)")
            
        except Exception as e:
            self._log(f"发生错误 (Error occurred): {e}")
            self._update_status("错误 (Error)")
            messagebox.showerror("错误 (Error)", str(e))
        finally:
            self.is_running = False
            self.root.after(0, lambda: self.start_btn.config(state='normal'))
            
    def _update_progress(self, value):
        """Update progress bar from any thread."""
        self.root.after(0, lambda: self.progress_var.set(value))
        
    def _update_status(self, status):
        """Update status label from any thread."""
        self.root.after(0, lambda: self.status_var.set(status))


def main():
    """Main entry point for GUI application."""
    root = tk.Tk()
    PhotoOrganizerGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
