import json

from dataclasses import dataclass
from enum import IntEnum
from typing import Optional

from pytonconnect.exceptions import TonConnectError, UnknownError, BadRequestError, UnknownAppError, UserRejectsError
from ._rpc_parser import RpcParser


class SEND_TRANSACTION_ERROR_CODES(IntEnum):
    UNKNOWN_ERROR = 0
    BAD_REQUEST_ERROR = 1
    UNKNOWN_APP_ERROR = 100
    USER_REJECTS_ERROR = 300
    METHOD_NOT_SUPPORTED = 400


SEND_TRANSACTION_ERRORS = {
    SEND_TRANSACTION_ERROR_CODES.UNKNOWN_ERROR: UnknownError,
    SEND_TRANSACTION_ERROR_CODES.BAD_REQUEST_ERROR: BadRequestError,
    SEND_TRANSACTION_ERROR_CODES.UNKNOWN_APP_ERROR: UnknownAppError,
    SEND_TRANSACTION_ERROR_CODES.USER_REJECTS_ERROR: UserRejectsError,
}


@dataclass
class TransactionMessage():
    address: str
    amount: int
    send_mode: int = 3  # SendModeEnum.ignore_errors | SendModeEnum.pay_gas_separately
    payload: Optional[str] = None
    state_init: Optional[str] = None

    def to_dict(cls):
        d = {
            'address': cls.address,
            'amount': cls.amount,
            'send_mode': cls.send_mode,
        }
        if cls.payload is not None:
            d['payload'] = cls.payload
        if cls.state_init is not None:
            d['state_init'] = cls.state_init
        return d

    @staticmethod
    def from_dict(d: dict):
        return TransactionMessage(
            address=d.get('address'),
            amount=d.get('amount'),
            send_mode=d.get('send_mode', 3),
            payload=d.get('payload', None),
            state_init=d.get('state_init', None),
        )


class SendTransactionParser(RpcParser):

    def convert_to_rpc_request(request: dict) -> dict:
        return {
            'method': 'sendTransaction',
            'params': [json.dumps(request)]
        }

    def convert_from_rpc_response(rpc_response: dict) -> dict:
        return {
            'boc': rpc_response['result']
        }

    def parse_and_throw_error(response: dict) -> None:
        error_constructor: TonConnectError = UnknownError

        code = response.get('error', {}).get('code', None)
        if code is not None and code in SEND_TRANSACTION_ERRORS:
            error_constructor = SEND_TRANSACTION_ERRORS[code]

        message = response.get('error', {}).get('message', None)
        raise error_constructor(message)
