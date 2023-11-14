import json
from pytonconnect.crypto import SessionCrypto


class BridgeSession:

    session_crypto: SessionCrypto
    wallet_public_key: str
    bridge_url: str

    def __init__(self, stored: dict = None):
        self.session_crypto = SessionCrypto(stored['session_private_key']) \
                              if stored and 'session_private_key' in stored else None
        self.wallet_public_key = stored['wallet_public_key'] if stored and 'wallet_public_key' in stored else None
        self.bridge_url = stored['bridge_url'] if stored and 'bridge_url' in stored else None

    def __repr__(self):
        return json.dumps(self.get_dict())

    def get_dict(self):
        return {
            'session_private_key': self.session_crypto.key_pair.encode().hex(),
            'wallet_public_key': self.wallet_public_key,
            'bridge_url': self.bridge_url
        }
