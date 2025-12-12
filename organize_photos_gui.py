#!/usr/bin/env python3
"""
Photo and Video Organizer - GUI Version v0.7.0

A graphical interface to manage and organize a large collection of photos and videos.
It scans a source directory, extracts shooting dates, deduplicates based on
file size and timestamp, and organizes files into a Year/Month/Day structure.
"""

import os
import re
import shutil
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from PIL import Image, ExifTags

# Supported file extensions
IMAGE_EXTENSIONS = {
    # Common formats
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.heic', '.heif',
    # RAW formats (Canon, Nikon, Sony, Adobe, Olympus, Panasonic, Fuji, Pentax, etc.)
    '.raw', '.cr2', '.cr3', '.nef', '.arw', '.dng', '.orf', '.rw2', '.raf', '.pef', '.srw',
    '.3fr', '.ari', '.bay', '.cap', '.crw', '.dcs', '.dcr', '.drf', '.eip', '.erf', '.fff',
    '.iiq', '.k25', '.kdc', '.mdc', '.mef', '.mos', '.mrw', '.nrw', '.ptx', '.pxn', '.r3d',
    '.rwl', '.rwz', '.sr2', '.srf', '.x3f'
}
VIDEO_EXTENSIONS = {
    # Common formats
    '.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg',
    # HD/Camcorder/Older formats
    '.m2ts', '.mts', '.3gp', '.3g2', '.ts', '.vob', '.divx', '.xvid', '.rm', '.rmvb', '.asf', '.dv'
}
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


