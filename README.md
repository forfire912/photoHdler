# photoHdler

A simple yet powerful photo management tool for organizing, searching, and analyzing your photo collections.

照片管理工具

## Features

- **List photos** with sorting options (by name, size, date, modified time)
- **Search photos** by name, size, date range, or file extension
- **Organize photos** automatically by date into folder structures
- **View statistics** about your photo collection
- **Extract EXIF metadata** from photos

## Installation

```bash
# Clone the repository
git clone https://github.com/forfire912/photoHdler.git
cd photoHdler

# Install the package
pip install -e .

# Or install dependencies manually
pip install -r requirements.txt
```

## Usage

### List Photos

```bash
# List all photos in a directory
photohdler list /path/to/photos

# Sort by size
photohdler list /path/to/photos -s size

# Sort by date in reverse order
photohdler list /path/to/photos -s date -r
```

### Search Photos

```bash
# Search by name pattern
photohdler search /path/to/photos -n "vacation"

# Search by extension
photohdler search /path/to/photos --ext jpg,png

# Search by size range
photohdler search /path/to/photos --min-size 1000000 --max-size 5000000

# Search by date range
photohdler search /path/to/photos --start-date 2023-01-01 --end-date 2023-12-31
```

### Organize Photos

```bash
# Organize photos by date (copies files)
photohdler organize /path/to/photos -o /path/to/organized

# Move files instead of copying
photohdler organize /path/to/photos -o /path/to/organized -m

# Custom date format for folders
photohdler organize /path/to/photos -o /path/to/organized -f "%Y/%m"

# Verbose output
photohdler organize /path/to/photos -o /path/to/organized -v
```

### View Statistics

```bash
photohdler stats /path/to/photos
```

### Photo Information

```bash
# Basic info
photohdler info /path/to/photo.jpg

# Include EXIF data
photohdler info /path/to/photo.jpg -e
```

## Python API

```python
from photohdler import PhotoManager, Photo

# Create a manager for a directory
manager = PhotoManager('/path/to/photos')

# List all photos
photos = manager.list_photos(sort_by='date')

# Search for photos
results = manager.search(name_pattern='vacation', extensions=['jpg'])

# Organize by date
manager.organize_by_date(output_dir='/path/to/organized')

# Get statistics
stats = manager.get_statistics()
print(f"Total photos: {stats['total_count']}")

# Work with individual photos
photo = Photo('/path/to/photo.jpg')
print(f"Name: {photo.name}")
print(f"Size: {photo.size} bytes")
print(f"Date taken: {photo.get_date_taken()}")
print(f"EXIF data: {photo.get_exif_data()}")
```

## Supported Formats

- JPEG (.jpg, .jpeg)
- PNG (.png)
- GIF (.gif)
- BMP (.bmp)
- TIFF (.tiff)
- WebP (.webp)

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=photohdler
```

## License

MIT License
照片管理

有大量（几十GB）照片和视频分布在不同的目录中，并且有很多是重复的。照片和视频的拍摄时间跨度遍布很多年份。
现在欲对这些照片整理到一个根目录中，并按年/月/日的目录结构进行移动和存储，并去掉重复（拍摄时间和大小一样）的照片和视频。
