"""
File-backed state helpers with cross-process locking and atomic JSON writes.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Generator, TypeVar

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows only
    fcntl = None  # type: ignore[assignment]

try:
    import msvcrt
except ImportError:  # pragma: no cover - Unix only
    msvcrt = None  # type: ignore[assignment]

T = TypeVar("T")

_LOCAL_LOCKS: dict[str, threading.RLock] = {}
_LOCAL_LOCKS_GUARD = threading.Lock()


def _get_local_lock(lock_path: Path) -> threading.RLock:
    key = str(lock_path.resolve())
    with _LOCAL_LOCKS_GUARD:
        if key not in _LOCAL_LOCKS:
            _LOCAL_LOCKS[key] = threading.RLock()
        return _LOCAL_LOCKS[key]


def _lock_file(file_obj) -> None:
    if fcntl is not None:
        fcntl.flock(file_obj.fileno(), fcntl.LOCK_EX)
        return
    if msvcrt is not None:  # pragma: no cover - Windows only
        file_obj.seek(0)
        msvcrt.locking(file_obj.fileno(), msvcrt.LK_LOCK, 1)
        return
    raise RuntimeError("No file locking implementation available")


def _unlock_file(file_obj) -> None:
    if fcntl is not None:
        fcntl.flock(file_obj.fileno(), fcntl.LOCK_UN)
        return
    if msvcrt is not None:  # pragma: no cover - Windows only
        file_obj.seek(0)
        msvcrt.locking(file_obj.fileno(), msvcrt.LK_UNLCK, 1)
        return
    raise RuntimeError("No file locking implementation available")


def _lock_path_for(path: Path) -> Path:
    return path.parent / f".{path.name}.lock"


def _load_json_unlocked(path: Path, default_factory: Callable[[], T]) -> T:
    if not path.exists():
        return default_factory()
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return default_factory()


def atomic_write_json(path: Path | str, data: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(
        dir=str(target.parent),
        prefix=f".{target.name}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, target)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def read_json_file(path: Path | str, default_factory: Callable[[], T]) -> T:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lock_path = _lock_path_for(target)
    local_lock = _get_local_lock(lock_path)

    with local_lock:
        with lock_path.open("a+b") as lock_handle:
            _lock_file(lock_handle)
            try:
                data = _load_json_unlocked(target, default_factory)
            finally:
                _unlock_file(lock_handle)
    return data


def write_json_file(path: Path | str, data: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lock_path = _lock_path_for(target)
    local_lock = _get_local_lock(lock_path)

    with local_lock:
        with lock_path.open("a+b") as lock_handle:
            _lock_file(lock_handle)
            try:
                atomic_write_json(target, data)
            finally:
                _unlock_file(lock_handle)


@contextmanager
def locked_json_state(
    path: Path | str,
    default_factory: Callable[[], T],
) -> Generator[T, None, None]:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lock_path = _lock_path_for(target)
    local_lock = _get_local_lock(lock_path)

    with local_lock:
        with lock_path.open("a+b") as lock_handle:
            _lock_file(lock_handle)
            data = _load_json_unlocked(target, default_factory)
            try:
                yield data
            except Exception:
                raise
            else:
                atomic_write_json(target, data)
            finally:
                _unlock_file(lock_handle)
