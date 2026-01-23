"""
TikTok 플랫폼 업로드 모듈
"""

import os
from typing import Optional

import aiohttp

from .base import BasePlatform
from ..core.pipeline import MemeContent
from ..utils.logger import get_logger

logger = get_logger(__name__)


class TikTokPlatform(BasePlatform):
    """TikTok 업로드 클래스"""

    def __init__(self, config_loader):
        super().__init__(config_loader)
        self.access_token = None
        self.open_id = None

    @property
    def platform_name(self) -> str:
        return "tiktok"

    async def authenticate(self) -> bool:
        """TikTok API 인증을 수행합니다."""
        try:
            # 환경변수에서 토큰 로드
            self.access_token = os.getenv("TIKTOK_ACCESS_TOKEN")
            self.open_id = os.getenv("TIKTOK_OPEN_ID")

            if not self.access_token or not self.open_id:
                logger.warning("TikTok credentials not found in environment variables")
                logger.info("Please set TIKTOK_ACCESS_TOKEN and TIKTOK_OPEN_ID")
                return False

            # 토큰 유효성 검증
            is_valid = await self._validate_token()
            if is_valid:
                self._authenticated = True
                logger.info("TikTok authentication successful")
                return True

            return False

        except Exception as e:
            logger.error(f"TikTok authentication failed: {e}")
            return False

    async def _validate_token(self) -> bool:
        """액세스 토큰의 유효성을 검증합니다."""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.access_token}"}
                url = f"https://open.tiktokapis.com/v2/user/info/?fields=open_id,display_name"

                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return True
                    else:
                        logger.warning(f"TikTok token validation failed: {response.status}")
                        return False

        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return False

    async def upload(self, content: MemeContent, metadata: dict) -> Optional[str]:
        """TikTok에 동영상을 업로드합니다."""
        if not self._authenticated:
            if not await self.authenticate():
                return None

        video_path = content.video_path
        if not video_path or not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return None

        try:
            # TikTok Content Posting API 사용
            # 1. 업로드 URL 요청
            upload_url = await self._init_upload()
            if not upload_url:
                return None

            # 2. 동영상 업로드
            upload_result = await self._upload_video(upload_url, video_path)
            if not upload_result:
                return None

            # 3. 게시물 생성
            caption = self._generate_caption(content, metadata)
            post_result = await self._create_post(upload_result, caption)

            if post_result:
                self.log_upload_result(True, post_result)
                return post_result
            else:
                self.log_upload_result(False)
                return None

        except Exception as e:
            logger.error(f"TikTok upload failed: {e}")
            self.log_upload_result(False)
            return None

    async def _init_upload(self) -> Optional[str]:
        """업로드 초기화 및 URL 획득"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }
                url = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"

                data = {
                    "source_info": {
                        "source": "FILE_UPLOAD",
                        "video_size": 0,  # Will be updated
                        "chunk_size": 10000000,
                        "total_chunk_count": 1
                    }
                }

                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("data", {}).get("upload_url")
                    else:
                        logger.error(f"Failed to init upload: {response.status}")
                        return None

        except Exception as e:
            logger.error(f"Upload init error: {e}")
            return None

    async def _upload_video(self, upload_url: str, video_path: str) -> Optional[dict]:
        """동영상 파일을 업로드합니다."""
        try:
            async with aiohttp.ClientSession() as session:
                with open(video_path, "rb") as f:
                    video_data = f.read()

                headers = {
                    "Content-Type": "video/mp4",
                    "Content-Range": f"bytes 0-{len(video_data)-1}/{len(video_data)}"
                }

                async with session.put(upload_url, headers=headers, data=video_data) as response:
                    if response.status in [200, 201]:
                        return {"status": "success"}
                    else:
                        logger.error(f"Video upload failed: {response.status}")
                        return None

        except Exception as e:
            logger.error(f"Video upload error: {e}")
            return None

    async def _create_post(self, upload_result: dict, caption: str) -> Optional[str]:
        """게시물을 생성합니다."""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }
                url = "https://open.tiktokapis.com/v2/post/publish/video/init/"

                data = {
                    "post_info": {
                        "title": caption[:150],
                        "privacy_level": "PUBLIC_TO_EVERYONE",
                        "disable_duet": False,
                        "disable_comment": False,
                        "disable_stitch": False,
                    }
                }

                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        publish_id = result.get("data", {}).get("publish_id")
                        return f"https://www.tiktok.com/@user/video/{publish_id}"
                    else:
                        logger.error(f"Post creation failed: {response.status}")
                        return None

        except Exception as e:
            logger.error(f"Post creation error: {e}")
            return None

    def _generate_caption(self, content: MemeContent, metadata: dict) -> str:
        """TikTok 캡션을 생성합니다."""
        caption = metadata.get("caption", "")

        if not caption and content.news_items:
            caption = content.news_items[0].title

        # 해시태그 추가
        hashtags = self.get_hashtags()
        hashtag_str = " ".join(hashtags)

        max_length = self.config.get("caption_max_length", 2200)
        full_caption = f"{caption}\n\n{hashtag_str}"

        return full_caption[:max_length]

    async def get_analytics(self, video_id: str) -> dict:
        """동영상 분석 데이터를 가져옵니다."""
        if not self._authenticated:
            return {}

        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.access_token}"}
                url = f"https://open.tiktokapis.com/v2/video/query/?fields=id,like_count,comment_count,share_count,view_count"

                data = {"filters": {"video_ids": [video_id]}}

                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        videos = result.get("data", {}).get("videos", [])
                        if videos:
                            video = videos[0]
                            return {
                                "views": video.get("view_count", 0),
                                "likes": video.get("like_count", 0),
                                "comments": video.get("comment_count", 0),
                                "shares": video.get("share_count", 0),
                            }
                    return {}

        except Exception as e:
            logger.error(f"Failed to get TikTok analytics: {e}")
            return {}
