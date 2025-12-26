import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from devtul_core.fs_factory import FileSystemFactory
from devtul_core.fs_models import BaseDirectoryModel, BaseFileModel

# --- Fixtures ---


@pytest.fixture
def workspace(tmp_path):
    """Creates a dummy filesystem structure."""
    # Root files
    (tmp_path / "root_file.txt").write_text("content")
    (tmp_path / "ignored.pyc").write_text("binary")

    # Subdirectory
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("print('hello')")

    # Nested directory
    utils = src / "utils"
    utils.mkdir()
    (utils / "helper.py").write_text("def help(): pass")

    # Ignored directory
    venv = tmp_path / ".venv"
    venv.mkdir()
    (venv / "lib.py").write_text("library code")

    return tmp_path


# --- Tests ---


def test_fs_factory_scan_standard(workspace):
    """Test standard recursive scanning with default ignores."""
    factory = FileSystemFactory(workspace)
    model = factory.build()

    assert isinstance(model, BaseDirectoryModel)
    assert model.path_json.name == workspace.name

    # Check that root file exists
    file_names = [f.path_json.name for f in model.files]
    assert "root_file.txt" in file_names

    # Check that ignored file is excluded (.pyc is in default constants)
    assert "ignored.pyc" not in file_names

    # Check recursion
    dir_names = [d.path_json.name for d in model.directories]
    assert "src" in dir_names
    assert ".venv" not in dir_names  # Should be ignored by default IGNORE_PARTS


def test_fs_factory_nested_structure(workspace):
    """Verify the deep nesting structure."""
    factory = FileSystemFactory(workspace)
    model = factory.build()

    # Access: src -> utils -> helper.py
    src_dir = next(d for d in model.directories if d.path_json.name == "src")
    utils_dir = next(d for d in src_dir.directories if d.path_json.name == "utils")
    helper_file = next(f for f in utils_dir.files if f.path_json.name == "helper.py")

    assert helper_file.path_json.suffix == ".py"


def test_get_paths_list(workspace):
    """Verify flat list output."""
    factory = FileSystemFactory(workspace)
    paths = factory.get_paths_list()

    # Convert to filenames for easy checking
    names = [p.name for p in paths]
    assert "root_file.txt" in names
    assert "main.py" in names
    assert "helper.py" in names
    assert "lib.py" not in names  # Inside ignored folder


@patch("subprocess.run")
def test_git_scan_mode(mock_subprocess, workspace):
    """Test Git mode relies on subprocess output."""
    # 1. Create a fake .git directory so the factory logic accepts it
    (workspace / ".git").mkdir()

    # 2. Mock git ls-files output (git usually returns paths relative to root)
    mock_stdout = "root_file.txt\nsrc/main.py"

    mock_subprocess.return_value = MagicMock(
        stdout=mock_stdout, stderr="", returncode=0
    )

    factory = FileSystemFactory(workspace, git_mode=True)
    model = factory.build()

    paths = factory.get_paths_list()
    names = [p.name for p in paths]

    assert "root_file.txt" in names
    assert "main.py" in names
    # "helper.py" was not in our mocked git output, so it should be excluded
    # even though it exists on disk
    assert "helper.py" not in names


def test_json_output(workspace):
    """Verify hierarchical JSON export."""
    factory = FileSystemFactory(workspace)
    json_str = factory.to_json()
    data = json.loads(json_str)

    assert data["path_json"]["name"] == workspace.name
    assert len(data["files"]) > 0


def test_tree_output_string(workspace):
    """Verify the visual tree output generation."""
    factory = FileSystemFactory(workspace)
    tree_str = factory.to_tree()

    print(tree_str)  # Helpful for debugging on failure

    # Check for expected components regardless of sort order
    assert "src/" in tree_str
    assert "helper.py" in tree_str
    assert "ignored.pyc" not in tree_str  # Should definitely be gone now

    # Check a specific branch structure we know exists
    # "│   ├── utils/" or "    └── utils/" depending on position
    assert "utils/" in tree_str
