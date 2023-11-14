import json

from enum import IntEnum

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
