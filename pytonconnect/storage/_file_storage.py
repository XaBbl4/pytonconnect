import json
from contextlib import suppress
from pathlib import Path

from ._interface import IStorage


class FileStorage(IStorage):

    _cache: dict
    _file_path: Path

    def __init__(self, file_path: str, use_cache=True):
        self._file_path = Path(file_path)
        if use_cache:
            self._cache = {}
            with suppress(Exception):
                self._cache = json.loads(self._file_path.read_text())
        else:
            self._cache = None

    def _read_from_file(self):
        return json.loads(self._file_path.read_text())

    def _write_to_file(self, d: dict):
        self._file_path.write_text(json.dumps(d))

    async def set_item(self, key: str, value: str):
        data = self._read_from_file() if self._cache is None else self._cache
        data[key] = value
        self._write_to_file(data)

    async def get_item(self, key: str, default_value: str = None):
        data = self._read_from_file() if self._cache is None else self._cache
        if key not in data:
            return default_value
        return data[key]

    async def remove_item(self, key: str):
        data = self._read_from_file() if self._cache is None else self._cache
        if key in data:
            del data[key]
            self._write_to_file(data)
