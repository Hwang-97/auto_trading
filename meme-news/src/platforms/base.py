"""
플랫폼 베이스 클래스
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from ..core.pipeline import MemeContent
from ..utils.logger import get_logger

logger = get_logger(__name__)


class BasePlatform(ABC):
    """플랫폼 업로드 기본 클래스"""

    def __init__(self, config_loader):
        self.config_loader = config_loader
        self.platforms_config = config_loader.load("platforms")
        self._authenticated = False

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """플랫폼 이름을 반환합니다."""
        pass

    @property
    def config(self) -> dict:
        """플랫폼별 설정을 반환합니다."""
        return self.platforms_config.get("platforms", {}).get(self.platform_name, {})

    @property
    def is_enabled(self) -> bool:
        """플랫폼이 활성화되어 있는지 확인합니다."""
        return self.config.get("enabled", False)

    @abstractmethod
    async def authenticate(self) -> bool:
        """플랫폼 인증을 수행합니다."""
        pass

    @abstractmethod
    async def upload(self, content: MemeContent, metadata: dict) -> Optional[str]:
        """콘텐츠를 업로드합니다. 성공 시 URL 반환."""
        pass

    @abstractmethod
    async def get_analytics(self, content_id: str) -> dict:
        """콘텐츠 분석 데이터를 가져옵니다."""
        pass

    def get_default_tags(self) -> List[str]:
        """기본 태그 목록을 반환합니다."""
        return self.config.get("tags", {}).get("default", [])

    def get_hashtags(self) -> List[str]:
        """기본 해시태그 목록을 반환합니다."""
        return self.config.get("hashtags", {}).get("default", [])

    def format_caption(self, content: MemeContent) -> str:
        """캡션을 플랫폼에 맞게 포맷팅합니다."""
        max_length = self.config.get("caption_max_length", 2200)
        caption = content.meme_text or ""

        # 해시태그 추가
        hashtags = self.get_hashtags()
        if hashtags:
            hashtag_str = " ".join(hashtags)
            if len(caption) + len(hashtag_str) + 2 <= max_length:
                caption = f"{caption}\n\n{hashtag_str}"

        return caption[:max_length]

    async def validate_content(self, content: MemeContent) -> bool:
        """업로드 전 콘텐츠를 검증합니다."""
        if not content.video_path and not content.image_path:
            logger.error("No media content to upload")
            return False
        return True

    def log_upload_result(self, success: bool, url: Optional[str] = None):
        """업로드 결과를 로깅합니다."""
        if success:
            logger.info(f"Successfully uploaded to {self.platform_name}: {url}")
        else:
            logger.error(f"Failed to upload to {self.platform_name}")
