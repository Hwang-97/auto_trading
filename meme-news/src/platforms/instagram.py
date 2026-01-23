"""
Instagram 플랫폼 업로드 모듈
"""

import os
from typing import Optional

import aiohttp

from .base import BasePlatform
from ..core.pipeline import MemeContent
from ..utils.logger import get_logger

logger = get_logger(__name__)


class InstagramPlatform(BasePlatform):
    """Instagram 업로드 클래스 (Graph API 사용)"""

    def __init__(self, config_loader):
        super().__init__(config_loader)
        self.access_token = None
        self.instagram_account_id = None
        self.api_version = "v18.0"
        self.base_url = f"https://graph.facebook.com/{self.api_version}"

    @property
    def platform_name(self) -> str:
        return "instagram"

    async def authenticate(self) -> bool:
        """Instagram Graph API 인증을 수행합니다."""
        try:
            # 환경변수에서 토큰 로드
            self.access_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
            self.instagram_account_id = os.getenv("INSTAGRAM_ACCOUNT_ID")

            if not self.access_token or not self.instagram_account_id:
                logger.warning("Instagram credentials not found in environment variables")
                logger.info("Please set INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_ACCOUNT_ID")
                return False

            # 토큰 유효성 검증
            is_valid = await self._validate_token()
            if is_valid:
                self._authenticated = True
                logger.info("Instagram authentication successful")
                return True

            return False

        except Exception as e:
            logger.error(f"Instagram authentication failed: {e}")
            return False

    async def _validate_token(self) -> bool:
        """액세스 토큰의 유효성을 검증합니다."""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/{self.instagram_account_id}"
                params = {
                    "access_token": self.access_token,
                    "fields": "id,username"
                }

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"Authenticated as: {data.get('username')}")
                        return True
                    else:
                        logger.warning(f"Instagram token validation failed: {response.status}")
                        return False

        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return False

    async def upload(self, content: MemeContent, metadata: dict) -> Optional[str]:
        """Instagram에 콘텐츠를 업로드합니다."""
        if not self._authenticated:
            if not await self.authenticate():
                return None

        # 비디오 업로드 (Reels)
        if content.video_path and os.path.exists(content.video_path):
            return await self._upload_reel(content, metadata)

        # 이미지 업로드 (피드)
        if content.image_path and os.path.exists(content.image_path):
            return await self._upload_image(content, metadata)

        logger.error("No valid media content to upload")
        return None

    async def _upload_reel(self, content: MemeContent, metadata: dict) -> Optional[str]:
        """Instagram Reels를 업로드합니다."""
        try:
            video_path = content.video_path

            # 동영상을 호스팅된 URL로 제공해야 함
            # 실제 구현 시 클라우드 스토리지 업로드 필요
            video_url = metadata.get("video_url")
            if not video_url:
                logger.error("Video URL required for Instagram upload")
                logger.info("Instagram requires video to be hosted on a public URL")
                return None

            caption = self._generate_caption(content, metadata)

            # 1. 컨테이너 생성
            container_id = await self._create_media_container(
                media_type="REELS",
                video_url=video_url,
                caption=caption
            )

            if not container_id:
                return None

            # 2. 처리 완료 대기
            is_ready = await self._wait_for_container(container_id)
            if not is_ready:
                return None

            # 3. 게시
            media_id = await self._publish_container(container_id)
            if media_id:
                post_url = f"https://www.instagram.com/reel/{media_id}/"
                self.log_upload_result(True, post_url)
                return post_url

            self.log_upload_result(False)
            return None

        except Exception as e:
            logger.error(f"Reel upload failed: {e}")
            return None

    async def _upload_image(self, content: MemeContent, metadata: dict) -> Optional[str]:
        """Instagram 이미지를 업로드합니다."""
        try:
            # 이미지를 호스팅된 URL로 제공해야 함
            image_url = metadata.get("image_url")
            if not image_url:
                logger.error("Image URL required for Instagram upload")
                return None

            caption = self._generate_caption(content, metadata)

            # 1. 컨테이너 생성
            container_id = await self._create_media_container(
                media_type="IMAGE",
                image_url=image_url,
                caption=caption
            )

            if not container_id:
                return None

            # 2. 게시
            media_id = await self._publish_container(container_id)
            if media_id:
                post_url = f"https://www.instagram.com/p/{media_id}/"
                self.log_upload_result(True, post_url)
                return post_url

            self.log_upload_result(False)
            return None

        except Exception as e:
            logger.error(f"Image upload failed: {e}")
            return None

    async def _create_media_container(
        self,
        media_type: str,
        caption: str,
        video_url: str = None,
        image_url: str = None
    ) -> Optional[str]:
        """미디어 컨테이너를 생성합니다."""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/{self.instagram_account_id}/media"

                data = {
                    "caption": caption,
                    "access_token": self.access_token,
                }

                if media_type == "REELS":
                    data["media_type"] = "REELS"
                    data["video_url"] = video_url
                else:
                    data["image_url"] = image_url

                async with session.post(url, data=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("id")
                    else:
                        error = await response.text()
                        logger.error(f"Container creation failed: {error}")
                        return None

        except Exception as e:
            logger.error(f"Container creation error: {e}")
            return None

    async def _wait_for_container(self, container_id: str, max_attempts: int = 30) -> bool:
        """컨테이너 처리 완료를 대기합니다."""
        import asyncio

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/{container_id}"
                params = {
                    "access_token": self.access_token,
                    "fields": "status_code"
                }

                for _ in range(max_attempts):
                    async with session.get(url, params=params) as response:
                        if response.status == 200:
                            result = await response.json()
                            status = result.get("status_code")

                            if status == "FINISHED":
                                return True
                            elif status == "ERROR":
                                logger.error("Container processing failed")
                                return False

                    await asyncio.sleep(10)

                logger.error("Container processing timed out")
                return False

        except Exception as e:
            logger.error(f"Wait for container error: {e}")
            return False

    async def _publish_container(self, container_id: str) -> Optional[str]:
        """컨테이너를 게시합니다."""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/{self.instagram_account_id}/media_publish"
                data = {
                    "creation_id": container_id,
                    "access_token": self.access_token
                }

                async with session.post(url, data=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("id")
                    else:
                        error = await response.text()
                        logger.error(f"Publishing failed: {error}")
                        return None

        except Exception as e:
            logger.error(f"Publishing error: {e}")
            return None

    def _generate_caption(self, content: MemeContent, metadata: dict) -> str:
        """Instagram 캡션을 생성합니다."""
        caption = metadata.get("caption", "")

        if not caption and content.news_items:
            caption = content.news_items[0].title

        # 해시태그 추가
        hashtags = self.get_hashtags()
        hashtag_str = " ".join(hashtags)

        max_length = self.config.get("caption_max_length", 2200)
        full_caption = f"{caption}\n\n{hashtag_str}"

        return full_caption[:max_length]

    async def get_analytics(self, media_id: str) -> dict:
        """미디어 분석 데이터를 가져옵니다."""
        if not self._authenticated:
            return {}

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/{media_id}/insights"
                params = {
                    "access_token": self.access_token,
                    "metric": "impressions,reach,likes,comments,shares,saved"
                }

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        insights = {}
                        for item in result.get("data", []):
                            insights[item["name"]] = item["values"][0]["value"]
                        return insights
                    return {}

        except Exception as e:
            logger.error(f"Failed to get Instagram analytics: {e}")
            return {}
