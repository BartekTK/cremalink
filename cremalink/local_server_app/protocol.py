import base64
import json
from typing import Tuple

from cremalink.crypto import aes_decrypt, aes_encrypt, extract_bits, hmac_for_key_and_data, rotate_iv_from_ciphertext


def pad_seq(seq: int) -> str:
    return str(seq)


def derive_keys(lan_key: str, random_1: str, random_2: str, time_1: str, time_2: str):
    rnd_1s = random_1.encode("utf-8")
    rnd_2s = random_2.encode("utf-8")
    time_1s = str(time_1).encode("utf-8")
    time_2s = str(time_2).encode("utf-8")
    lan_key_bytes = lan_key.encode("utf-8")

    lastbyte = b"\x30"
    concat = rnd_1s + rnd_2s + time_1s + time_2s + lastbyte
    app_sign_key = hmac_for_key_and_data(
        lan_key_bytes, hmac_for_key_and_data(lan_key_bytes, concat) + concat
    )

    lastbyte = b"\x31"
    concat = rnd_1s + rnd_2s + time_1s + time_2s + lastbyte
    app_crypto_key = hmac_for_key_and_data(
        lan_key_bytes, hmac_for_key_and_data(lan_key_bytes, concat) + concat
    )

    lastbyte = b"\x32"
    concat = rnd_1s + rnd_2s + time_1s + time_2s + lastbyte
    app_iv_seed = extract_bits(
        hmac_for_key_and_data(lan_key_bytes, hmac_for_key_and_data(lan_key_bytes, concat) + concat),
        0,
        16 * 2,
    )

    lastbyte = b"\x31"
    concat = rnd_2s + rnd_1s + time_2s + time_1s + lastbyte
    dev_crypto_key = hmac_for_key_and_data(
        lan_key_bytes, hmac_for_key_and_data(lan_key_bytes, concat) + concat
    )

    lastbyte = b"\x32"
    concat = rnd_2s + rnd_1s + time_2s + time_1s + lastbyte
    dev_iv_seed = extract_bits(
        hmac_for_key_and_data(lan_key_bytes, hmac_for_key_and_data(lan_key_bytes, concat) + concat),
        0,
        16 * 2,
    )

    return app_sign_key, app_crypto_key, app_iv_seed, dev_crypto_key, dev_iv_seed


def encrypt_payload(payload: str, crypto_key: bytes, iv_seed: bytes) -> Tuple[str, bytes]:
    enc = aes_encrypt(payload, crypto_key, iv_seed)
    new_iv = rotate_iv_from_ciphertext(enc)
    return enc, new_iv


def decrypt_payload(enc: str, crypto_key: bytes, iv_seed: bytes) -> Tuple[bytes, bytes]:
    decrypted = aes_decrypt(enc, crypto_key, iv_seed)
    new_iv = rotate_iv_from_ciphertext(enc)
    return decrypted, new_iv


def sign_payload(payload: str, sign_key: bytes) -> str:
    return base64.b64encode(hmac_for_key_and_data(sign_key, payload.encode("utf-8"))).decode("utf-8")


def build_empty_payload(seq: int) -> str:
    return json.dumps({"seq_no": pad_seq(seq), "data": {}}, separators=(",", ":"))
