"""Archive reader imports once, preserving career rows and both original stores."""
from datetime import datetime
from pathlib import Path
import sqlite3

from backend.core.storage import init_db
from backend.core.run_lock import collection_lock


def separate_pipelines(db_path, reader_data_dir):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with collection_lock(db_path.parent / ".collection.lock"):
        return _separate_pipelines(db_path, reader_data_dir)


def _separate_pipelines(db_path, reader_data_dir):
    db_path, reader_data_dir = Path(db_path), Path(reader_data_dir)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path, timeout=30) as source:
        init_db(source)
        if source.execute("SELECT 1 FROM platform_settings WHERE key='separate_pipelines_v1'").fetchone():
            return {"archived": 0, "already_separate": True}
        count = source.execute("SELECT COUNT(*) FROM jobs WHERE source GLOB 'reader_*'").fetchone()[0]
        backup_path = archive_path = None
        if count:
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            backup_dir = db_path.parent / "backups"
            backup_dir.mkdir(exist_ok=True)
            backup_path = backup_dir / f"before-separation-{stamp}.db"
            with sqlite3.connect(backup_path) as backup:
                source.backup(backup)
            reader_data_dir.mkdir(parents=True, exist_ok=True)
            archive_path = reader_data_dir / "previous_platform_imports.sqlite3"
            with sqlite3.connect(archive_path) as archive:
                for table, where in (("jobs", "WHERE source GLOB 'reader_*'"), ("job_origins", ""), ("reader_files", "")):
                    schema = source.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()[0]
                    archive.execute(schema.replace("CREATE TABLE ", "CREATE TABLE IF NOT EXISTS ", 1))
                    rows = source.execute(f"SELECT * FROM {table} {where}").fetchall()
                    if rows:
                        slots = ",".join("?" for _ in rows[0])
                        archive.executemany(f"INSERT OR REPLACE INTO {table} VALUES({slots})", rows)
                archive.commit()
                archived_count = archive.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
                if archived_count < count:
                    raise RuntimeError("Reader history was not completely archived; career data has not been removed.")
        # The archive commits before any active rows are removed. A failure
        # here leaves recoverable copies and does not mark migration complete.
        with source:
            source.execute("DELETE FROM jobs WHERE source GLOB 'reader_*'")
            source.execute("DELETE FROM job_origins")
            source.execute("DELETE FROM reader_files")
            source.execute("INSERT INTO platform_settings VALUES('separate_pipelines_v1','1')")
    return {"archived": count, "already_separate": False,
            "backup": str(backup_path) if backup_path else None,
            "archive": str(archive_path) if archive_path else None}
