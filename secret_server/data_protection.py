import os
import platform
import json 

from base64 import (b64encode, b64decode)
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import (Cipher, algorithms, modes)


class DataProtection:
    SALT = os.urandom(64)
    FILE_Path = "creds.json"

    @classmethod
    def get_home_directory(cls):
        home_path = os.path.expanduser("~")
        if platform.system() is "Windows":
            home_path = os.path.join(home_path, "AppData", "Local")
            return home_path
        return home_path

    @classmethod
    def get_master_key(cls):
        path= os.path.join(cls.get_home_directory(), ".thycotic", "thycotic-sdk-client")
        name = os.path.join(path, "masterKey.config")
        try:
            if not os.path.exists(path):
                os.makedirs(path)
                master_key = b64encode(os.urandom(32))
                open(name, "w").write(master_key)
            else:
                master_key = open(name).read()
            return  master_key
        except IOError as e:
            raise IOError(e)
        except ValueError as e:
            raise ValueError(e)

    @classmethod
    def get_key(cls, salt):    
        backend = default_backend()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA512(),
            length=32,
            salt= salt,
            iterations=2145,
            backend=backend
        )
        try:
            return kdf.derive(cls.get_master_key())
        except IOError as e:
            raise IOError(e.message)

    @classmethod
    def encrypt(cls, data):

        salt = cls.SALT
        iv = os.urandom(16)
        encryptor = Cipher(
            algorithms.AES(cls.get_key(salt=salt)),
            modes.GCM(iv),
            backend = default_backend()
        ).encryptor()

        try:
            ciphertext = encryptor.update(json.dumps(data)) + encryptor.finalize()
            payload = salt + iv + encryptor.tag + ciphertext
        except Exception as e:
            raise Exception(e.message)
        
        try:
            open(cls.FILE_Path , "w").write(b64encode(payload))
        except IOError as e:
            raise IOError("Couldn't Save credentials: " + e.message)

    @classmethod
    def decrypt(cls):
        try:
            raw = b64decode(open(cls.FILE_Path, 'r').read())
        except IOError as e:
           "Couldn't load credentials: " + e.message
           raise
        #slice the bytes to get the salt, iv, tag, and the ciphertext
        salt =  raw[:64]
        iv = raw[64:80]
        tag = raw[80:96]
        ciphertext = raw[96:]

        decryptor = Cipher(
            algorithms.AES(cls.get_key(salt=salt)),
            modes.GCM(iv, tag),
            backend=default_backend()
        ).decryptor()
        try:
            return json.loads(decryptor.update(ciphertext) + decryptor.finalize())
        except Exception as e:
            raise Exception(e.message)