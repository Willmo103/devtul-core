import sys
import platform
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from devtul_core.fs_models import (
    BaseFileStatModel,
    MacOSFileStatModel,
    WindowsFileStatModel,
    LinuxFileStatModel,
    PathModel,
    FileLinesModel,
    FileLineModel,
    ImageFileModel,
    BaseDirectoryModel,
    get_file_stat_model,
    get_path_model,
    get_file_sha256
)

# --- Helper Tests ---

def test_get_file_sha256(tmp_path):
    f = tmp_path / "test.txt"
    content = b"hello world"
    f.write_bytes(content)

    # Known SHA256 for "hello world"
    expected_hash = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    assert get_file_sha256(f) == expected_hash

# --- OS Specific Stat Tests ---

@patch("platform.system")
def test_get_stat_model_macos(mock_system, tmp_path):
    mock_system.return_value = "Darwin"
    f = tmp_path / "mac_test.txt"
    f.touch()

    model = get_file_stat_model(f)
    assert isinstance(model, MacOSFileStatModel)
    # Ensure base fields are populated
    assert model.st_size == 0

@patch("platform.system")
def test_get_stat_model_windows(mock_system, tmp_path):
    mock_system.return_value = "Windows"
    f = tmp_path / "win_test.txt"
    f.touch()

    model = get_file_stat_model(f)
    assert isinstance(model, WindowsFileStatModel)

@patch("platform.system")
def test_get_stat_model_linux(mock_system, tmp_path):
    mock_system.return_value = "Linux"
    f = tmp_path / "lin_test.txt"
    f.touch()

    model = get_file_stat_model(f)
    assert isinstance(model, LinuxFileStatModel)

# --- Path Model Tests ---

def test_path_model(tmp_path):
    f = tmp_path / "subdir" / "file.txt"
    model = get_path_model(f)

    assert model.name == "file.txt"
    assert model.suffix == ".txt"
    assert "subdir" in model.parts

    # Test YAML serialization
    yaml_out = model.to_yaml()
    assert "name: file.txt" in yaml_out

# --- File Content Logic Tests ---

def test_file_lines_logic():
    lines = [
        FileLineModel(content="def hello():", line_number=1),
        FileLineModel(content="    return True", line_number=2),
        FileLineModel(content="# TODO: Fix this", line_number=3),
    ]
    model = FileLinesModel(lines=lines)

    assert model.line_count == 3

    # Test search
    results = model.search_lines("TODO")
    assert len(results) == 1
    assert results[0].line_number == 3

# --- Image Model Tests ---

def test_image_thumbnail_tag():
    # Note: Assuming 'thubnail_b64_data' as per your code,
    # if you fixed the typo change this to 'thumbnail_b64_data'
    img = ImageFileModel(
        sha256="abc",
        stat_json=BaseFileStatModel(),
        path_json=get_path_model(Path("test.png")),
        b64_data="realdata",
        thubnail_b64_data="thumbdata",
        fmt="png"
    )

    tag = img.thumbnail_tag()
    assert '<img src="data:image/png;base64,thumbdata"' in tag

# --- Directory Recursion Tests ---

def test_directory_model(tmp_path):
    # Setup: root -> file1, subdir -> file2
    (tmp_path / "file1.txt").touch()
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (subdir / "file2.txt").touch()

    # Manual construction test (since we don't have a get_dir_model helper yet)
    # This validates the model structure handles recursion
    dir_model = BaseDirectoryModel(
        path_json=get_path_model(tmp_path),
        stat_json=get_file_stat_model(tmp_path),
        directories=[
            BaseDirectoryModel(
                path_json=get_path_model(subdir),
                stat_json=get_file_stat_model(subdir)
            )
        ]
    )

    assert len(dir_model.directories) == 1
    assert dir_model.directories[0].path_json.name == "subdir"
