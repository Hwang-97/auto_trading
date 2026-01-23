"""
알림 유틸리티 모듈
"""

import os
from datetime import datetime
from typing import Dict, List, Optional

import aiohttp

from .logger import get_logger

logger = get_logger(__name__)


class Notifier:
    """알림을 전송하는 클래스"""

    def __init__(self, config_loader):
        self.config_loader = config_loader
        self.config = config_loader.load("config")
        self.notification_config = self.config.get("notification", {})

    @property
    def is_enabled(self) -> bool:
        """알림이 활성화되어 있는지 확인합니다."""
        return self.notification_config.get("enabled", False)

    async def notify(
        self,
        title: str,
        message: str,
        level: str = "info",
        channels: Optional[List[str]] = None
    ):
        """모든 활성화된 채널로 알림을 전송합니다."""
        if not self.is_enabled:
            logger.debug("Notifications are disabled")
            return

        channels = channels or ["slack", "discord"]

        for channel in channels:
            try:
                if channel == "slack":
                    await self._send_slack(title, message, level)
                elif channel == "discord":
                    await self._send_discord(title, message, level)
            except Exception as e:
                logger.error(f"Failed to send {channel} notification: {e}")

    async def _send_slack(self, title: str, message: str, level: str = "info"):
        """Slack 웹훅으로 알림을 전송합니다."""
        webhook_url = (
            self.notification_config.get("slack_webhook") or
            os.getenv("SLACK_WEBHOOK_URL")
        )

        if not webhook_url:
            logger.debug("Slack webhook URL not configured")
            return

        # 레벨별 색상
        colors = {
            "info": "#36a64f",
            "warning": "#ffcc00",
            "error": "#ff0000",
            "success": "#00ff00",
        }

        payload = {
            "attachments": [
                {
                    "color": colors.get(level, "#36a64f"),
                    "title": title,
                    "text": message,
                    "footer": "MemeNews Bot",
                    "ts": int(datetime.now().timestamp())
                }
            ]
        }

        await self._send_webhook(webhook_url, payload)
        logger.info(f"Slack notification sent: {title}")

    async def _send_discord(self, title: str, message: str, level: str = "info"):
        """Discord 웹훅으로 알림을 전송합니다."""
        webhook_url = (
            self.notification_config.get("discord_webhook") or
            os.getenv("DISCORD_WEBHOOK_URL")
        )

        if not webhook_url:
            logger.debug("Discord webhook URL not configured")
            return

        # 레벨별 색상 (Discord는 10진수 정수)
        colors = {
            "info": 3447003,  # 파랑
            "warning": 16776960,  # 노랑
            "error": 15158332,  # 빨강
            "success": 3066993,  # 초록
        }

        payload = {
            "embeds": [
                {
                    "title": title,
                    "description": message,
                    "color": colors.get(level, 3447003),
                    "footer": {
                        "text": "MemeNews Bot"
                    },
                    "timestamp": datetime.now().isoformat()
                }
            ]
        }

        await self._send_webhook(webhook_url, payload)
        logger.info(f"Discord notification sent: {title}")

    async def _send_webhook(self, url: str, payload: dict):
        """웹훅 요청을 전송합니다."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status not in [200, 204]:
                        error = await response.text()
                        logger.error(f"Webhook failed: {response.status} - {error}")

        except Exception as e:
            logger.error(f"Webhook request error: {e}")
            raise

    async def notify_upload_success(
        self,
        platform: str,
        title: str,
        url: str
    ):
        """업로드 성공 알림을 전송합니다."""
        await self.notify(
            title=f"[{platform.upper()}] 업로드 완료",
            message=f"**{title}**\n{url}",
            level="success"
        )

    async def notify_upload_failure(
        self,
        platform: str,
        error: str
    ):
        """업로드 실패 알림을 전송합니다."""
        await self.notify(
            title=f"[{platform.upper()}] 업로드 실패",
            message=f"오류: {error}",
            level="error"
        )

    async def notify_daily_summary(
        self,
        stats: Dict
    ):
        """일일 요약 알림을 전송합니다."""
        message_parts = [
            f"총 콘텐츠: {stats.get('total_content', 0)}개",
            f"총 조회수: {stats.get('total_views', 0):,}",
            f"총 좋아요: {stats.get('total_likes', 0):,}",
            f"참여율: {stats.get('engagement_rate', 0):.2f}%",
        ]

        await self.notify(
            title="MemeNews 일일 리포트",
            message="\n".join(message_parts),
            level="info"
        )

    async def notify_error(
        self,
        error_type: str,
        error_message: str,
        context: Optional[dict] = None
    ):
        """에러 알림을 전송합니다."""
        message = f"**오류 유형**: {error_type}\n**메시지**: {error_message}"

        if context:
            context_str = "\n".join([f"- {k}: {v}" for k, v in context.items()])
            message += f"\n**컨텍스트**:\n{context_str}"

        await self.notify(
            title="MemeNews 오류 발생",
            message=message,
            level="error"
        )
