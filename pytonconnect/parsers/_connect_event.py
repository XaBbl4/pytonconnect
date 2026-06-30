from base64 import b64decode
from enum import IntEnum
from typing import List

from pytonconnect.exceptions import (BadRequestError,
                                     CheckProofIsDeprecatedError,
                                     ManifestContentError,
                                     ManifestNotFoundError, TonConnectError,
                                     UnknownAppError, UnknownError,
                                     UserRejectsError)


class CONNECT_EVENT_ERROR_CODES(IntEnum):
    UNKNOWN_ERROR = 0
    BAD_REQUEST_ERROR = 1
    MANIFEST_NOT_FOUND_ERROR = 2
    MANIFEST_CONTENT_ERROR = 3
    UNKNOWN_APP_ERROR = 100
    USER_REJECTS_ERROR = 300
    METHOD_NOT_SUPPORTED = 400


CONNECT_EVENT_ERRORS = {
    CONNECT_EVENT_ERROR_CODES.UNKNOWN_ERROR: UnknownError,
    CONNECT_EVENT_ERROR_CODES.BAD_REQUEST_ERROR: BadRequestError,
    CONNECT_EVENT_ERROR_CODES.UNKNOWN_APP_ERROR: UnknownAppError,
    CONNECT_EVENT_ERROR_CODES.USER_REJECTS_ERROR: UserRejectsError,
    CONNECT_EVENT_ERROR_CODES.USER_REJECTS_ERROR: ManifestNotFoundError,
    CONNECT_EVENT_ERROR_CODES.METHOD_NOT_SUPPORTED: ManifestContentError,
}


class CHAIN(IntEnum):
    MAINNET = '-239'
    TESTNET = '-3'


class DeviceInfo():

    platform: str  # 'iphone' | 'ipad' | 'android' | 'windows' | 'mac' | 'linux' | 'browser'
    app_name: str  # e.g. "Tonkeeper"
    app_version: str  # e.g. "2.3.367"
    max_protocol_version: int
    features: List[dict]

    def from_dict(device: dict):
        device_info = DeviceInfo()
        device_info.platform = device['platform']
        device_info.app_name = device['appName']
        device_info.app_version = device['appVersion']
        device_info.max_protocol_version = device['maxProtocolVersion']
        device_info.features = device['features']
        return device_info


class Account():

    # User's address in "hex" format: "<wc>:<hex>"
    address: str

    # User's selected chain
    chain: CHAIN

    # Base64 (not url safe) encoded wallet contract state_init.
    # Can be used to get user's public key from the state_init
    #   if the wallet contract doesn't support corresponding method
    wallet_state_init: str

    # Hex string without 0x prefix
    public_key: str

    def __repr__(self):
        return f'<Account "{self.address}">'

    def from_dict(ton_addr: dict):
        if 'address' not in ton_addr:
            raise TonConnectError('address not contains in ton_addr')

        account = Account()
        account.address = ton_addr['address']
        account.chain = ton_addr['network']
        account.wallet_state_init = ton_addr['walletStateInit']
        account.public_key = ton_addr.get('publicKey')
        return account


class TonProof():

    timestamp: int
    domain_len: int
    domain_val: str
    payload: str
    signature: bytes

    def from_dict(reply: dict):
        proof = reply.get('proof')
        if proof is None:
            raise TonConnectError('proof not contains in ton_proof')

        ton_proof = TonProof()
        ton_proof.timestamp = proof['timestamp']
        ton_proof.domain_len = proof['domain']['lengthBytes']
        ton_proof.domain_val = proof['domain']['value']
        ton_proof.payload = proof['payload']
        ton_proof.signature = b64decode(proof['signature'])
        return ton_proof


class WalletInfo():

    # Information about user's wallet's device
    device: DeviceInfo

    # Provider type
    provider: str

    # Selected account
    account: Account

    # Response for ton_proof item request
    ton_proof: TonProof

    def __repr__(self):
        return f'<WalletInfo {self.account}>'

    def __init__(self):
        self.device = None
        self.provider = 'http'  # only http supported
        self.account = None
        self.ton_proof = None

    def check_proof(self, src_payload: str = None) -> bool:
        raise CheckProofIsDeprecatedError()


class ConnectEventParser():

    def parse_response(payload: dict) -> WalletInfo:
        if 'items' not in payload:
            raise TonConnectError('items not contains in payload')

        wallet = WalletInfo()

        for item in payload['items']:
            if 'name' in item:
                if item['name'] == 'ton_addr':
                    wallet.account = Account.from_dict(item)
                elif item['name'] == 'ton_proof':
                    wallet.ton_proof = TonProof.from_dict(item)

        if wallet.account is None:
            raise TonConnectError('ton_addr not contains in items')

        wallet.device = DeviceInfo.from_dict(payload['device'])

        return wallet

    def parse_error(payload: dict) -> TonConnectError:
        error_constructor: TonConnectError = UnknownError

        code = payload.get('error', {}).get('code')
        if code is not None and code in CONNECT_EVENT_ERRORS:
            error_constructor = CONNECT_EVENT_ERRORS[code]

        message = payload.get('error', {}).get('message')
        return error_constructor(message)
