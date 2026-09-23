import hashlib
from typing import Tuple


def decode_text(data: bytes) -> Tuple[str, str]:
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig"), "utf-8-sig"
    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        try:
            return data.decode("cp1252"), "cp1252"
        except UnicodeDecodeError:
            return data.decode("latin-1"), "latin-1"


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in text.split("\n")).strip()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalized_text_and_hash(text: str) -> Tuple[str, str]:
    normalized = normalize_text(text)
    return normalized, hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def sha256_text(text: str) -> str:
    return normalized_text_and_hash(text)[1]
