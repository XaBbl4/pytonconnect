import json

from ._interface import IStorage


class FileStorage(IStorage):

    _cache: dict
    _file_path: str

    def __init__(self, file_path: str, use_cache=True):
        self._file_path = file_path
        if use_cache:
            self._cache = {}
            try:
                with open(self._file_path, 'r') as f:
                    self._cache = json.loads(f.read())
            except Exception:
                pass
        else:
            self._cache = None

    def _read_from_file(self):
        with open(self._file_path, 'r') as f:
            return json.loads(f.read())

    def _write_to_file(self, d: dict):
        with open(self._file_path, 'w') as f:
            f.write(json.dumps(d))

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
