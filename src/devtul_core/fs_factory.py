import fnmatch
import os
import subprocess
from pathlib import Path
from typing import List, Optional, Set

from devtul_core.constants import IGNORE_EXTENSIONS, IGNORE_PARTS
from devtul_core.fs_models import (
    BaseDirectoryModel,
    BaseFileModel,
    get_file_sha256,
    get_file_stat_model,
    get_path_model,
)


class FileSystemFactory:
    def __init__(
        self,
        root: Path,
        git_mode: bool = False,
        ignore_parts: Optional[List[str]] = None,
        ignore_patterns: Optional[List[str]] = None,
    ):
        self.root = root.resolve()
        self.git_mode = git_mode
        self.ignore_parts = ignore_parts if ignore_parts is not None else IGNORE_PARTS
        self.ignore_patterns = (
            ignore_patterns if ignore_patterns is not None else IGNORE_EXTENSIONS
        )

        # Cache for the gathered paths to avoid re-scanning
        self._gathered_paths: Optional[List[Path]] = None
        self._model: Optional[BaseDirectoryModel] = None

    def build(self) -> BaseDirectoryModel:
        """
        Orchestrates the build process: scans, filters, and constructs the model.
        """
        if self._model:
            return self._model

        # 1. Gather raw paths
        paths = self._scan()

        # 2. Filter paths
        paths = self._filter(paths)
        self._gathered_paths = sorted(paths)

        # 3. Construct recursive model
        self._model = self._build_directory_recursive(self.root, self._gathered_paths)
        return self._model

    def get_paths_list(self) -> List[Path]:
        """Returns the flat list of allowed file paths."""
        if self._gathered_paths is None:
            self.build()
        return self._gathered_paths

    def to_json(self) -> str:
        """Returns the JSON representation of the hierarchical model."""
        if not self._model:
            self.build()
        return self._model.model_dump_json(indent=2)

    def to_tree(self) -> str:
        """Returns a visual tree string."""
        if self._gathered_paths is None:
            self.build()

        # We need relative paths for the tree builder logic
        rel_paths = [str(p.relative_to(self.root)) for p in self._gathered_paths]
        return self._generate_tree_string(rel_paths)

    # --- Internals ---

    def _scan(self) -> List[Path]:
        if self.git_mode:
            return self._scan_git()
        return self._scan_standard()

    def _scan_standard(self) -> List[Path]:
        all_paths = []
        for dirpath, _, filenames in os.walk(self.root):
            # Optimization: check if current dir is ignored before processing files
            d_path = Path(dirpath)
            if self._should_ignore(d_path):
                continue

            for f in filenames:
                full_path = d_path / f
                all_paths.append(full_path)
        return all_paths

    def _scan_git(self) -> List[Path]:
        # We check for .git directory existence to fail fast,
        # unless we are in a test context where we might want to force it
        if not (self.root / ".git").exists():
            print(
                f"Warning: No .git found at {self.root}, falling back to standard scan."
            )
            return self._scan_standard()

        tracked_paths = []
        shell = os.name == "nt"
        try:
            result = subprocess.run(
                ["git", "-C", str(self.root), "ls-files"],
                capture_output=True,
                text=True,
                check=True,
                shell=shell,
            )
            files = [f.strip() for f in result.stdout.splitlines() if f.strip()]
            for f in files:
                full_path = (self.root / f).resolve()
                if full_path.exists():  # Git might list deleted files
                    tracked_paths.append(full_path)
        except subprocess.CalledProcessError:
            return []

        return tracked_paths

    def _filter(self, paths: List[Path]) -> List[Path]:
        filtered = []
        for p in paths:
            if not self._should_ignore(p):
                filtered.append(p)
        return filtered

    def _should_ignore(self, path: Path) -> bool:
        path_str = str(path.as_posix())
        try:
            rel_parts = path.relative_to(self.root).parts
        except ValueError:
            # If path is not relative to root (shouldn't happen), use all parts
            rel_parts = path.parts

        # 1. Check Directory Parts (e.g., .venv, __pycache__)
        for part in rel_parts:
            if part in self.ignore_parts:
                return True

        # 2. Check File Extensions/Patterns
        for pattern in self.ignore_patterns:
            # Case A: Pattern matches suffix exactly (e.g. ".pyc" == ".pyc")
            if path.suffix == pattern:
                return True
            # Case B: Pattern is a glob (e.g. "*.tmp")
            if fnmatch.fnmatch(path.name, pattern):
                return True

        return False

    def _build_directory_recursive(
        self, current_path: Path, all_paths: List[Path]
    ) -> BaseDirectoryModel:
        current_files: List[BaseFileModel] = []
        current_subdirs: List[BaseDirectoryModel] = []

        # 1. Find files directly in this folder
        direct_files = [p for p in all_paths if p.parent == current_path]

        # 2. Find direct subdirectories that contain allowed files
        child_dirs_str: Set[str] = set()
        for p in all_paths:
            try:
                rel = p.relative_to(current_path)
                if len(rel.parts) > 1:
                    child_dirs_str.add(rel.parts[0])
            except ValueError:
                continue

        # Process Files
        for f_path in direct_files:
            try:
                stat = get_file_stat_model(f_path)
                path_model = get_path_model(f_path)
                sha = get_file_sha256(f_path)

                model = BaseFileModel(sha256=sha, stat_json=stat, path_json=path_model)
                current_files.append(model)
            except Exception as e:
                print(f"Error reading {f_path}: {e}")

        # Process Subdirectories
        for d_name in sorted(child_dirs_str):
            d_path = current_path / d_name
            subdir_model = self._build_directory_recursive(d_path, all_paths)
            current_subdirs.append(subdir_model)

        return BaseDirectoryModel(
            path_json=get_path_model(current_path),
            stat_json=get_file_stat_model(current_path),
            files=current_files,
            directories=current_subdirs,
        )

    def _generate_tree_string(self, rel_paths: List[str]) -> str:
        if not rel_paths:
            return ""

        # Build directory structure dict
        tree_dict = {}
        for file_path in sorted(rel_paths):
            parts = file_path.split("/")  # Assumes posix paths from relative_to
            if os.name == "nt":
                parts = file_path.split("\\")
                # Normalize back to forward slash for consistent internal processing
                parts = [p.replace("\\", "/") for p in parts]

            current = tree_dict
            for i, part in enumerate(parts):
                if i == len(parts) - 1:  # It's a file
                    if "__files__" not in current:
                        current["__files__"] = []
                    current["__files__"].append(part)
                else:  # It's a directory
                    if part not in current:
                        current[part] = {}
                    current = current[part]

        def render_tree(
            node: dict, prefix: str = "", is_last: bool = True
        ) -> List[str]:
            lines = []
            dirs = [
                (k, v)
                for k, v in node.items()
                if k != "__files__" and isinstance(v, dict)
            ]
            dirs.sort(key=lambda x: x[0])
            files = node.get("__files__", [])
            files.sort()

            all_items = [(name, "dir", content) for name, content in dirs] + [
                (name, "file", None) for name in files
            ]

            for i, (name, item_type, content) in enumerate(all_items):
                is_last_item = i == len(all_items) - 1
                symbol = "└── " if is_last_item else "├── "

                if item_type == "dir":
                    lines.append(f"{prefix}{symbol}{name}/")
                    next_prefix = prefix + ("    " if is_last_item else "│   ")
                    lines.extend(render_tree(content, next_prefix, is_last_item))
                else:
                    lines.append(f"{prefix}{symbol}{name}")
            return lines

        root_lines = [f"{self.root.name}/"]
        root_lines.extend(render_tree(tree_dict))
        return "\n".join(root_lines)
