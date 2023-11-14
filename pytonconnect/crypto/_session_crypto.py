from base64 import b64decode, b64encode
from nacl.utils import random
from nacl.public import PrivateKey, PublicKey, Box
from nacl.encoding import HexEncoder


class SessionCrypto:

    key_pair: PrivateKey
    session_id: str

    def __init__(self, private_key: str = None):
        self.key_pair = PrivateKey(private_key, HexEncoder) if private_key else PrivateKey.generate()
        self.session_id = self.key_pair.public_key.encode().hex()

    def create_nonce(self):
        return random(Box.NONCE_SIZE)

    def encrypt(self, message: str, receiver_pub_key_hex: str):
        nonce = self.create_nonce()

        receiver_pk = PublicKey(receiver_pub_key_hex, HexEncoder)
        box = Box(self.key_pair, receiver_pk)
        encrypted = box.encrypt(message.encode('utf-8'), nonce)

        res = bytearray(nonce)
        res.extend(encrypted.ciphertext)
        return b64encode(bytes(res))

    def decrypt(self, message: bytes, sender_pub_key_hex: str):
        msg = b64decode(message)
        nonce = msg[:Box.NONCE_SIZE]
        internal_message = msg[Box.NONCE_SIZE:]

        sender_pk = PublicKey(sender_pub_key_hex, HexEncoder)
        box = Box(self.key_pair, sender_pk)

        decrypted = box.decrypt(internal_message, nonce)
        return decrypted.decode('utf-8')
