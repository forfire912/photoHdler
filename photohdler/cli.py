"""
Command-line interface for photoHdler.
"""

import argparse
import sys
from datetime import datetime

from .manager import PhotoManager


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def cmd_list(args: argparse.Namespace) -> int:
    """List photos in a directory."""
    manager = PhotoManager(args.directory)
    photos = manager.list_photos(sort_by=args.sort, reverse=args.reverse)

    if not photos:
        print("No photos found.")
        return 0

    print(f"\nFound {len(photos)} photos in {args.directory}\n")
    print(f"{'Name':<40} {'Size':>10} {'Date Taken':>20}")
    print("-" * 72)

    for photo in photos:
        date_taken = photo.get_date_taken()
        date_str = date_taken.strftime('%Y-%m-%d %H:%M') if date_taken else 'Unknown'
        print(f"{photo.name:<40} {format_size(photo.size):>10} {date_str:>20}")

    return 0


def cmd_search(args: argparse.Namespace) -> int:
    """Search for photos."""
    manager = PhotoManager(args.directory)

    start_date = None
    end_date = None

    if args.start_date:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    if args.end_date:
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d')

    extensions = args.ext.split(',') if args.ext else None

    photos = manager.search(
        name_pattern=args.name,
        min_size=args.min_size,
        max_size=args.max_size,
        start_date=start_date,
        end_date=end_date,
        extensions=extensions
    )

    if not photos:
        print("No matching photos found.")
        return 0

    print(f"\nFound {len(photos)} matching photos:\n")
    for photo in photos:
        print(f"  {photo.path}")

    return 0


def cmd_organize(args: argparse.Namespace) -> int:
    """Organize photos by date."""
    manager = PhotoManager(args.directory)

    if not manager.photos:
        print("No photos found to organize.")
        return 0

    action = "Copying" if args.copy else "Moving"
    print(f"{action} {len(manager.photos)} photos...")

    results = manager.organize_by_date(
        output_dir=args.output,
        date_format=args.format,
        copy=args.copy
    )

    print(f"\nOrganized {len(results)} photos.")
    if args.verbose:
        for src, dst in results.items():
            print(f"  {src} -> {dst}")

    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    """Show statistics about photos."""
    manager = PhotoManager(args.directory)
    stats = manager.get_statistics()

    print(f"\nPhoto Statistics for {args.directory}\n")
    print(f"  Total photos: {stats['total_count']}")
    print(f"  Total size: {format_size(stats['total_size'])}")

    if stats['extensions']:
        print("\n  By extension:")
        for ext, count in sorted(stats['extensions'].items()):
            print(f"    {ext}: {count}")

    if stats['oldest']:
        print(f"\n  Date range:")
        print(f"    Oldest: {stats['oldest'].strftime('%Y-%m-%d %H:%M')}")
        print(f"    Newest: {stats['newest'].strftime('%Y-%m-%d %H:%M')}")

    return 0


def cmd_info(args: argparse.Namespace) -> int:
    """Show information about a specific photo."""
    from .photo import Photo

    try:
        photo = Photo(args.file)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")
        return 1

    print(f"\nPhoto Information: {photo.name}\n")
    print(f"  Path: {photo.path}")
    print(f"  Size: {format_size(photo.size)}")
    print(f"  Modified: {photo.modified_time.strftime('%Y-%m-%d %H:%M:%S')}")

    date_taken = photo.get_date_taken()
    if date_taken:
        print(f"  Date taken: {date_taken.strftime('%Y-%m-%d %H:%M:%S')}")

    if args.exif:
        exif = photo.get_exif_data()
        if exif:
            print("\n  EXIF Data:")
            for key, value in sorted(exif.items()):
                if isinstance(value, bytes):
                    value = f"<{len(value)} bytes>"
                print(f"    {key}: {value}")
        else:
            print("\n  No EXIF data available.")

    return 0


def main(argv: list = None) -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog='photohdler',
        description='Photo management tool'
    )
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 0.1.0'
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # List command
    list_parser = subparsers.add_parser('list', help='List photos in a directory')
    list_parser.add_argument('directory', help='Directory to scan')
    list_parser.add_argument(
        '-s', '--sort',
        choices=['name', 'size', 'date', 'modified'],
        default='name',
        help='Sort criteria'
    )
    list_parser.add_argument(
        '-r', '--reverse',
        action='store_true',
        help='Reverse sort order'
    )
    list_parser.set_defaults(func=cmd_list)

    # Search command
    search_parser = subparsers.add_parser('search', help='Search for photos')
    search_parser.add_argument('directory', help='Directory to search')
    search_parser.add_argument('-n', '--name', help='Name pattern to match')
    search_parser.add_argument('--min-size', type=int, help='Minimum size in bytes')
    search_parser.add_argument('--max-size', type=int, help='Maximum size in bytes')
    search_parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    search_parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    search_parser.add_argument('--ext', help='Extensions (comma-separated)')
    search_parser.set_defaults(func=cmd_search)

    # Organize command
    organize_parser = subparsers.add_parser('organize', help='Organize photos by date')
    organize_parser.add_argument('directory', help='Source directory')
    organize_parser.add_argument('-o', '--output', help='Output directory')
    organize_parser.add_argument(
        '-f', '--format',
        default='%Y/%Y-%m',
        help='Date format for folders (default: %%Y/%%Y-%%m)'
    )
    organize_parser.add_argument(
        '-m', '--move',
        dest='copy',
        action='store_false',
        help='Move files instead of copying'
    )
    organize_parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show detailed output'
    )
    organize_parser.set_defaults(func=cmd_organize)

    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show photo statistics')
    stats_parser.add_argument('directory', help='Directory to analyze')
    stats_parser.set_defaults(func=cmd_stats)

    # Info command
    info_parser = subparsers.add_parser('info', help='Show photo information')
    info_parser.add_argument('file', help='Photo file')
    info_parser.add_argument(
        '-e', '--exif',
        action='store_true',
        help='Show EXIF data'
    )
    info_parser.set_defaults(func=cmd_info)

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
