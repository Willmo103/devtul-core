from pathlib import Path

from sqlalchemy.orm import Session

from devtul_core.db_models import (
    FileModel,
    Folder,
    FolderSnapshot,
    ImageFileModel,
    Repository,
    RepoSnapshot,
    TextFileModel,
)
from devtul_core.fs_models import (
    BaseDirectoryModel,
)
from devtul_core.fs_models import ImageFileModel as PyImageFile
from devtul_core.fs_models import TextFileModel as PyTextFile


def ingest_scan(
    session: Session,
    root_path: str,
    dir_model: BaseDirectoryModel,
    repo_name: str | None = None,
    folder_name: str | None = None,
):
    """
    Saves a Pydantic BaseDirectoryModel tree into the DB as a snapshot.
    """
    snapshot: RepoSnapshot | FolderSnapshot

    if folder_name and repo_name:
        raise ValueError("Specify either repo_name or folder_name, not both.")
    if not repo_name and not folder_name:
        folder_name = Path(root_path).name
    if repo_name:
        repo = session.query(Repository).filter_by(name=repo_name).first()
        if not repo:
            repo = Repository(name=repo_name, path=root_path)
            session.add(repo)
            session.flush()

        # 2. Create Snapshot
        snapshot = RepoSnapshot(repository_id=repo.id)
        session.add(snapshot)
        session.flush()
    elif folder_name:
        folder = session.query(Folder).filter_by(name=folder_name).first()
        if not folder:
            folder = Folder(name=folder_name, path=root_path)
            session.add(folder)
            session.flush()

        # 2. Create Snapshot
        snapshot = FolderSnapshot(folder_id=folder.id)
        session.add(snapshot)
        session.flush()

    # 3. Flatten and Save Files recursively
    def _recurse_save(directory):
        # Save files in this directory
        for p_file in directory.files:

            # Common Data
            common_data = {
                "snapshot_id": snapshot.id,
                "sha256": p_file.sha256,
                "path_json": p_file.path_json.model_dump(),
                "stat_json": p_file.stat_json.model_dump(),
            }

            if isinstance(p_file, PyTextFile):
                db_file = TextFileModel(
                    **common_data,
                    content=p_file.content,
                    lines_json=p_file.lines_json.model_dump(),
                )
            elif isinstance(p_file, PyImageFile):
                db_file = ImageFileModel(
                    **common_data,
                    b64_data=p_file.b64_data,
                    thumbnail_b64_data=p_file.thumbnail_b64_data,  # Matches Pydantic model field
                    exif_data=p_file.exif_data,
                    fmt=p_file.fmt,
                )
            else:
                # Fallback for generic binary files
                db_file = FileModel(**common_data)

            session.add(db_file)

        # Recurse
        for subdir in directory.directories:
            _recurse_save(subdir)

    _recurse_save(dir_model)
    session.commit()
    return snapshot
