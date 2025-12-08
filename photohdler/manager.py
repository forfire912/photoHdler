"""
PhotoManager class for managing a collection of photos.
"""

import os
import shutil
from datetime import datetime
from typing import Callable, List, Optional

from .photo import Photo


class PhotoManager:
    """Manages a collection of photos in a directory."""

    def __init__(self, directory: str):
        """
        Initialize the PhotoManager.

        Args:
            directory: Path to the directory containing photos.

        Raises:
            NotADirectoryError: If the path is not a directory.
        """
        self.directory = os.path.abspath(directory)

        if not os.path.exists(self.directory):
            os.makedirs(self.directory)
        elif not os.path.isdir(self.directory):
            raise NotADirectoryError(f"Not a directory: {self.directory}")

        self._photos: List[Photo] = []
        self._loaded = False

    def scan(self) -> List[Photo]:
        """
        Scan the directory for photos.

        Returns:
            List of Photo objects found in the directory.
        """
        self._photos = []

        for root, _, files in os.walk(self.directory):
            for filename in files:
                filepath = os.path.join(root, filename)
                try:
                    photo = Photo(filepath)
                    self._photos.append(photo)
                except (FileNotFoundError, ValueError):
                    continue

        self._loaded = True
        return self._photos

    @property
    def photos(self) -> List[Photo]:
        """Return the list of photos. Scans if not already loaded."""
        if not self._loaded:
            self.scan()
        return self._photos

    def list_photos(self, sort_by: str = 'name', reverse: bool = False) -> List[Photo]:
        """
        List all photos with optional sorting.

        Args:
            sort_by: Sort criteria ('name', 'size', 'date', 'modified').
            reverse: Whether to reverse the sort order.

        Returns:
            Sorted list of Photo objects.
        """
        photos = self.photos.copy()

        sort_keys: dict[str, Callable[[Photo], object]] = {
            'name': lambda p: p.name.lower(),
            'size': lambda p: p.size,
            'date': lambda p: p.get_date_taken() or datetime.min,
            'modified': lambda p: p.modified_time,
        }

        key_func = sort_keys.get(sort_by, sort_keys['name'])
        photos.sort(key=key_func, reverse=reverse)

        return photos

    def search(
        self,
        name_pattern: Optional[str] = None,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        extensions: Optional[List[str]] = None
    ) -> List[Photo]:
        """
        Search for photos matching the given criteria.

        Args:
            name_pattern: Pattern to match in filename (case-insensitive).
            min_size: Minimum file size in bytes.
            max_size: Maximum file size in bytes.
            start_date: Earliest date taken.
            end_date: Latest date taken.
            extensions: List of extensions to filter by.

        Returns:
            List of Photo objects matching the criteria.
        """
        results = []

        for photo in self.photos:
            if name_pattern and name_pattern.lower() not in photo.name.lower():
                continue

            if min_size is not None and photo.size < min_size:
                continue

            if max_size is not None and photo.size > max_size:
                continue

            date_taken = photo.get_date_taken()
            if date_taken:
                if start_date and date_taken < start_date:
                    continue
                if end_date and date_taken > end_date:
                    continue

            if extensions:
                normalized_extensions = [e.lower() if e.startswith('.') else f'.{e.lower()}' for e in extensions]
                if photo.extension not in normalized_extensions:
                    continue

            results.append(photo)

        return results

    def organize_by_date(
        self,
        output_dir: Optional[str] = None,
        date_format: str = '%Y/%Y-%m',
        copy: bool = True
    ) -> dict:
        """
        Organize photos into subdirectories by date.

        Args:
            output_dir: Output directory (defaults to source directory).
            date_format: strftime format for directory structure.
            copy: If True, copy files; if False, move files.

        Returns:
            Dictionary mapping photos to their new locations.
        """
        if output_dir is None:
            output_dir = self.directory
        else:
            output_dir = os.path.abspath(output_dir)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

        results = {}

        for photo in self.photos:
            date_taken = photo.get_date_taken()
            if date_taken is None:
                date_taken = photo.modified_time

            date_dir = date_taken.strftime(date_format)
            target_dir = os.path.join(output_dir, date_dir)

            if not os.path.exists(target_dir):
                os.makedirs(target_dir)

            target_path = os.path.join(target_dir, photo.name)

            # Handle duplicate filenames
            if os.path.exists(target_path) and target_path != photo.path:
                base, ext = os.path.splitext(photo.name)
                counter = 1
                while os.path.exists(target_path):
                    target_path = os.path.join(target_dir, f"{base}_{counter}{ext}")
                    counter += 1

            if target_path != photo.path:
                if copy:
                    shutil.copy2(photo.path, target_path)
                else:
                    shutil.move(photo.path, target_path)

                results[photo.path] = target_path

        return results

    def get_statistics(self) -> dict:
        """
        Get statistics about the photo collection.

        Returns:
            Dictionary with statistics.
        """
        photos = self.photos

        if not photos:
            return {
                'total_count': 0,
                'total_size': 0,
                'extensions': {},
                'oldest': None,
                'newest': None,
            }

        total_size = sum(p.size for p in photos)
        extensions: dict[str, int] = {}

        for photo in photos:
            ext = photo.extension
            extensions[ext] = extensions.get(ext, 0) + 1

        dates = [p.get_date_taken() for p in photos]
        valid_dates = [d for d in dates if d is not None]

        return {
            'total_count': len(photos),
            'total_size': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'extensions': extensions,
            'oldest': min(valid_dates) if valid_dates else None,
            'newest': max(valid_dates) if valid_dates else None,
        }

    def __len__(self) -> int:
        return len(self.photos)

    def __repr__(self) -> str:
        return f"PhotoManager('{self.directory}')"
