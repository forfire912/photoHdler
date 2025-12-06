"""Tests for the Photo class."""

import os
import tempfile
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from photohdler.photo import Photo


@pytest.fixture
def temp_image():
    """Create a temporary image file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
        # Create a minimal JPEG file (just the header)
        f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00')
        f.write(b'\xff\xdb\x00C\x00')  # DQT marker
        f.write(bytes([8] * 64))  # Quantization table
        f.write(b'\xff\xd9')  # EOI marker
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def temp_png():
    """Create a temporary PNG file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        # Minimal PNG header
        f.write(b'\x89PNG\r\n\x1a\n')
        temp_path = f.name

    yield temp_path

    if os.path.exists(temp_path):
        os.unlink(temp_path)


class TestPhoto:
    """Tests for Photo class."""

    def test_init_valid_image(self, temp_image):
        """Test Photo initialization with valid image."""
        photo = Photo(temp_image)
        assert photo.path == os.path.abspath(temp_image)
        assert photo.name == os.path.basename(temp_image)
        assert photo.size > 0

    def test_init_file_not_found(self):
        """Test Photo initialization with non-existent file."""
        with pytest.raises(FileNotFoundError):
            Photo('/nonexistent/path/image.jpg')

    def test_init_unsupported_format(self):
        """Test Photo initialization with unsupported format."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b'not an image')
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Unsupported image format"):
                Photo(temp_path)
        finally:
            os.unlink(temp_path)

    def test_supported_extensions(self, temp_png):
        """Test that PNG files are supported."""
        photo = Photo(temp_png)
        assert photo.extension == '.png'

    def test_properties(self, temp_image):
        """Test Photo properties."""
        photo = Photo(temp_image)

        assert isinstance(photo.name, str)
        assert isinstance(photo.size, int)
        assert isinstance(photo.modified_time, datetime)
        assert isinstance(photo.created_time, datetime)
        assert photo.extension == '.jpg'

    def test_get_exif_data_no_pillow(self, temp_image):
        """Test get_exif_data when Pillow is not available."""
        photo = Photo(temp_image)

        with patch.dict('sys.modules', {'PIL': None, 'PIL.Image': None}):
            exif = photo.get_exif_data()
            # Should return empty dict or cached result
            assert isinstance(exif, dict)

    def test_get_date_taken_fallback(self, temp_image):
        """Test get_date_taken falls back to modified time."""
        photo = Photo(temp_image)
        date_taken = photo.get_date_taken()
        assert date_taken is not None
        assert isinstance(date_taken, datetime)

    def test_repr(self, temp_image):
        """Test Photo __repr__."""
        photo = Photo(temp_image)
        repr_str = repr(photo)
        assert 'Photo' in repr_str
        assert photo.path in repr_str

    def test_str(self, temp_image):
        """Test Photo __str__."""
        photo = Photo(temp_image)
        assert str(photo) == photo.name
