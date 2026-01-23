"""
설정 파일 로더 모듈

YAML 설정 파일과 환경 변수를 관리합니다.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv


class ConfigLoader:
    """YAML 설정 파일 및 환경 변수를 로드하는 클래스"""

    def __init__(self, config_dir: str = "config"):
        """
        ConfigLoader를 초기화합니다.

        Args:
            config_dir: 설정 파일 디렉토리 경로
        """
        self.config_dir = Path(config_dir)
        self._configs: Dict[str, Dict[str, Any]] = {}
        load_dotenv()

    def load(self, config_name: str) -> Dict[str, Any]:
        """
        특정 설정 파일을 로드합니다.

        Args:
            config_name: 설정 파일 이름 (확장자 제외)

        Returns:
            설정 딕셔너리

        Raises:
            FileNotFoundError: 설정 파일이 없을 경우
        """
        if config_name in self._configs:
            return self._configs[config_name]

        config_path = self.config_dir / f"{config_name}.yaml"
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        self._configs[config_name] = config or {}
        return self._configs[config_name]

    def load_all(self) -> Dict[str, Dict[str, Any]]:
        """모든 설정 파일을 로드합니다."""
        config_files = ["config", "channels", "sources", "platforms", "prompts"]
        for config_name in config_files:
            try:
                self.load(config_name)
            except FileNotFoundError:
                pass
        return self._configs

    def get(self, config_name: str, key: str, default: Any = None) -> Any:
        """
        점(.) 표기법으로 설정 값을 가져옵니다.

        Args:
            config_name: 설정 파일 이름
            key: 점으로 구분된 키 경로 (예: "api.gemini.model")
            default: 기본값

        Returns:
            설정 값 또는 기본값
        """
        config = self.load(config_name)
        keys = key.split(".")
        value = config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value

    def get_channel(self, channel_name: str) -> Optional[Dict[str, Any]]:
        """
        채널 설정을 가져옵니다.

        Args:
            channel_name: 채널 이름 (daily_meme, trend_meme, it_meme)

        Returns:
            채널 설정 딕셔너리
        """
        channels = self.load("channels")
        return channels.get("channels", {}).get(channel_name)

    def get_all_channels(self) -> Dict[str, Dict[str, Any]]:
        """활성화된 모든 채널을 가져옵니다."""
        channels = self.load("channels")
        return {
            name: config
            for name, config in channels.get("channels", {}).items()
            if config.get("enabled", True)
        }

    def get_source(self, category: str) -> Optional[Dict[str, Any]]:
        """
        카테고리별 소스 설정을 가져옵니다.

        Args:
            category: 카테고리 (daily, trend, it, stock)

        Returns:
            소스 설정 딕셔너리
        """
        sources = self.load("sources")
        return sources.get("sources", {}).get(category)

    def get_platform(self, platform_name: str) -> Optional[Dict[str, Any]]:
        """
        플랫폼 설정을 가져옵니다.

        Args:
            platform_name: 플랫폼 이름 (youtube, tiktok, instagram)

        Returns:
            플랫폼 설정 딕셔너리
        """
        platforms = self.load("platforms")
        return platforms.get("platforms", {}).get(platform_name)

    def get_prompt(self, prompt_name: str) -> Optional[Dict[str, Any]]:
        """
        프롬프트 템플릿을 가져옵니다.

        Args:
            prompt_name: 프롬프트 이름

        Returns:
            프롬프트 설정 딕셔너리
        """
        prompts = self.load("prompts")
        return prompts.get(prompt_name)

    @staticmethod
    def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
        """환경 변수를 가져옵니다."""
        return os.getenv(key, default)

    def get_api_key(self, service: str) -> Optional[str]:
        """
        API 키를 환경 변수에서 가져옵니다.

        Args:
            service: 서비스 이름 (gemini, youtube, tiktok 등)

        Returns:
            API 키 또는 None
        """
        # config.yaml의 env_keys에서 환경변수 이름 가져오기
        config = self.load("config")
        env_keys = config.get("env_keys", {})

        # 서비스별 환경변수 키 매핑
        key_mapping = {
            "gemini": env_keys.get("gemini_api_key", "GEMINI_API_KEY"),
            "youtube": env_keys.get("youtube_api_key", "YOUTUBE_API_KEY"),
            "youtube_client_id": env_keys.get("youtube_client_id", "YOUTUBE_CLIENT_ID"),
            "youtube_client_secret": env_keys.get("youtube_client_secret", "YOUTUBE_CLIENT_SECRET"),
            "youtube_refresh_token": env_keys.get("youtube_refresh_token", "YOUTUBE_REFRESH_TOKEN"),
            "tiktok": env_keys.get("tiktok_api_key", "TIKTOK_API_KEY"),
            "tiktok_access_token": env_keys.get("tiktok_access_token", "TIKTOK_ACCESS_TOKEN"),
            "instagram_access_token": env_keys.get("instagram_access_token", "INSTAGRAM_ACCESS_TOKEN"),
            "instagram_account_id": env_keys.get("instagram_account_id", "INSTAGRAM_ACCOUNT_ID"),
            "slack": env_keys.get("slack_webhook", "SLACK_WEBHOOK_URL"),
            "discord": env_keys.get("discord_webhook", "DISCORD_WEBHOOK_URL"),
        }

        env_key = key_mapping.get(service.lower())
        if env_key:
            return os.getenv(env_key)
        return None

    def get_output_path(self, channel_name: str) -> Path:
        """
        채널별 출력 디렉토리 경로를 가져옵니다.

        Args:
            channel_name: 채널 이름

        Returns:
            출력 디렉토리 Path
        """
        config = self.load("config")
        paths = config.get("paths", {})
        channel_output = paths.get("channel_output", {})

        output_dir = channel_output.get(channel_name, f"output/{channel_name}")
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)

        return path

    def get_database_path(self) -> str:
        """데이터베이스 경로를 가져옵니다."""
        config = self.load("config")
        return config.get("database", {}).get("path", "data/memenews.db")

    def get_keyword_filters(self, category: str) -> Dict[str, List[str]]:
        """
        카테고리별 키워드 필터를 가져옵니다.

        Args:
            category: 카테고리 이름

        Returns:
            include, exclude 키워드 딕셔너리
        """
        sources = self.load("sources")
        filters = sources.get("keyword_filters", {})

        return {
            "include": filters.get("include", {}).get(category, []),
            "exclude": (
                filters.get("exclude", {}).get("common", []) +
                filters.get("exclude", {}).get("sensitive", [])
            ),
        }
