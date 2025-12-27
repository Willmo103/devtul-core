from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# --- Parents ---


class Repository(Base):
    """Identity of the repo."""

    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    path: Mapped[str] = mapped_column(String)  # Local path root

    # One-to-Many to RepoSnapshot
    snapshots: Mapped[List["RepoSnapshot"]] = relationship(back_populates="repository")


class Folder(Base):
    """Identity of the Folder outside of a repo."""

    __tablename__ = "folders"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    path: Mapped[str] = mapped_column(String)  # Local path root

    # One-to-Many to FolderSnapshot
    snapshots: Mapped[List["FolderSnapshot"]] = relationship(back_populates="folder")


# --- Snapshots (Polymorphic) ---


class Snapshot(Base):
    """
    Base Snapshot class.
    Allows FileModel to point to a single 'snapshot_id' regardless of type.
    """

    __tablename__ = "snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Discriminator column (repo_snapshot vs folder_snapshot)
    type: Mapped[str] = mapped_column(String(20))

    # Relationship to files (Defined here so it works for both subclasses)
    files: Mapped[List["FileModel"]] = relationship(
        back_populates="snapshot", cascade="all, delete-orphan"
    )

    __mapper_args__ = {
        "polymorphic_identity": "snapshot",
        "polymorphic_on": "type",
    }


class RepoSnapshot(Snapshot):
    """
    Snapshot specific to a Repository.
    """

    __tablename__ = "repo_snapshots"

    # ID maps to the parent Snapshot ID
    id: Mapped[int] = mapped_column(ForeignKey("snapshots.id"), primary_key=True)

    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"))
    repository: Mapped["Repository"] = relationship(back_populates="snapshots")

    __mapper_args__ = {
        "polymorphic_identity": "repo_snapshot",
    }


class FolderSnapshot(Snapshot):
    """
    Snapshot specific to a standard Folder.
    """

    __tablename__ = "folder_snapshots"

    id: Mapped[int] = mapped_column(ForeignKey("snapshots.id"), primary_key=True)

    # FIXED: Was pointing to repositories.id
    folder_id: Mapped[int] = mapped_column(ForeignKey("folders.id"))
    folder: Mapped["Folder"] = relationship(back_populates="snapshots")

    __mapper_args__ = {
        "polymorphic_identity": "folder_snapshot",
    }


# --- Files (Polymorphic) ---


class FileModel(Base):
    """
    Direct mapping of BaseFileModel.
    Links to the parent Snapshot (which can be Repo or Folder).
    """

    __tablename__ = "files"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Points to the BASE Snapshot table, so it accepts either type
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("snapshots.id"), index=True)

    # Polymorphic Identity for File Types
    type: Mapped[str] = mapped_column(String(20))

    # 1:1 Fields from Pydantic
    sha256: Mapped[str] = mapped_column(String(64))

    # Storing the exact Pydantic nested models as JSON
    path_json: Mapped[Dict[str, Any]] = mapped_column(JSON)
    stat_json: Mapped[Dict[str, Any]] = mapped_column(JSON)

    snapshot: Mapped["Snapshot"] = relationship(back_populates="files")

    __mapper_args__ = {
        "polymorphic_identity": "file",
        "polymorphic_on": "type",
    }


class TextFileModel(FileModel):
    __tablename__ = "text_files"
    id: Mapped[int] = mapped_column(ForeignKey("files.id"), primary_key=True)
    content: Mapped[str] = mapped_column(Text)
    lines_json: Mapped[Dict[str, Any]] = mapped_column(JSON)

    __mapper_args__ = {
        "polymorphic_identity": "text",
    }


class ImageFileModel(FileModel):
    __tablename__ = "image_files"
    id: Mapped[int] = mapped_column(ForeignKey("files.id"), primary_key=True)
    fmt: Mapped[Optional[str]] = mapped_column(String(10))
    b64_data: Mapped[str] = mapped_column(Text)
    thumbnail_b64_data: Mapped[Optional[str]] = mapped_column(Text)
    exif_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    __mapper_args__ = {
        "polymorphic_identity": "image",
    }
