import base64
import hashlib
import hmac

from Crypto.Cipher import AES


def hmac_for_key_and_data(key: bytes, data: bytes) -> bytes:
    mac_hash = hmac.new(key, data, hashlib.sha256)
    return mac_hash.digest()


def pad_zero(data: bytes, block_size: int = 16) -> bytes:
    return data + (block_size - len(data) % block_size) * b"\x00"


def unpad_zero(data: bytes) -> bytes:
    return data[: data.find(b"\x00")]


def extract_bits(raw: bytes, start: int, end: int) -> bytearray:
    strhex = raw.hex()
    return bytearray.fromhex(strhex[start:end])


def aes_encrypt(message: str, key: bytes, iv: bytes) -> str:
    raw = pad_zero(message.encode())
    cipher = AES.new(key, AES.MODE_CBC, iv)
    enc = cipher.encrypt(raw)
    return base64.b64encode(enc).decode("utf-8")


def aes_decrypt(enc: str, key: bytes, iv: bytes) -> bytes:
    decoded = base64.b64decode(enc)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    dec = cipher.decrypt(decoded)
    return unpad_zero(dec)


def rotate_iv_from_ciphertext(enc: str) -> bytes:
    return bytearray.fromhex(base64.b64decode(enc).hex()[-32:])


__all__ = [
    "aes_decrypt",
    "aes_encrypt",
    "extract_bits",
    "hmac_for_key_and_data",
    "pad_zero",
    "rotate_iv_from_ciphertext",
    "unpad_zero",
]
