"""Tests for the CLI module."""

import os
import sys
import tempfile
import shutil
from io import StringIO

import pytest

from photohdler.cli import main, format_size


@pytest.fixture
def temp_photo_dir():
    """Create a temporary directory with test images."""
    temp_dir = tempfile.mkdtemp()

    images = [
        ('photo1.jpg', b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9'),
        ('photo2.jpg', b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9'),
    ]

    for name, content in images:
        filepath = os.path.join(temp_dir, name)
        with open(filepath, 'wb') as f:
            f.write(content)

    yield temp_dir

    shutil.rmtree(temp_dir)


@pytest.fixture
def temp_image():
    """Create a single temporary image."""
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
        f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9')
        temp_path = f.name

    yield temp_path

    if os.path.exists(temp_path):
        os.unlink(temp_path)


class TestFormatSize:
    """Tests for format_size function."""

    def test_bytes(self):
        assert 'B' in format_size(500)

    def test_kilobytes(self):
        assert 'KB' in format_size(1500)

    def test_megabytes(self):
        assert 'MB' in format_size(1500000)

    def test_gigabytes(self):
        assert 'GB' in format_size(1500000000)


class TestCLI:
    """Tests for CLI commands."""

    def test_main_no_args(self, capsys):
        """Test main with no arguments shows help."""
        result = main([])
        assert result == 0

    def test_list_command(self, temp_photo_dir, capsys):
        """Test list command."""
        result = main(['list', temp_photo_dir])
        assert result == 0

        captured = capsys.readouterr()
        assert 'photo1.jpg' in captured.out
        assert 'photo2.jpg' in captured.out

    def test_list_command_empty(self, capsys):
        """Test list command with empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = main(['list', temp_dir])
            assert result == 0

            captured = capsys.readouterr()
            assert 'No photos found' in captured.out

    def test_list_command_sorted(self, temp_photo_dir, capsys):
        """Test list command with sorting."""
        result = main(['list', temp_photo_dir, '-s', 'size'])
        assert result == 0

    def test_search_command(self, temp_photo_dir, capsys):
        """Test search command."""
        result = main(['search', temp_photo_dir, '-n', 'photo1'])
        assert result == 0

        captured = capsys.readouterr()
        assert 'photo1' in captured.out

    def test_search_command_no_results(self, temp_photo_dir, capsys):
        """Test search command with no results."""
        result = main(['search', temp_photo_dir, '-n', 'nonexistent'])
        assert result == 0

        captured = capsys.readouterr()
        assert 'No matching photos' in captured.out

    def test_stats_command(self, temp_photo_dir, capsys):
        """Test stats command."""
        result = main(['stats', temp_photo_dir])
        assert result == 0

        captured = capsys.readouterr()
        assert 'Total photos: 2' in captured.out

    def test_info_command(self, temp_image, capsys):
        """Test info command."""
        result = main(['info', temp_image])
        assert result == 0

        captured = capsys.readouterr()
        assert 'Photo Information' in captured.out

    def test_info_command_file_not_found(self, capsys):
        """Test info command with non-existent file."""
        result = main(['info', '/nonexistent/file.jpg'])
        assert result == 1

        captured = capsys.readouterr()
        assert 'Error' in captured.out

    def test_organize_command(self, temp_photo_dir, capsys):
        """Test organize command."""
        with tempfile.TemporaryDirectory() as output_dir:
            result = main(['organize', temp_photo_dir, '-o', output_dir])
            assert result == 0

            captured = capsys.readouterr()
            assert 'Organized' in captured.out

    def test_organize_command_verbose(self, temp_photo_dir, capsys):
        """Test organize command with verbose output."""
        with tempfile.TemporaryDirectory() as output_dir:
            result = main(['organize', temp_photo_dir, '-o', output_dir, '-v'])
            assert result == 0
