#!/usr/bin/env python3
"""
Photo and Video Organizer

A script to manage and organize a large collection of photos and videos.
It scans a source directory, extracts shooting dates, deduplicates based on
file size and timestamp, and organizes files into a Year/Month/Day structure.
"""

import argparse
import os
import shutil
from datetime import datetime
from pathlib import Path

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


def organize_photos(src, dest, copy_mode=False):
    """
    Main function to organize photos and videos.
    
    Args:
        src: Source directory path
        dest: Destination directory path
        copy_mode: If True, copy files; if False, move files
    """
    source_dir = Path(src)
    dest_dir = Path(dest)
    
    if not source_dir.exists():
        print(f"Error: Source directory '{src}' does not exist.")
        return
    
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
    
    print(f"Scanning source directory: {source_dir}")
    print(f"Destination directory: {dest_dir}")
    print(f"Mode: {'Copy' if copy_mode else 'Move'}")
    print("-" * 50)
    
    for filepath in scan_directory(source_dir):
        stats['processed'] += 1
        
        try:
            # Get file info for deduplication
            file_size = get_file_size(filepath)
            shooting_time = get_shooting_time(filepath)
            
            # Create deduplication key
            dedup_key = (file_size, shooting_time)
            
            # Check for duplicates
            if dedup_key in processed_files:
                print(f"Skipping duplicate: {filepath}")
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
                print(f"Renamed: {filepath.name} -> {dest_path.name}")
            
            # Move or copy the file
            if copy_mode:
                shutil.copy2(filepath, dest_path)
                stats['copied'] += 1
                print(f"Copied: {filepath} -> {dest_path}")
            else:
                shutil.move(filepath, dest_path)
                stats['moved'] += 1
                print(f"Moved: {filepath} -> {dest_path}")
                
        except Exception as e:
            print(f"Error processing {filepath}: {e}")
            stats['errors'] += 1
    
    # Print summary
    print("-" * 50)
    print("Summary:")
    print(f"  Total files processed: {stats['processed']}")
    print(f"  Files {'copied' if copy_mode else 'moved'}: {stats['copied'] if copy_mode else stats['moved']}")
    print(f"  Duplicates skipped: {stats['skipped_duplicate']}")
    print(f"  Files renamed: {stats['renamed']}")
    print(f"  Errors: {stats['errors']}")


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description='Organize photos and videos by date into Year/Month/Day structure.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s --src /path/to/photos --dest /path/to/organized
  %(prog)s --src ./messy_photos --dest ./organized_photos --copy
        '''
    )
    
    parser.add_argument(
        '--src',
        required=True,
        help='Source directory to scan for photos and videos'
    )
    
    parser.add_argument(
        '--dest',
        required=True,
        help='Destination directory for organized files'
    )
    
    parser.add_argument(
        '--copy',
        action='store_true',
        help='Copy files instead of moving them (default: move)'
    )
    
    args = parser.parse_args()
    
    organize_photos(args.src, args.dest, copy_mode=args.copy)


if __name__ == '__main__':
    main()
