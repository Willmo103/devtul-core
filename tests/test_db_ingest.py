from datetime import datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

# Import your DB models
from devtul_core.db_models import (
    Base,
    FileModel,
    ImageFileModel,
    Repository,
    RepoSnapshot,
    TextFileModel,
)

# Import your Pydantic models (for data construction)
from devtul_core.fs_models import (
    BaseDirectoryModel,
)
from devtul_core.fs_models import BaseFileModel as PyBaseFile
from devtul_core.fs_models import (
    BaseFileStatModel,
    FileLineModel,
    FileLinesModel,
)
from devtul_core.fs_models import ImageFileModel as PyImageFile
from devtul_core.fs_models import (
    PathModel,
)
from devtul_core.fs_models import TextFileModel as PyTextFile
from devtul_core.ingestor import ingest_scan

# --- Fixtures ---


@pytest.fixture
def db_session():
    """Creates an in-memory SQLite DB and returns a session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def mock_fs_data():
    """Creates a dummy Pydantic directory tree with all file types."""

    # 1. Helper Helpers
    def make_stat():
        return BaseFileStatModel(st_size=100, st_mtime=123456.7)

    def make_path(name, parent="root"):
        return PathModel(
            name=name,
            suffix="." + name.split(".")[-1],
            suffixes=[],
            stem=name.split(".")[0],
            parent=parent,
            parents=[],
            anchor="",
            drive="",
            root="",
            parts=[parent, name],
            is_absolute=True,
        )

    # 2. Text File
    txt_file = PyTextFile(
        sha256="hash_text",
        stat_json=make_stat(),
        path_json=make_path("readme.md"),
        content="Hello World",
        lines_json=FileLinesModel(
            lines=[FileLineModel(content="Hello World", line_number=1)]
        ),
    )

    # 3. Image File
    img_file = PyImageFile(
        sha256="hash_img",
        stat_json=make_stat(),
        path_json=make_path("logo.png"),
        b64_data="fakebase64",
        thubnail_b64_data="thumbbase64",  # Intentionally matching typo from your fs_models definition if needed
        fmt="png",
        exif_data={"camera": "canon"},
    )

    # 4. Generic/Binary File (BaseFileModel)
    bin_file = PyBaseFile(
        sha256="hash_bin", stat_json=make_stat(), path_json=make_path("data.bin")
    )

    # 5. Structure: Root -> [txt_file] -> Subdir -> [img_file, bin_file]
    subdir = BaseDirectoryModel(
        path_json=make_path("subdir"),
        stat_json=make_stat(),
        files=[img_file, bin_file],
        directories=[],
    )

    root = BaseDirectoryModel(
        path_json=make_path("root"),
        stat_json=make_stat(),
        files=[txt_file],
        directories=[subdir],
    )

    return root


# --- Tests ---


def test_ingest_creates_repo_and_snapshot(db_session, mock_fs_data):
    """Test that a new repo and snapshot are created."""
    snapshot = ingest_scan(db_session, "my-repo", "/tmp/root", mock_fs_data)

    # Verify Repo
    repo = db_session.execute(
        select(Repository).where(Repository.name == "my-repo")
    ).scalar_one()
    assert repo.path == "/tmp/root"

    # Verify Snapshot
    assert snapshot.repository_id == repo.id
    assert snapshot.files is not None


def test_ingest_reuses_existing_repo(db_session, mock_fs_data):
    """Test idempotency: Second scan should reuse repo but make new snapshot."""
    # First Scan
    ingest_scan(db_session, "my-repo", "/tmp/root", mock_fs_data)

    # Second Scan
    ingest_scan(db_session, "my-repo", "/tmp/root", mock_fs_data)

    # Checks
    repos = db_session.execute(select(Repository)).scalars().all()
    snapshots = db_session.execute(select(RepoSnapshot)).scalars().all()

    assert len(repos) == 1
    assert len(snapshots) == 2


def test_ingest_polymorphism(db_session, mock_fs_data):
    """Verify that Text, Image, and Generic files are saved to correct tables."""
    snapshot = ingest_scan(db_session, "poly-test", "/tmp", mock_fs_data)

    # Fetch all files associated with this snapshot
    files = (
        db_session.execute(
            select(FileModel).where(FileModel.snapshot_id == snapshot.id)
        )
        .scalars()
        .all()
    )

    assert len(files) == 3

    # 1. Check Text File
    text_file = next(f for f in files if f.path_json["name"] == "readme.md")
    assert isinstance(text_file, TextFileModel)
    assert text_file.type == "text"
    assert text_file.content == "Hello World"
    assert text_file.lines_json["lines"][0]["content"] == "Hello World"

    # 2. Check Image File
    img_file = next(f for f in files if f.path_json["name"] == "logo.png")
    assert isinstance(img_file, ImageFileModel)
    assert img_file.type == "image"
    assert img_file.fmt == "png"
    assert img_file.exif_data["camera"] == "canon"
    # Note: accessing thumbnail_b64_data vs thubnail_b64_data depending on if you fixed typo in ingestor
    assert img_file.thumbnail_b64_data == "thumbbase64"

    # 3. Check Generic File
    bin_file = next(f for f in files if f.path_json["name"] == "data.bin")
    # It should be exactly FileModel (or not one of the subclasses if query returns base)
    # SQLAlchemy polymorphism means it might be returned as FileModel but not satisfy subclass checks
    # Asserting strict type if we queried base might depend on mapping config,
    # but usually 'type' column is the giveaway.
    assert bin_file.type == "file"
    assert not isinstance(bin_file, TextFileModel)
    assert not isinstance(bin_file, ImageFileModel)


def test_json_field_storage(db_session, mock_fs_data):
    """Ensure Pydantic models serialized into JSON columns correctly."""
    ingest_scan(db_session, "json-test", "/tmp", mock_fs_data)

    # Retrieve a file
    file_record = db_session.execute(select(FileModel)).scalars().first()

    # Check Stat JSON (nested object)
    assert file_record.stat_json["st_size"] == 100

    # Check Path JSON
    assert file_record.path_json["parent"] == "root"
