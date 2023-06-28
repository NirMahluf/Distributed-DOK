from random import randint
from Cryptodome import Random
from Cryptodome.Cipher import AES
from cryptography.hazmat.primitives import padding
import hashlib
import base64


class Security:
    """
    class to encrypt and decrypt data
    """
    def __init__(self):
        """
        initialize the chosen attributes
        """
        self.key = None
        self.P = 23
        self.g = 9
        self.a = None

    def create_public_key(self):
        """
        create the key supposed to be sent to the other member
        :return: the number generated
        """
        self.a = randint(0, 999999)
        public_key = (self.g ** self.a) % self.P
        return public_key

    def set_key(self, given_key):
        """
        finish the Diffie Hellman key exchange by
        setting the encryption key
        :param given_key: the key the other member generated
        :return: the final encryption key
        """
        self.key = str((int(given_key) ** self.a) % self.P)
        return self.key

    def encrypt(self, raw_msg, key=None):
        """
        encrypt given message
        :param raw_msg: the message to encrypt
        :param key: the encryption key
        :return: the encrypted message
        """
        if key is None:
            key = self.key
        key = hashlib.sha256(str(key).encode()).digest()
        raw_msg = self._pad(raw_msg.encode())
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw_msg))

    def encrypt_file(self, raw, key=None):
        """
        encrypt given file
        :param raw: the content of the file
        :param key: the encryption key
        :return: the encrypted file
        """
        if key is None:
            key = self.key
        key = hashlib.sha256(key.encode()).digest()
        raw = self._pad(raw)
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw))

    def decrypt(self, enc, key=None):
        """
        decrypt given file
        :param enc: the encrypted message
        :param key: the decryption key
        :return: the message decrypted
        """
        if key is None:
            key = self.key
        key = hashlib.sha256(key.encode()).digest()
        enc = base64.b64decode(enc)
        iv = enc[:AES.block_size]
        cipher = AES.new(key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size:])).decode('utf-8')

    def decrypt_file(self, enc, key=None):
        """
        decrypt given file
        :param enc: the file encrypted
        :param key: the decryption key
        :return: the file decrypted
        """
        if key is None:
            key = self.key
        key = hashlib.sha256(key.encode()).digest()
        enc = base64.b64decode(enc)
        iv = enc[:AES.block_size]
        cipher = AES.new(key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size:]))

    @staticmethod
    def _pad(s):
        block_size = AES.block_size
        padder = padding.PKCS7(block_size * 8).padder()
        padded_data = padder.update(s) + padder.finalize()
        return padded_data

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s)-1:])]
