"""
Photo class for representing individual photos.
"""

import os
from datetime import datetime
from typing import Optional


class Photo:
    """Represents a photo file with its metadata."""

    SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}

    def __init__(self, path: str):
        """
        Initialize a Photo object.

        Args:
            path: Path to the photo file.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file is not a supported image format.
        """
        self.path = os.path.abspath(path)

        if not os.path.exists(self.path):
            raise FileNotFoundError(f"Photo not found: {self.path}")

        ext = os.path.splitext(self.path)[1].lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported image format: {ext}")

        self._name = os.path.basename(self.path)
        self._size = os.path.getsize(self.path)
        self._modified_time = datetime.fromtimestamp(os.path.getmtime(self.path))
        self._created_time = datetime.fromtimestamp(os.path.getctime(self.path))
        self._exif_data: Optional[dict] = None

    @property
    def name(self) -> str:
        """Return the filename of the photo."""
        return self._name

    @property
    def size(self) -> int:
        """Return the file size in bytes."""
        return self._size

    @property
    def modified_time(self) -> datetime:
        """Return the file modification time."""
        return self._modified_time

    @property
    def created_time(self) -> datetime:
        """Return the file creation time."""
        return self._created_time

    @property
    def extension(self) -> str:
        """Return the file extension."""
        return os.path.splitext(self.path)[1].lower()

    def get_exif_data(self) -> dict:
        """
        Extract EXIF metadata from the photo.

        Returns:
            Dictionary containing EXIF data.
        """
        if self._exif_data is not None:
            return self._exif_data

        self._exif_data = {}

        try:
            from PIL import Image
            from PIL.ExifTags import TAGS

            with Image.open(self.path) as img:
                exif = img._getexif()
                if exif:
                    for tag_id, value in exif.items():
                        tag = TAGS.get(tag_id, tag_id)
                        self._exif_data[tag] = value
        except ImportError:
            pass
        except (AttributeError, IOError):
            pass

        return self._exif_data

    def get_date_taken(self) -> Optional[datetime]:
        """
        Get the date when the photo was taken.

        Returns:
            datetime object if available, None otherwise.
        """
        exif = self.get_exif_data()
        date_str = exif.get('DateTimeOriginal') or exif.get('DateTime')

        if date_str:
            try:
                return datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
            except (ValueError, TypeError):
                pass

        return self._modified_time

    def __repr__(self) -> str:
        return f"Photo('{self.path}')"

    def __str__(self) -> str:
        return self._name
