from abc import ABCMeta, abstractmethod


class BaseProvider(metaclass=ABCMeta):

    @abstractmethod
    async def restore_connection(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def close_connection(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def disconnect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def send_request(self, request) -> None:
        raise NotImplementedError

    @abstractmethod
    def listen(self, eventsCallback) -> None:
        raise NotImplementedError
