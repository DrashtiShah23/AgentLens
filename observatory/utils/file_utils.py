import hashlib
from pathlib import Path
from typing import Iterator


def list_json_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(directory.glob("*.json"))


def iter_json_files(directory: Path) -> Iterator[Path]:
    yield from list_json_files(directory)


def file_checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_empty_file(path: Path) -> bool:
    return path.exists() and path.stat().st_size == 0
