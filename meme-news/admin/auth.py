"""
인증 관리 모듈

비밀번호 해싱 및 사용자 인증을 처리합니다.
"""

import hashlib
import json
import os
import secrets
from pathlib import Path
from typing import Optional

# bcrypt 대신 hashlib 사용 (의존성 최소화)


class AuthManager:
    """사용자 인증 관리 클래스"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.users_file = self.data_dir / "users.json"
        self._init_default_user()

    def _init_default_user(self):
        """기본 관리자 계정 초기화"""
        if not self.users_file.exists():
            default_username = os.getenv("ADMIN_USERNAME", "admin")
            default_password = os.getenv("ADMIN_PASSWORD", "memenews123!")

            users = {
                default_username: {
                    "password_hash": self._hash_password(default_password),
                    "salt": secrets.token_hex(16),
                    "created_at": self._get_timestamp(),
                    "is_default_password": True,
                }
            }
            self._save_users(users)

    def _hash_password(self, password: str, salt: Optional[str] = None) -> str:
        """비밀번호 해싱 (SHA-256 + salt)"""
        if salt is None:
            salt = secrets.token_hex(16)

        # PBKDF2-like 방식으로 해싱
        key = password + salt
        for _ in range(100000):  # 반복 해싱으로 보안 강화
            key = hashlib.sha256(key.encode()).hexdigest()

        return f"{salt}${key}"

    def _verify_hash(self, password: str, stored_hash: str) -> bool:
        """해시 검증"""
        try:
            salt, _ = stored_hash.split("$")
            return self._hash_password(password, salt) == stored_hash
        except ValueError:
            return False

    def _load_users(self) -> dict:
        """사용자 정보 로드"""
        if not self.users_file.exists():
            return {}

        with open(self.users_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_users(self, users: dict):
        """사용자 정보 저장"""
        with open(self.users_file, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)

    def _get_timestamp(self) -> str:
        """현재 타임스탬프"""
        from datetime import datetime
        return datetime.now().isoformat()

    def verify_password(self, username: str, password: str) -> bool:
        """비밀번호 검증"""
        users = self._load_users()
        user = users.get(username)

        if not user:
            return False

        return self._verify_hash(password, user["password_hash"])

    def change_password(self, username: str, new_password: str) -> bool:
        """비밀번호 변경"""
        users = self._load_users()

        if username not in users:
            return False

        users[username]["password_hash"] = self._hash_password(new_password)
        users[username]["is_default_password"] = False
        users[username]["updated_at"] = self._get_timestamp()

        self._save_users(users)
        return True

    def is_default_password(self, username: str) -> bool:
        """기본 비밀번호 사용 여부 확인"""
        users = self._load_users()
        user = users.get(username)

        if not user:
            return False

        return user.get("is_default_password", False)

    def create_user(self, username: str, password: str) -> bool:
        """새 사용자 생성"""
        users = self._load_users()

        if username in users:
            return False

        users[username] = {
            "password_hash": self._hash_password(password),
            "salt": secrets.token_hex(16),
            "created_at": self._get_timestamp(),
            "is_default_password": False,
        }

        self._save_users(users)
        return True

    def delete_user(self, username: str) -> bool:
        """사용자 삭제"""
        users = self._load_users()

        if username not in users:
            return False

        # admin 계정은 삭제 불가
        if username == "admin":
            return False

        del users[username]
        self._save_users(users)
        return True
