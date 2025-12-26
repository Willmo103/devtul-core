from pydantic import BaseModel, computed_field
from pathlib import Path
from os import stat
import yaml
from datetime import datetime
from typing import Any, Optional
import platform


class BaseFileStatModel(BaseModel):
    """
    A Pydantic model to represent file statistics.
    """

    st_mode: Optional[int] = None
    st_ino: Optional[int] = None
    st_dev: Optional[int] = None
    st_nlink: Optional[int] = None
    st_uid: Optional[int] = None
    st_gid: Optional[int] = None
    st_size: Optional[int] = None

    st_atime: Optional[float] = None
    st_mtime: Optional[float] = None
    st_ctime: Optional[float] = None

    st_atime_ns: Optional[int] = None
    st_mtime_ns: Optional[int] = None
    st_ctime_ns: Optional[int] = None

    st_blocks: Optional[int] = None
    st_blksize: Optional[int] = None
    st_rdev: Optional[int] = None

    def to_yaml(self) -> str:
        """
        Serialize the model to a YAML string.
        """
        return yaml.dump(self.model_dump(), sort_keys=False)

    @classmethod
    def from_yaml(cls, yaml_str: str):
        """
        Deserialize a YAML string to an instance of the model.
        """
        data = yaml.safe_load(yaml_str)
        return cls.model_validate(data)

    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat(),
        }
    }


class MacOSFileStatModel(BaseFileStatModel):
    """
    A Pydantic model to represent macOS/BSD specific file statistics.
    """

    # macOS/BSD-specific
    st_flags: Optional[int] = None
    st_gen: Optional[int] = None
    st_birthtime: Optional[float] = None

    model_config = {
        "ignore_extra": True,
        **BaseFileStatModel.model_config,
    }


class WindowsFileStatModel(BaseFileStatModel):
    """
    A Pydantic model to represent Windows-specific file statistics.
    """

    # Windows-specific
    st_file_attributes: Optional[int] = None
    st_reparse_tag: Optional[int] = None

    model_config = {
        "ignore_extra": True,
        **BaseFileStatModel.model_config,
    }


class LinuxFileStatModel(BaseFileStatModel):
    """
    A Pydantic model to represent Linux-specific file statistics.
    """

    # Linux-specific
    st_atim: Optional[float] = None
    st_mtim: Optional[float] = None
    st_ctim: Optional[float] = None
    st_ctimensec: Optional[int] = None
    st_mtimensec: Optional[int] = None
    st_atimensec: Optional[int] = None

    model_config = {
        "ignore_extra": True,
        **BaseFileStatModel.model_config,
    }


class PathModel(BaseModel):
    """
    A Pydantic model to represent pathlib.Path attributes.
    """

    name: str
    suffix: str
    suffixes: list[str]
    stem: str
    parent: str
    parents: list[str]
    anchor: str
    drive: str
    root: str
    parts: list[str]
    is_absolute: bool

    def to_yaml(self) -> str:
        """
        Serialize the model to a YAML string.
        """
        return yaml.dump(self.model_dump(), sort_keys=False)

    @classmethod
    def from_yaml(cls, yaml_str: str):
        """
        Deserialize a YAML string to an instance of the model.
        """
        data = yaml.safe_load(yaml_str)
        return cls.model_validate(data)

    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat(),
            tuple: lambda v: list(v),
        }
    }


