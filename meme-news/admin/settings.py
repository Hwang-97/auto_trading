"""
설정 관리 모듈

API 키 및 민감한 설정을 암호화하여 관리합니다.
"""

import base64
import hashlib
import json
import os
import secrets
from pathlib import Path
from typing import Any, Dict, Optional

# cryptography 라이브러리 로드 시도 (폴백 지원)
CRYPTO_AVAILABLE = False
Fernet = None

try:
    import importlib
    cryptography_module = importlib.import_module('cryptography.fernet')
    Fernet = cryptography_module.Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except (ImportError, Exception):
    CRYPTO_AVAILABLE = False


class SimpleCipher:
    """cryptography 없을 때 사용하는 간단한 암호화 (Base64 + XOR)"""

    def __init__(self, key: bytes):
        self.key = key

    def encrypt(self, data: bytes) -> bytes:
        """간단한 XOR 암호화 + Base64"""
        encrypted = bytes(a ^ b for a, b in zip(data, (self.key * (len(data) // len(self.key) + 1))[:len(data)]))
        return base64.urlsafe_b64encode(encrypted)

    def decrypt(self, token: bytes) -> bytes:
        """Base64 디코딩 + XOR 복호화"""
        decoded = base64.urlsafe_b64decode(token)
        return bytes(a ^ b for a, b in zip(decoded, (self.key * (len(decoded) // len(self.key) + 1))[:len(decoded)]))


class SettingsManager:
    """설정 관리 클래스 (암호화 지원)"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.settings_file = self.data_dir / "settings.enc"
        self.key_file = self.data_dir / ".keyfile"
        self._cipher = self._init_encryption()

    def _init_encryption(self):
        """암호화 키 초기화"""
        secret_key = os.getenv("SECRET_KEY", "")

        if self.key_file.exists():
            with open(self.key_file, "rb") as f:
                salt = f.read()
        else:
            salt = secrets.token_bytes(16)
            with open(self.key_file, "wb") as f:
                f.write(salt)
            try:
                os.chmod(self.key_file, 0o600)
            except OSError:
                pass

        if not secret_key:
            secret_key = "memenews_default_secret_change_in_production"

        if CRYPTO_AVAILABLE:
            # Fernet 사용 (안전한 암호화)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
            return Fernet(key)
        else:
            # SimpleCipher 폴백 (테스트용)
            key = hashlib.pbkdf2_hmac('sha256', secret_key.encode(), salt, 100000)
            return SimpleCipher(key)

    def _encrypt(self, data: str) -> str:
        """데이터 암호화"""
        return self._cipher.encrypt(data.encode()).decode()

    def _decrypt(self, encrypted_data: str) -> str:
        """데이터 복호화"""
        return self._cipher.decrypt(encrypted_data.encode()).decode()

    def _load_settings(self) -> Dict[str, Any]:
        """설정 로드"""
        if not self.settings_file.exists():
            return {"api_keys": {}, "general": {}}

        try:
            with open(self.settings_file, "r", encoding="utf-8") as f:
                encrypted = f.read()
            decrypted = self._decrypt(encrypted)
            return json.loads(decrypted)
        except Exception:
            return {"api_keys": {}, "general": {}}

    def _save_settings(self, settings: Dict[str, Any]):
        """설정 저장 (암호화)"""
        data = json.dumps(settings, ensure_ascii=False)
        encrypted = self._encrypt(data)
        with open(self.settings_file, "w", encoding="utf-8") as f:
            f.write(encrypted)
        try:
            os.chmod(self.settings_file, 0o600)
        except OSError:
            pass

    def get_all_settings(self) -> Dict[str, Any]:
        """모든 설정 반환 (API 키는 마스킹)"""
        settings = self._load_settings()

        masked_keys = {}
        for key, value in settings.get("api_keys", {}).items():
            if value:
                masked_keys[key] = self._mask_value(value)
            else:
                masked_keys[key] = ""

        return {
            "api_keys": masked_keys,
            "api_keys_set": {k: bool(v) for k, v in settings.get("api_keys", {}).items()},
            "general": settings.get("general", {}),
        }

    def _mask_value(self, value: str) -> str:
        """값 마스킹 (앞 4자, 뒤 4자만 표시)"""
        if len(value) <= 8:
            return "*" * len(value)
        return value[:4] + "*" * (len(value) - 8) + value[-4:]

    def get_api_key(self, key_name: str) -> Optional[str]:
        """API 키 반환 (복호화된 원본)"""
        settings = self._load_settings()
        return settings.get("api_keys", {}).get(key_name)

    def save_api_keys(self, api_keys: Dict[str, str]):
        """API 키 저장"""
        settings = self._load_settings()

        existing_keys = settings.get("api_keys", {})
        for key, value in api_keys.items():
            if value:
                existing_keys[key] = value

        settings["api_keys"] = existing_keys
        self._save_settings(settings)

        self._update_env_file(existing_keys)

    def _update_env_file(self, api_keys: Dict[str, str]):
        """환경 변수 파일 업데이트"""
        env_file = Path(".env")

        existing_vars = {}
        if env_file.exists():
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        existing_vars[key] = value

        key_mapping = {
            "gemini_api_key": "GEMINI_API_KEY",
            "youtube_client_id": "YOUTUBE_CLIENT_ID",
            "youtube_client_secret": "YOUTUBE_CLIENT_SECRET",
            "youtube_refresh_token": "YOUTUBE_REFRESH_TOKEN",
            "tiktok_access_token": "TIKTOK_ACCESS_TOKEN",
            "instagram_access_token": "INSTAGRAM_ACCESS_TOKEN",
            "instagram_account_id": "INSTAGRAM_ACCOUNT_ID",
            "slack_webhook": "SLACK_WEBHOOK_URL",
            "discord_webhook": "DISCORD_WEBHOOK_URL",
        }

        for internal_key, env_key in key_mapping.items():
            if internal_key in api_keys and api_keys[internal_key]:
                existing_vars[env_key] = api_keys[internal_key]

        with open(env_file, "w", encoding="utf-8") as f:
            f.write("# MemeNews Environment Variables\n")
            f.write("# Auto-generated - do not edit manually\n\n")
            for key, value in existing_vars.items():
                f.write(f"{key}={value}\n")

    def get_setting(self, key: str, default: Any = None) -> Any:
        """일반 설정 가져오기"""
        settings = self._load_settings()
        return settings.get("general", {}).get(key, default)

    def save_setting(self, key: str, value: Any):
        """일반 설정 저장"""
        settings = self._load_settings()
        if "general" not in settings:
            settings["general"] = {}
        settings["general"][key] = value
        self._save_settings(settings)
