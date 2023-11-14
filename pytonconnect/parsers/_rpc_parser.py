from abc import ABCMeta, abstractmethod


class RpcParser(metaclass=ABCMeta):

    @abstractmethod
    def convert_to_rpc_request(*args, **kwargs) -> dict:
        raise NotImplementedError

    @abstractmethod
    def convert_from_rpc_response(rpc_response: dict) -> dict:
        raise NotImplementedError

    @abstractmethod
    def parse_and_throw_error(response: dict) -> None:
        raise NotImplementedError

    def is_error(response: dict) -> bool:
        return 'error' in response