def get_camera_model(filepath):
    """
    Extract Camera Model from image EXIF data.
    
    Args:
        filepath: Path to the image file
        
    Returns:
        String representing camera model, or 'Unknown_Device'
    """
    try:
        ext = Path(filepath).suffix.lower()
        if ext not in IMAGE_EXTENSIONS:
            return "Video"
            
        with Image.open(filepath) as img:
            exif = img.getexif()
            if exif:
                # Look for Model tag (272)
                if 272 in exif:
                    model = exif[272]
                    # Clean up string (remove null bytes, extra spaces)
                    return str(model).strip().replace('\x00', '')
                
                # Look for Make tag (271) as fallback
                if 271 in exif:
                    return str(exif[271]).strip().replace('\x00', '')
                    
    except Exception:
        pass
    return "Unknown_Device"


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
        self.root.geometry("700x600")
        self.root.minsize(600, 500)
        
        # Variables
        self.src_dirs = []  # List of source directories
        self.dest_var = tk.StringVar()
        self.copy_mode_var = tk.BooleanVar(value=False)
        self.clean_empty_dirs_var = tk.BooleanVar(value=True)
        self.delete_duplicates_var = tk.BooleanVar(value=False)
        self.rename_files_var = tk.BooleanVar(value=False)
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
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(5, weight=1)
        
        # Title
        title_label = ttk.Label(
            main_frame, 
            text="照片视频整理工具", 
            font=("Arial", 16, "bold")
        )
        title_label.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        
        # Source directories section
        src_frame = ttk.LabelFrame(main_frame, text="源目录 (Source Directories)", padding="5")
        src_frame.grid(row=1, column=0, sticky="nsew", pady=5)
        src_frame.columnconfigure(0, weight=1)
        src_frame.rowconfigure(0, weight=1)
        
        # Listbox for source directories
        listbox_frame = ttk.Frame(src_frame)
        listbox_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        listbox_frame.columnconfigure(0, weight=1)
        listbox_frame.rowconfigure(0, weight=1)
        
        self.src_listbox = tk.Listbox(listbox_frame, height=4, selectmode=tk.EXTENDED)
        self.src_listbox.grid(row=0, column=0, sticky="nsew")
        
        scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=self.src_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.src_listbox.config(yscrollcommand=scrollbar.set)
        
        # Buttons for source directories
        src_buttons_frame = ttk.Frame(src_frame)
        src_buttons_frame.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Button(
            src_buttons_frame, text="添加目录\nAdd Dir", command=self._add_src_dir, width=12
        ).pack(pady=2)
        
        ttk.Button(
            src_buttons_frame, text="删除选中\nRemove", command=self._remove_src_dir, width=12
        ).pack(pady=2)
        
        ttk.Button(
            src_buttons_frame, text="清空全部\nClear All", command=self._clear_src_dirs, width=12
        ).pack(pady=2)
        
        # Destination directory
        dest_frame = ttk.Frame(main_frame)
        dest_frame.grid(row=2, column=0, sticky="ew", pady=5)
        dest_frame.columnconfigure(1, weight=1)
        
        ttk.Label(dest_frame, text="目标目录 (Dest):").grid(
            row=0, column=0, sticky="w", padx=5
        )
        dest_entry = ttk.Entry(dest_frame, textvariable=self.dest_var, width=50)
        dest_entry.grid(row=0, column=1, sticky="ew", padx=5)
        ttk.Button(
            dest_frame, text="浏览...", command=self._browse_dest
        ).grid(row=0, column=2, padx=5)
        
        # Options frame
        options_frame = ttk.LabelFrame(main_frame, text="选项 (Options)", padding="5")
        options_frame.grid(row=3, column=0, sticky="ew", pady=10)
        
        # Organization Mode
        mode_frame = ttk.Frame(options_frame)
        mode_frame.pack(fill="x", pady=2)
        
        ttk.Label(mode_frame, text="整理模式 (Mode):").pack(side="left")
        
        self.mode_var = tk.StringVar(value="date")
        ttk.Radiobutton(
            mode_frame, 
            text="按日期 (By Date) - YYYY/MM/DD", 
            variable=self.mode_var, 
            value="date"
        ).pack(side="left", padx=10)
        
        ttk.Radiobutton(
            mode_frame, 
            text="按事件 (By Event) - 聚合相近时间照片", 
            variable=self.mode_var, 
            value="event"
        ).pack(side="left", padx=10)
        
        ttk.Radiobutton(
            mode_frame, 
            text="自定义 (Custom)", 
            variable=self.mode_var, 
            value="custom",
            command=self._toggle_custom_template
        ).pack(side="left", padx=10)
        
        # Custom Template Frame (Hidden by default)
        self.template_frame = ttk.Frame(options_frame)
        self.template_frame.pack(fill="x", pady=5)
        
        ttk.Label(self.template_frame, text="路径模板 (Template):").pack(side="left")
        self.template_var = tk.StringVar(value="{year}/{month}/{day}")
        ttk.Entry(self.template_frame, textvariable=self.template_var, width=40).pack(side="left", padx=5)
        
        help_text = "可用变量: {year}, {month}, {day}, {camera}, {ext}"
        ttk.Label(self.template_frame, text=help_text, font=("Arial", 8), foreground="gray").pack(side="left", padx=5)
        
        # Initial toggle state
        self._toggle_custom_template()
        
        ttk.Separator(options_frame, orient="horizontal").pack(fill="x", pady=5)
        
        ttk.Checkbutton(
            options_frame, 
            text="复制模式 (保留原文件) / Copy mode (keep original files)",
            variable=self.copy_mode_var
        ).pack(anchor="w")
        
        ttk.Checkbutton(
            options_frame, 
            text="移动后清理空目录 / Delete empty folders after move",
            variable=self.clean_empty_dirs_var
        ).pack(anchor="w")
        
        ttk.Checkbutton(
            options_frame, 
            text="移动时删除重复文件 / Delete duplicates when moving",
            variable=self.delete_duplicates_var
        ).pack(anchor="w")
        
        ttk.Checkbutton(
            options_frame, 
            text="按拍摄时间重命名文件 / Rename files by Date (YYYYMMDD_HHMMSS)",
            variable=self.rename_files_var
        ).pack(anchor="w")
        
        # Progress and log area
        log_frame = ttk.LabelFrame(main_frame, text="日志 (Log)", padding="5")
        log_frame.grid(row=4, column=0, sticky="nsew", pady=10)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=12, width=70, state='disabled'
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            main_frame, variable=self.progress_var, maximum=100
        )
        self.progress_bar.grid(row=5, column=0, sticky="ew", pady=5)
        
        # Status label
        self.status_var = tk.StringVar(value="就绪 (Ready)")
        status_label = ttk.Label(main_frame, textvariable=self.status_var)
        status_label.grid(row=6, column=0, sticky="w")
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=7, column=0, pady=10)
        
        # Start button with prominent styling
        style = ttk.Style()
        style.configure("Start.TButton", font=("Arial", 11, "bold"))
        
        self.start_btn = ttk.Button(
            buttons_frame, 
            text="▶ 开始整理 (Start Organizing)", 
            command=self._start_organizing,
            style="Start.TButton",
            width=25
        )
        self.start_btn.pack(side="left", padx=10)
        
        ttk.Button(
            buttons_frame, text="清除日志 (Clear Log)", command=self._clear_log
        ).pack(side="left", padx=5)
        
        ttk.Button(
            buttons_frame, text="退出 (Exit)", command=self.root.quit
        ).pack(side="left", padx=5)
    
    def _add_src_dir(self):
        """Add a source directory to the list."""
        directory = filedialog.askdirectory(title="选择源目录 (Select Source Directory)")
        if directory and directory not in self.src_dirs:
            self.src_dirs.append(directory)
            self.src_listbox.insert(tk.END, directory)
        elif directory in self.src_dirs:
            messagebox.showinfo("提示 (Info)", "该目录已添加 (Directory already added)")
    
    def _remove_src_dir(self):
        """Remove selected source directories from the list."""
        selected_indices = self.src_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("警告 (Warning)", "请先选择要删除的目录 (Please select directories to remove)")
            return
        
        # Delete in reverse order to maintain correct indices
        for index in reversed(selected_indices):
            del self.src_dirs[index]
            self.src_listbox.delete(index)
    
    def _clear_src_dirs(self):
        """Clear all source directories."""
        self.src_dirs.clear()
        self.src_listbox.delete(0, tk.END)
        
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
    
    def _toggle_custom_template(self):
        """Show/hide custom template input based on mode."""
        if self.mode_var.get() == 'custom':
            # Use pack_forget first to ensure clean state, then pack
            self.template_frame.pack(fill="x", pady=5, after=self.template_frame.master.winfo_children()[0])
        else:
            self.template_frame.pack_forget()
            
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
        dest = self.dest_var.get().strip()
        
        # Validate inputs
        if not self.src_dirs:
            messagebox.showerror("错误 (Error)", "请至少添加一个源目录 (Please add at least one source directory)")
            return
        if not dest:
            messagebox.showerror("错误 (Error)", "请选择目标目录 (Please select destination directory)")
            return
        
        # Validate all source directories exist
        invalid_dirs = [d for d in self.src_dirs if not os.path.isdir(d)]
        if invalid_dirs:
            messagebox.showerror(
                "错误 (Error)", 
                f"以下源目录不存在 (The following source directories do not exist):\n" + 
                "\n".join(invalid_dirs)
            )
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
            args=(self.src_dirs.copy(), dest, self.copy_mode_var.get())
        )
        thread.daemon = False  # Allow thread to complete before exit
        thread.start()
        
    def _organize_thread(self, src_dirs, dest, copy_mode):
        """Background thread for organizing photos."""
        try:
            dest_dir = Path(dest)
            
            # Track processed files by (size, timestamp) for deduplication
            processed_files = set()
            
            # Statistics
            stats = {
                'processed': 0,
                'skipped_duplicate': 0,
                'deleted_duplicate': 0,
                'moved': 0,
                'copied': 0,
                'renamed': 0,
                'errors': 0
            }
            
            self._update_status("正在扫描文件... (Scanning files...)")
            self._log(f"源目录数量: {len(src_dirs)}")
            for i, src_dir in enumerate(src_dirs, 1):
                self._log(f"  源目录 {i}: {src_dir}")
            self._log(f"目标目录: {dest_dir}")
            self._log(f"模式: {'复制 (Copy)' if copy_mode else '移动 (Move)'}")
            self._log("-" * 50)
            
            # First, count total files from all source directories for progress
            all_files = []
            for src_dir in src_dirs:
                source_dir = Path(src_dir)
                self._log(f"正在扫描: {source_dir}")
                files_from_dir = list(scan_directory(source_dir))
                all_files.extend(files_from_dir)
                self._log(f"  找到 {len(files_from_dir)} 个文件")
            
            total_files = len(all_files)
            
            if total_files == 0:
                self._log("未找到支持的文件 (No supported files found)")
                self._update_status("完成 (Done) - 未找到文件")
                return
                
            self._log(f"找到 {total_files} 个文件 (Found {total_files} files)")
            self._log("-" * 50)
            
            if total_files == 0:
                self._log("未找到支持的文件 (No supported files found)")
                self._update_status("完成 (Done) - 未找到文件")
                return
                
            self._log(f"找到 {total_files} 个文件 (Found {total_files} files)")
            self._log("-" * 50)
            
            if self.mode_var.get() == 'event':
                self._process_by_event(all_files, dest_dir, copy_mode, stats, processed_files)
            elif self.mode_var.get() == 'custom':
                template = self.template_var.get().strip()
                if not template:
                    self._log("错误: 模板为空，使用默认模板 (Error: Empty template, using default)")
                    template = "{year}/{month}/{day}"
                self._process_by_custom(all_files, dest_dir, copy_mode, stats, processed_files, template)
            else:
                self._process_by_date(all_files, dest_dir, copy_mode, stats, processed_files)
            
            # Print summary
            self._log("-" * 50)
            self._log("完成! 统计信息 (Done! Summary):")
            self._log(f"  处理文件总数 (Total processed): {stats['processed']}")
            self._log(f"  {'复制 (Copied)' if copy_mode else '移动 (Moved)'}: {stats['copied'] if copy_mode else stats['moved']}")
            self._log(f"  跳过重复 (Duplicates skipped): {stats['skipped_duplicate']}")
            if stats['deleted_duplicate'] > 0:
                self._log(f"  删除重复 (Duplicates deleted): {stats['deleted_duplicate']}")
            self._log(f"  重命名 (Renamed): {stats['renamed']}")
            self._log(f"  错误 (Errors): {stats['errors']}")
            
            # Clean up empty directories if requested and not in copy mode
            if not copy_mode and self.clean_empty_dirs_var.get():
                self._cleanup_empty_dirs(src_dirs)
            
            self._update_status("完成 (Done)")
            messagebox.showinfo("完成 (Done)", "文件整理完成! (File organization complete!)")
            
        except Exception as e:
            self._log(f"发生错误 (Error occurred): {e}")
            self._update_status("错误 (Error)")
            messagebox.showerror("错误 (Error)", str(e))
        finally:
            self.is_running = False
            self.root.after(0, lambda: self.start_btn.config(state='normal'))
    
    def _process_by_date(self, all_files, dest_dir, copy_mode, stats, processed_files):
        """Process files by date (Year/Month/Day)."""
        total_files = len(all_files)
        
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
                    if not copy_mode and self.delete_duplicates_var.get():
                        try:
                            os.remove(filepath)
                            self._log(f"删除重复文件 (Deleted duplicate): {filepath.name}")
                            stats['deleted_duplicate'] += 1
                        except Exception as e:
                            self._log(f"删除重复文件失败 (Failed to delete duplicate) {filepath.name}: {e}")
                            stats['errors'] += 1
                    else:
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
                
                # Determine filename
                filename = self._get_target_filename(filepath, shooting_time)
                dest_path = dest_folder / filename
                
                self._move_or_copy_file(filepath, dest_path, dest_dir, copy_mode, stats, file_size, shooting_time)
                    
            except Exception as e:
                self._log(f"错误 (Error) {filepath.name}: {e}")
                stats['errors'] += 1

    def _process_by_event(self, all_files, dest_dir, copy_mode, stats, processed_files):
        """Process files by event (clustering by time)."""
        total_files = len(all_files)
        self._update_status("正在分析文件时间... (Analyzing file times...)")
        
        # 1. Collect file info
        file_infos = []
        for i, filepath in enumerate(all_files):
            try:
                shooting_time = get_shooting_time(filepath)
                file_size = get_file_size(filepath)
                file_infos.append({
                    'path': filepath,
                    'time': shooting_time,
                    'size': file_size
                })
            except Exception as e:
                self._log(f"读取信息失败 (Read info failed) {filepath.name}: {e}")
                stats['errors'] += 1
            
            if i % 10 == 0:
                progress = (i + 1) / total_files * 50  # First 50% for analysis
                self._update_progress(progress)
        
        # 2. Sort by time
        file_infos.sort(key=lambda x: x['time'])
        
        # 3. Cluster events
        # Threshold: 2 hours (7200 seconds)
        EVENT_THRESHOLD = 7200
        
        if not file_infos:
            return

        current_event_files = []
        last_time = None
        
        # Process clusters
        total_infos = len(file_infos)
        processed_count = 0
        
        # Helper to process a batch of files as one event
        def process_event_batch(files_batch):
            if not files_batch:
                return
                
            # Determine event folder name from the first file's time
            start_time = files_batch[0]['time']
            # Format: YYYY-MM-DD_HHMM
            event_folder_name = start_time.strftime("%Y-%m-%d_%H%M")
            dest_folder = dest_dir / event_folder_name
            dest_folder.mkdir(parents=True, exist_ok=True)
            
            self._log(f"创建事件文件夹 (Event): {event_folder_name} ({len(files_batch)} files)")
            
            for file_info in files_batch:
                filepath = file_info['path']
                dedup_key = (file_info['size'], file_info['time'])
                
                stats['processed'] += 1
                
                if dedup_key in processed_files:
                    if not copy_mode and self.delete_duplicates_var.get():
                        try:
                            os.remove(filepath)
                            self._log(f"  删除重复 (Deleted dup): {filepath.name}")
                            stats['deleted_duplicate'] += 1
                        except Exception as e:
                            self._log(f"  删除重复失败 (Failed delete dup) {filepath.name}: {e}")
                            stats['errors'] += 1
                    else:
                        self._log(f"  跳过重复 (Skip dup): {filepath.name}")
                        stats['skipped_duplicate'] += 1
                    continue
                
                processed_files.add(dedup_key)
                
                # Determine filename
                filename = self._get_target_filename(filepath, file_info['time'])
                dest_path = dest_folder / filename
                
                try:
                    self._move_or_copy_file(filepath, dest_path, dest_dir, copy_mode, stats, file_info['size'], file_info['time'])
                except Exception as e:
                    self._log(f"  错误 (Error) {filepath.name}: {e}")
                    stats['errors'] += 1

        # Iterate and cluster
        for i, info in enumerate(file_infos):
            current_time = info['time']
            
            if last_time is None:
                current_event_files.append(info)
            else:
                time_diff = (current_time - last_time).total_seconds()
                if time_diff > EVENT_THRESHOLD:
                    # New event detected, process previous batch
                    process_event_batch(current_event_files)
                    current_event_files = [info]
                else:
                    current_event_files.append(info)
            
            last_time = current_time
            
            # Update progress (50% - 100%)
            processed_count += 1
            if processed_count % 5 == 0:
                progress = 50 + (processed_count / total_infos * 50)
                self._update_progress(progress)
                self._update_status(f"整理事件中: {processed_count}/{total_infos}")

        # Process the last batch
        if current_event_files:
            process_event_batch(current_event_files)
            
        self._update_progress(100)

    def _process_by_custom(self, all_files, dest_dir, copy_mode, stats, processed_files, template):
        """Process files using a custom path template."""
        total_files = len(all_files)
        
        for i, filepath in enumerate(all_files):
            stats['processed'] += 1
            progress = (i + 1) / total_files * 100
            self._update_progress(progress)
            self._update_status(f"处理中: {i+1}/{total_files}")
            
            try:
                # Get file info
                file_size = get_file_size(filepath)
                shooting_time = get_shooting_time(filepath)
                
                # Deduplication
                dedup_key = (file_size, shooting_time)
                if dedup_key in processed_files:
                    if not copy_mode and self.delete_duplicates_var.get():
                        try:
                            os.remove(filepath)
                            self._log(f"删除重复文件 (Deleted duplicate): {filepath.name}")
                            stats['deleted_duplicate'] += 1
                        except Exception as e:
                            self._log(f"删除重复文件失败 (Failed to delete duplicate) {filepath.name}: {e}")
                            stats['errors'] += 1
                    else:
                        self._log(f"跳过重复文件 (Skip duplicate): {filepath.name}")
                        stats['skipped_duplicate'] += 1
                    continue
                processed_files.add(dedup_key)
                
                # Prepare variables for template
                vars = {
                    'year': str(shooting_time.year),
                    'month': f"{shooting_time.month:02d}",
                    'day': f"{shooting_time.day:02d}",
                    'ext': filepath.suffix.lower().replace('.', ''),
                    'camera': get_camera_model(filepath).replace('/', '_').replace('\\', '_').strip(),
                    'type': 'Photo' if filepath.suffix.lower() in IMAGE_EXTENSIONS else 'Video'
                }
                
                # Generate relative path from template
                try:
                    rel_path_str = template.format(**vars)
                    # Sanitize path components
                    rel_path = Path(rel_path_str)
                except Exception as e:
                    self._log(f"模板错误 (Template Error): {e}")
                    # Fallback to date
                    rel_path = Path(vars['year']) / vars['month'] / vars['day']
                
                dest_folder = dest_dir / rel_path
                dest_folder.mkdir(parents=True, exist_ok=True)
                
                filename = self._get_target_filename(filepath, shooting_time)
                dest_path = dest_folder / filename
                
                self._move_or_copy_file(filepath, dest_path, dest_dir, copy_mode, stats, file_size, shooting_time)
                    
            except Exception as e:
                self._log(f"错误 (Error) {filepath.name}: {e}")
                stats['errors'] += 1

    def _get_target_filename(self, filepath, shooting_time):
        """Generate target filename based on settings."""
        if not self.rename_files_var.get():
            return filepath.name
            
        # Format: YYYYMMDD_HHMMSS
        timestamp_str = shooting_time.strftime("%Y%m%d_%H%M%S")
        suffix = filepath.suffix.lower()
        return f"{timestamp_str}{suffix}"

    def _move_or_copy_file(self, filepath, dest_path, dest_dir, copy_mode, stats, src_size=None, src_time=None):
        """Helper to move or copy a file with rename logic."""
        
        # Enhanced Duplicate Check: Check for existing files in the target folder
        # that match the filename pattern (including _1, _2 variations)
        if src_size is not None and src_time is not None:
            dest_folder = dest_path.parent
            if dest_folder.exists():
                target_stem = dest_path.stem
                target_suffix = dest_path.suffix.lower()
                
                # Determine base stem (handle cases like IMG_1234_1 -> IMG_1234)
                base_stem = target_stem
                # Check if stem ends with _\d+
                m = re.search(r'_(\d+)$', target_stem)
                if m:
                    base_stem = target_stem[:m.start()]
                
                found_duplicate = False
                duplicate_file = None

                try:
                    # Iterate over files in the destination folder
                    for entry in dest_folder.iterdir():
                        if not entry.is_file():
                            continue
                            
                        # Check if the file is a candidate
                        entry_suffix = entry.suffix.lower()
                        if entry_suffix != target_suffix:
                            continue
                            
                        entry_stem = entry.stem
                        is_candidate = False
                        
                        # Check against base_stem (e.g. IMG_1234)
                        if entry_stem == base_stem:
                            is_candidate = True
                        # Check against variations (e.g. IMG_1234_1, IMG_1234_2)
                        elif entry_stem.startswith(f"{base_stem}_"):
                            # Check if the rest is a number
                            suffix_part = entry_stem[len(base_stem)+1:]
                            if suffix_part.isdigit():
                                is_candidate = True
                        
                        if is_candidate:
                            # Check metadata match
                            try:
                                d_size = get_file_size(entry)
                                d_time = get_shooting_time(entry)
                                if src_size == d_size and src_time == d_time:
                                    found_duplicate = True
                                    duplicate_file = entry
                                    break
                            except Exception:
                                pass
                                
                    if found_duplicate:
                        if not copy_mode and self.delete_duplicates_var.get():
                            try:
                                os.remove(filepath)
                                self._log(f"  删除重复文件 (Deleted duplicate - found {duplicate_file.name}): {filepath.name}")
                                stats['deleted_duplicate'] += 1
                            except Exception as e:
                                self._log(f"  删除重复失败 (Failed delete dup): {e}")
                                stats['errors'] += 1
                        else:
                            self._log(f"  跳过重复文件 (Skip duplicate - found {duplicate_file.name}): {filepath.name}")
                            stats['skipped_duplicate'] += 1
                        return
                        
                except Exception as e:
                    self._log(f"  检查目标目录失败 (Check dest dir failed): {e}")

        # Handle filename collision
        original_dest = dest_path
        dest_path = generate_unique_filename(dest_path)
        
        if dest_path != original_dest:
            stats['renamed'] += 1
            self._log(f"  重命名 (Renamed): {filepath.name} -> {dest_path.name}")
        
        # Move or copy the file
        if copy_mode:
            shutil.copy2(filepath, dest_path)
            stats['copied'] += 1
            # self._log(f"  复制 (Copied): {filepath.name}") # Reduce log spam
        else:
            shutil.move(filepath, dest_path)
            stats['moved'] += 1
            # self._log(f"  移动 (Moved): {filepath.name}")

    def _cleanup_empty_dirs(self, src_dirs):
        """Clean up empty directories in source paths."""
        self._log("-" * 50)
        self._log("正在清理空目录... (Cleaning up empty directories...)")
        removed_count = 0
        
        for src_dir in src_dirs:
            # Walk bottom-up to remove nested empty dirs
            for root, dirs, files in os.walk(src_dir, topdown=False):
                for name in dirs:
                    dir_path = Path(root) / name
                    try:
                        # Only remove if empty
                        if not any(dir_path.iterdir()):
                            dir_path.rmdir()
                            removed_count += 1
                            self._log(f"  删除空目录 (Removed): {dir_path}")
                    except Exception:
                        pass
        
        if removed_count > 0:
            self._log(f"共删除 {removed_count} 个空目录 (Removed {removed_count} empty directories)")
        else:
            self._log("没有发现空目录 (No empty directories found)")

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