def get_file_sha256(file_path: Path) -> str:
    """
    Calculate the SHA256 hash of a file.
    """
    import hashlib

    sha256_hash = hashlib.sha256()
    with file_path.open("rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def get_file_stat_model(file_path: Path) -> BaseFileStatModel:
    """
    Get the appropriate file stat model based on the operating system.
    """
    file_stat = stat(file_path)

    system = platform.system()
    if system == "Darwin":
        return MacOSFileStatModel.model_validate(
            {
                stat_key: getattr(file_stat, stat_key)
                for stat_key in dir(file_stat)
                if not stat_key.startswith("_")
            }
        )
    elif system == "Windows":
        return WindowsFileStatModel.model_validate(
            {
                stat_key: getattr(file_stat, stat_key)
                for stat_key in dir(file_stat)
                if not stat_key.startswith("_")
            }
        )
    elif system == "Linux":
        return LinuxFileStatModel.model_validate(
            {
                stat_key: getattr(file_stat, stat_key)
                for stat_key in dir(file_stat)
                if not stat_key.startswith("_")
            }
        )
    else:
        return BaseFileStatModel.model_validate(
            {
                stat_key: getattr(file_stat, stat_key)
                for stat_key in dir(file_stat)
                if not stat_key.startswith("_")
            }
        )


def get_path_model(file_path: Path) -> PathModel:
    """
    Get the PathModel for a given file path.
    """
    return PathModel(
        name=file_path.name,
        suffix=file_path.suffix,
        suffixes=file_path.suffixes,
        stem=file_path.stem,
        parent=str(file_path.parent),
        parents=[str(p) for p in file_path.parents],
        anchor=file_path.anchor,
        drive=file_path.drive,
        root=file_path.root,
        parts=[p for p in file_path.parts],
        is_absolute=file_path.is_absolute(),
    )


class FileLineModel(BaseModel):
    """
    A Pydantic model to represent a line in a file with its content and line number.
    """

    content: str
    line_number: int

    model_config = {
        "json_encoders": {
            str: lambda v: str(v).strip() if str(v).strip() != "" else "",
        }
    }


class FileLinesModel(BaseModel):
    """
    A Pydantic model to represent multiple lines in a file.
    """

    lines: list[FileLineModel]

    @computed_field
    def line_count(self) -> int:
        return len(self.lines)

    def get_lines(self, start: int, end: int) -> list[FileLineModel]:
        return self.lines[start:end]

    def search_lines(self, keyword: str) -> list[FileLineModel]:
        return [line for line in self.lines if keyword in line.content]

    model_config = {
        "json_encoders": {
            FileLineModel: lambda v: v.model_dump(),
        }
    }


class BaseFileModel(BaseModel):
    """
    A Pydantic model to represent a file with its path, SHA256 hash, and file statistics.
    """

    sha256: str
    stat_json: BaseFileStatModel
    path_json: PathModel

    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat(),
            BaseFileStatModel: lambda v: v.model_dump(),
            PathModel: lambda v: v.model_dump(),
        },
        "arbitrary_types_allowed": True,
    }


class TextFileModel(BaseFileModel):
    """
    A Pydantic model to represent a text file with its lines.
    """

    content: str
    lines_json: FileLinesModel

    model_config = {
        **BaseFileModel.model_config,
        "json_encoders": {
            **BaseFileModel.model_config["json_encoders"],
            FileLinesModel: lambda v: v.model_dump(),
        },
    }


class ImageFileModel(BaseFileModel):
    """
    A Pydantic model to represent an image file with its dimensions.
    """

    b64_data: str
    thubnail_b64_data: Optional[str] = None
    exif_data: dict[str, Any] = {}
    fmt: Optional[str] = None

    def thumbnail_tag(self) -> Optional[str]:
        if self.thubnail_b64_data and self.fmt:
            return f'<img src="data:image/{self.fmt};base64,{self.thubnail_b64_data}" alt="Thumbnail"/>'
        return None

    model_config = {
        **BaseFileModel.model_config,
        "json_encoders": {
            **BaseFileModel.model_config["json_encoders"],
        },
    }


class BaseDirectoryModel(BaseModel):
    """
    A Pydantic model to represent a directory with its path and file statistics.
    """

    path_json: PathModel
    stat_json: BaseFileStatModel
    files: list[BaseFileModel] = []
    directories: list["BaseDirectoryModel"] = []

    model_config = {
        "json_encoders": {
            PathModel: lambda v: v.model_dump(),
            BaseFileStatModel: lambda v: v.model_dump(),
            "BaseDirectoryModel": lambda v: v.model_dump(),
        },
        "arbitrary_types_allowed": True,
    }


BaseDirectoryModel.model_rebuild()  # For self-referencing models
