"""Tests for the PhotoManager class."""

import os
import shutil
import tempfile
from datetime import datetime

import pytest

from photohdler.manager import PhotoManager
from photohdler.photo import Photo


@pytest.fixture
def temp_photo_dir():
    """Create a temporary directory with test images."""
    temp_dir = tempfile.mkdtemp()

    # Create test images
    images = [
        ('photo1.jpg', b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9'),
        ('photo2.jpg', b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9'),
        ('image.png', b'\x89PNG\r\n\x1a\n'),
        ('document.txt', b'not an image'),
    ]

    for name, content in images:
        filepath = os.path.join(temp_dir, name)
        with open(filepath, 'wb') as f:
            f.write(content)

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def empty_dir():
    """Create an empty temporary directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


class TestPhotoManager:
    """Tests for PhotoManager class."""

    def test_init_existing_directory(self, temp_photo_dir):
        """Test PhotoManager initialization with existing directory."""
        manager = PhotoManager(temp_photo_dir)
        assert manager.directory == os.path.abspath(temp_photo_dir)

    def test_init_creates_directory(self, empty_dir):
        """Test PhotoManager creates directory if it doesn't exist."""
        new_dir = os.path.join(empty_dir, 'new_photos')
        manager = PhotoManager(new_dir)
        assert os.path.exists(new_dir)

    def test_init_not_a_directory(self, temp_photo_dir):
        """Test PhotoManager raises error for file path."""
        file_path = os.path.join(temp_photo_dir, 'photo1.jpg')
        with pytest.raises(NotADirectoryError):
            PhotoManager(file_path)

    def test_scan(self, temp_photo_dir):
        """Test scanning for photos."""
        manager = PhotoManager(temp_photo_dir)
        photos = manager.scan()

        # Should find 3 image files, not the txt file
        assert len(photos) == 3
        assert all(isinstance(p, Photo) for p in photos)

    def test_photos_property(self, temp_photo_dir):
        """Test photos property auto-scans."""
        manager = PhotoManager(temp_photo_dir)
        photos = manager.photos

        assert len(photos) == 3

    def test_list_photos_sort_by_name(self, temp_photo_dir):
        """Test listing photos sorted by name."""
        manager = PhotoManager(temp_photo_dir)
        photos = manager.list_photos(sort_by='name')

        names = [p.name for p in photos]
        assert names == sorted(names, key=str.lower)

    def test_list_photos_sort_by_size(self, temp_photo_dir):
        """Test listing photos sorted by size."""
        manager = PhotoManager(temp_photo_dir)
        photos = manager.list_photos(sort_by='size')

        sizes = [p.size for p in photos]
        assert sizes == sorted(sizes)

    def test_list_photos_reverse(self, temp_photo_dir):
        """Test listing photos in reverse order."""
        manager = PhotoManager(temp_photo_dir)
        photos = manager.list_photos(sort_by='name', reverse=True)

        names = [p.name for p in photos]
        assert names == sorted(names, key=str.lower, reverse=True)

    def test_search_by_name(self, temp_photo_dir):
        """Test searching photos by name."""
        manager = PhotoManager(temp_photo_dir)
        results = manager.search(name_pattern='photo')

        assert len(results) == 2
        assert all('photo' in p.name.lower() for p in results)

    def test_search_by_extension(self, temp_photo_dir):
        """Test searching photos by extension."""
        manager = PhotoManager(temp_photo_dir)
        results = manager.search(extensions=['png'])

        assert len(results) == 1
        assert results[0].extension == '.png'

    def test_search_by_size(self, temp_photo_dir):
        """Test searching photos by size."""
        manager = PhotoManager(temp_photo_dir)
        results = manager.search(min_size=1, max_size=100)

        assert len(results) > 0
        assert all(1 <= p.size <= 100 for p in results)

    def test_search_no_results(self, temp_photo_dir):
        """Test search with no matching results."""
        manager = PhotoManager(temp_photo_dir)
        results = manager.search(name_pattern='nonexistent')

        assert len(results) == 0

    def test_organize_by_date_copy(self, temp_photo_dir, empty_dir):
        """Test organizing photos by date (copy mode)."""
        manager = PhotoManager(temp_photo_dir)
        output_dir = os.path.join(empty_dir, 'organized')

        results = manager.organize_by_date(output_dir=output_dir, copy=True)

        # Check files were copied
        assert len(results) > 0

        # Original files should still exist
        assert os.path.exists(os.path.join(temp_photo_dir, 'photo1.jpg'))

    def test_organize_by_date_move(self, empty_dir):
        """Test organizing photos by date (move mode)."""
        # Create source directory with images
        source_dir = os.path.join(empty_dir, 'source')
        os.makedirs(source_dir)

        # Create a test image
        source_file = os.path.join(source_dir, 'test.jpg')
        with open(source_file, 'wb') as f:
            f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9')

        output_dir = os.path.join(empty_dir, 'organized')

        manager = PhotoManager(source_dir)
        results = manager.organize_by_date(output_dir=output_dir, copy=False)

        # Check file was moved
        assert len(results) == 1
        assert not os.path.exists(source_file)

    def test_get_statistics(self, temp_photo_dir):
        """Test getting statistics."""
        manager = PhotoManager(temp_photo_dir)
        stats = manager.get_statistics()

        assert stats['total_count'] == 3
        assert stats['total_size'] > 0
        assert '.jpg' in stats['extensions']
        assert '.png' in stats['extensions']

    def test_get_statistics_empty(self, empty_dir):
        """Test statistics for empty directory."""
        manager = PhotoManager(empty_dir)
        stats = manager.get_statistics()

        assert stats['total_count'] == 0
        assert stats['total_size'] == 0
        assert stats['extensions'] == {}

    def test_len(self, temp_photo_dir):
        """Test __len__ method."""
        manager = PhotoManager(temp_photo_dir)
        assert len(manager) == 3

    def test_repr(self, temp_photo_dir):
        """Test __repr__ method."""
        manager = PhotoManager(temp_photo_dir)
        repr_str = repr(manager)
        assert 'PhotoManager' in repr_str
