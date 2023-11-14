from abc import ABCMeta, abstractmethod


class IStorage(metaclass=ABCMeta):

    KEY_LAST_EVENT_ID = 'last_event_id'
    KEY_CONNECTION = 'connection'

    @abstractmethod
    async def set_item(self, key: str, value: str):
        """Saves the `value` to the storage. Value can be accessed later by the `key`.

        :param key: key to access to the value later
        :param value: value to save
        """
        raise NotImplementedError

    @abstractmethod
    async def get_item(self, key: str, default_value: str = None):
        """Reads the `value` from the storage.

        :param key: key to access the value
        :param default_value: default value if key not found in storage
        """
        raise NotImplementedError

    @abstractmethod
    async def remove_item(self, key: str):
        """Removes the `value` from the storage.

        :param key: key to remove the value
        """
        raise NotImplementedError
