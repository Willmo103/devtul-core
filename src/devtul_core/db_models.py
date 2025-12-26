from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# --- Core Hierarchy Models ---


class Repository(Base):
    """The top-level identity of a repo (e.g., 'devtul-core')."""

    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    path: Mapped[str] = mapped_column(String)  # Local path on disk

    snapshots: Mapped[List["RepoSnapshot"]] = relationship(back_populates="repository")


class RepoSnapshot(Base):
    """
    Represents a specific scan event.
    Acts as the entry point to a file tree version.
    """

    __tablename__ = "repo_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"))
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # The root of the file tree for this snapshot
    root_directory_id: Mapped[int] = mapped_column(ForeignKey("directories.id"))

    repository: Mapped["Repository"] = relationship(back_populates="snapshots")
    root_directory: Mapped["Directory"] = relationship()


class Directory(Base):
    """
    Represents a folder. Self-referential for the tree structure.
    """

    __tablename__ = "directories"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("directories.id"))

    # PathModel fields flattened
    name: Mapped[str] = mapped_column(String)
    path: Mapped[str] = mapped_column(String, index=True)  # Full relative path

    # StatModel fields (common)
    st_size: Mapped[int] = mapped_column(Integer, default=0)
    st_mtime: Mapped[float] = mapped_column(Float, default=0.0)

    # Relationships
    subdirectories: Mapped[List["Directory"]] = relationship(
        back_populates="parent", cascade="all, delete-orphan"
    )
    parent: Mapped[Optional["Directory"]] = relationship(
        back_populates="subdirectories", remote_side=[id]
    )
    files: Mapped[List["FileBase"]] = relationship(
        back_populates="directory", cascade="all, delete-orphan"
    )


# --- File Polymorphism ---


class FileBase(Base):
    """
    Base table for all files. Contains shared metadata.
    """

    __tablename__ = "files"

    id: Mapped[int] = mapped_column(primary_key=True)
    directory_id: Mapped[int] = mapped_column(ForeignKey("directories.id"))

    # Polymorphic Identity
    type: Mapped[str] = mapped_column(String(20))

    # Shared Fields
    name: Mapped[str] = mapped_column(String)
    path: Mapped[str] = mapped_column(String, index=True)  # Full relative path
    sha256: Mapped[Optional[str]] = mapped_column(String(64))

    # Stat Fields
    st_size: Mapped[int] = mapped_column(Integer, default=0)
    st_mtime: Mapped[float] = mapped_column(Float, default=0.0)
    st_ctime: Mapped[float] = mapped_column(Float, default=0.0)

    directory: Mapped["Directory"] = relationship(back_populates="files")

    __mapper_args__ = {
        "polymorphic_identity": "file",
        "polymorphic_on": "type",
    }


class TextFile(FileBase):
    """
    Specific storage for text files.
    """

    __tablename__ = "text_files"

    id: Mapped[int] = mapped_column(ForeignKey("files.id"), primary_key=True)
    content: Mapped[Optional[str]] = mapped_column(Text)
    line_count: Mapped[int] = mapped_column(Integer, default=0)

    # We can store the detailed line breakdown as JSON if needed
    lines_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)

    __mapper_args__ = {
        "polymorphic_identity": "text",
    }


class ImageFile(FileBase):
    """
    Specific storage for image files.
    """

    __tablename__ = "image_files"

    id: Mapped[int] = mapped_column(ForeignKey("files.id"), primary_key=True)
    format: Mapped[Optional[str]] = mapped_column(String(10))
    width: Mapped[Optional[int]] = mapped_column(Integer)
    height: Mapped[Optional[int]] = mapped_column(Integer)

    # Base64 data (store carefully, can be large)
    b64_data: Mapped[Optional[str]] = mapped_column(Text)

    __mapper_args__ = {
        "polymorphic_identity": "image",
    }
