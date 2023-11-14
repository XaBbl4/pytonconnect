from ._interface import IStorage


class DefaultStorage(IStorage):

    _cache: dict

    def __init__(self):
        self._cache = {}

    async def set_item(self, key: str, value: str):
        self._cache[key] = value

    async def get_item(self, key: str, default_value: str = None):
        if key not in self._cache:
            return default_value
        return self._cache[key]

    async def remove_item(self, key: str):
        if key in self._cache:
            del self._cache[key]
