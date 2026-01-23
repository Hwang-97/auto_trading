"""
YouTube 플랫폼 업로드 모듈
"""

import os
from typing import Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from .base import BasePlatform
from ..core.pipeline import MemeContent
from ..utils.logger import get_logger

logger = get_logger(__name__)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


class YouTubePlatform(BasePlatform):
    """YouTube 업로드 클래스"""

    def __init__(self, config_loader):
        super().__init__(config_loader)
        self.youtube_service = None
        self.credentials = None

    @property
    def platform_name(self) -> str:
        return "youtube"

    async def authenticate(self) -> bool:
        """YouTube API 인증을 수행합니다."""
        try:
            # OAuth2 인증 정보 파일 경로
            client_secrets_file = os.getenv("YOUTUBE_CLIENT_SECRETS", "client_secrets.json")
            token_file = "youtube_token.json"

            # 기존 토큰 확인
            if os.path.exists(token_file):
                self.credentials = Credentials.from_authorized_user_file(token_file, SCOPES)

            # 토큰이 없거나 만료된 경우
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    from google.auth.transport.requests import Request
                    self.credentials.refresh(Request())
                else:
                    if not os.path.exists(client_secrets_file):
                        logger.error(f"Client secrets file not found: {client_secrets_file}")
                        return False

                    flow = InstalledAppFlow.from_client_secrets_file(
                        client_secrets_file, SCOPES
                    )
                    self.credentials = flow.run_local_server(port=0)

                # 토큰 저장
                with open(token_file, "w") as token:
                    token.write(self.credentials.to_json())

            # YouTube API 서비스 생성
            self.youtube_service = build("youtube", "v3", credentials=self.credentials)
            self._authenticated = True
            logger.info("YouTube authentication successful")
            return True

        except Exception as e:
            logger.error(f"YouTube authentication failed: {e}")
            return False

    async def upload(self, content: MemeContent, metadata: dict) -> Optional[str]:
        """YouTube에 동영상을 업로드합니다."""
        if not self._authenticated:
            if not await self.authenticate():
                return None

        video_path = content.video_path
        if not video_path or not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return None

        try:
            # 메타데이터 준비
            title = metadata.get("title", "MemeNews Video")[:100]
            description = metadata.get("description", self._generate_description(content))
            tags = metadata.get("tags", self.get_default_tags())
            category_id = self.config.get("upload_settings", {}).get("category_id", "22")
            privacy_status = metadata.get("privacy_status",
                self.config.get("upload_settings", {}).get("privacy_status", "public"))

            body = {
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": tags,
                    "categoryId": category_id,
                    "defaultLanguage": "ko",
                    "defaultAudioLanguage": "ko",
                },
                "status": {
                    "privacyStatus": privacy_status,
                    "madeForKids": False,
                    "selfDeclaredMadeForKids": False,
                },
            }

            # 미디어 파일 업로드
            media = MediaFileUpload(
                video_path,
                mimetype="video/mp4",
                resumable=True
            )

            # 업로드 요청
            request = self.youtube_service.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    logger.info(f"Upload progress: {int(status.progress() * 100)}%")

            video_id = response.get("id")
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            # 썸네일 업로드
            if content.thumbnail_path and os.path.exists(content.thumbnail_path):
                await self._upload_thumbnail(video_id, content.thumbnail_path)

            self.log_upload_result(True, video_url)
            return video_url

        except Exception as e:
            logger.error(f"YouTube upload failed: {e}")
            self.log_upload_result(False)
            return None

    async def _upload_thumbnail(self, video_id: str, thumbnail_path: str):
        """썸네일을 업로드합니다."""
        try:
            media = MediaFileUpload(thumbnail_path, mimetype="image/jpeg")
            self.youtube_service.thumbnails().set(
                videoId=video_id,
                media_body=media
            ).execute()
            logger.info(f"Thumbnail uploaded for video: {video_id}")
        except Exception as e:
            logger.warning(f"Thumbnail upload failed: {e}")

    def _generate_description(self, content: MemeContent) -> str:
        """동영상 설명을 생성합니다."""
        description_template = self.config.get("description_template", "")

        if content.news_items:
            title = content.news_items[0].title
        else:
            title = "오늘의 밈 뉴스"

        if description_template:
            return description_template.format(title=title)

        return f"{title}\n\n#뉴스 #밈 #시사유머"

    async def get_analytics(self, video_id: str) -> dict:
        """동영상 분석 데이터를 가져옵니다."""
        if not self._authenticated:
            return {}

        try:
            response = self.youtube_service.videos().list(
                part="statistics,snippet",
                id=video_id
            ).execute()

            if response.get("items"):
                item = response["items"][0]
                stats = item.get("statistics", {})
                return {
                    "views": int(stats.get("viewCount", 0)),
                    "likes": int(stats.get("likeCount", 0)),
                    "comments": int(stats.get("commentCount", 0)),
                    "title": item.get("snippet", {}).get("title", ""),
                }

            return {}

        except Exception as e:
            logger.error(f"Failed to get analytics: {e}")
            return {}

    async def upload_shorts(self, content: MemeContent, metadata: dict) -> Optional[str]:
        """YouTube Shorts를 업로드합니다."""
        # Shorts는 #Shorts 해시태그를 제목이나 설명에 포함
        if "tags" not in metadata:
            metadata["tags"] = self.get_default_tags()
        metadata["tags"].append("Shorts")

        description = metadata.get("description", "")
        if "#Shorts" not in description:
            metadata["description"] = f"{description}\n#Shorts"

        return await self.upload(content, metadata)
