from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# --- Repository / Snapshot Context ---


class Repository(Base):
    """Identity of the repo."""

    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    path: Mapped[str] = mapped_column(String)  # Local path root

    snapshots: Mapped[List["RepoSnapshot"]] = relationship(back_populates="repository")


class RepoSnapshot(Base):
    """
    A lookup table linking a specific scan time to a collection of files.
    """

    __tablename__ = "repo_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"))
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    repository: Mapped["Repository"] = relationship(back_populates="snapshots")
    files: Mapped[List["FileModel"]] = relationship(
        back_populates="snapshot", cascade="all, delete-orphan"
    )


# --- 1:1 File Models ---


class FileModel(Base):
    """
    Direct mapping of BaseFileModel.
    """

    __tablename__ = "files"

    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("repo_snapshots.id"), index=True
    )

    # Polymorphic Identity
    type: Mapped[str] = mapped_column(String(20))

    # 1:1 Fields from Pydantic
    sha256: Mapped[str] = mapped_column(String(64))

    # Storing the exact Pydantic nested models as JSON
    path_json: Mapped[Dict[str, Any]] = mapped_column(JSON)
    stat_json: Mapped[Dict[str, Any]] = mapped_column(JSON)

    snapshot: Mapped["RepoSnapshot"] = relationship(back_populates="files")

    __mapper_args__ = {
        "polymorphic_identity": "file",
        "polymorphic_on": "type",
    }


class TextFileModel(FileModel):
    """
    Direct mapping of TextFileModel.
    """

    __tablename__ = "text_files"

    id: Mapped[int] = mapped_column(ForeignKey("files.id"), primary_key=True)

    content: Mapped[str] = mapped_column(Text)

    # Stores the FileLinesModel (list of FileLineModel)
    lines_json: Mapped[Dict[str, Any]] = mapped_column(JSON)

    __mapper_args__ = {
        "polymorphic_identity": "text",
    }


class ImageFileModel(FileModel):
    """
    Direct mapping of ImageFileModel.
    """

    __tablename__ = "image_files"

    id: Mapped[int] = mapped_column(ForeignKey("files.id"), primary_key=True)

    fmt: Mapped[Optional[str]] = mapped_column(String(10))
    b64_data: Mapped[str] = mapped_column(Text)
    thumbnail_b64_data: Mapped[Optional[str]] = mapped_column(Text)
    exif_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    __mapper_args__ = {
        "polymorphic_identity": "image",
    }
