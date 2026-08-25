"""
encryptor.py - 인증서 암호 로컬 암호화/복호화 모듈
Fernet(AES-128-CBC + HMAC-SHA256) 사용
키는 key.bin 파일에 이 PC에서만 저장됩니다.
"""
import os
import sys
from cryptography.fernet import Fernet


def _get_base_dir() -> str:
    """실행 파일 기준 디렉토리 반환 (PyInstaller exe 지원)"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _get_key_path() -> str:
    return os.path.join(_get_base_dir(), "key.bin")


def _get_or_create_key() -> bytes:
    """암호화 키 로드 또는 신규 생성 (최초 1회만 생성)"""
    key_path = _get_key_path()
    if os.path.exists(key_path):
        with open(key_path, "rb") as f:
            return f.read()

    # 최초 실행: 새 키 생성
    key = Fernet.generate_key()
    with open(key_path, "wb") as f:
        f.write(key)
    return key


def encrypt(plaintext: str) -> str:
    """평문 문자열을 암호화하여 토큰 문자열 반환"""
    f = Fernet(_get_or_create_key())
    return f.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt(token: str) -> str:
    """암호화된 토큰을 복호화하여 평문 반환"""
    f = Fernet(_get_or_create_key())
    return f.decrypt(token.encode("utf-8")).decode("utf-8")
