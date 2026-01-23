"""
Database Manager

데이터베이스 작업을 위한 고수준 API 제공
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from .models import Database, Content, Upload, Analytics, TrendData
from ..core.pipeline import MemeContent, ContentType
from ..utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """데이터베이스 관리 클래스"""

    def __init__(self, config_loader):
        self.config_loader = config_loader
        db_path = config_loader.get_database_path()
        self.db = Database(db_path)

    def save_content(self, meme_content: MemeContent) -> int:
        """MemeContent를 데이터베이스에 저장"""
        content = Content(
            channel_name=meme_content.channel_name,
            content_type=meme_content.content_type.value if isinstance(
                meme_content.content_type, ContentType
            ) else str(meme_content.content_type),
            meme_text=meme_content.meme_text,
            top_text=meme_content.top_text,
            bottom_text=meme_content.bottom_text,
            narration=meme_content.narration,
            hashtags=json.dumps(meme_content.hashtags, ensure_ascii=False),
            image_path=meme_content.image_path,
            video_path=meme_content.video_path,
            quality_score=meme_content.metadata.get("quality_score", 0.0),
            status="created",
            created_at=meme_content.created_at,
            metadata=json.dumps(meme_content.metadata, ensure_ascii=False, default=str)
        )

        content_id = self.db.create_content(content)
        logger.info(f"Content saved: {content_id}")
        return content_id

    def record_upload(
        self, content_id: int, platform: str, success: bool,
        platform_id: str = None, error: str = None
    ):
        """업로드 결과 기록"""
        upload = Upload(
            content_id=content_id,
            platform=platform,
            platform_id=platform_id or "",
            status="success" if success else "failed",
            error_message=error,
            uploaded_at=datetime.now() if success else None
        )

        upload_id = self.db.create_upload(upload)

        if success:
            self.db.update_content_status(content_id, "uploaded")
        else:
            self.db.update_content_status(content_id, "failed")

        logger.info(f"Upload recorded: {upload_id} ({platform}: {'success' if success else 'failed'})")

    def record_analytics(
        self, content_id: int, platform: str,
        views: int = 0, likes: int = 0, comments: int = 0, shares: int = 0
    ):
        """분석 데이터 기록"""
        total_engagement = likes + comments + shares
        engagement_rate = (total_engagement / views * 100) if views > 0 else 0.0

        analytics = Analytics(
            content_id=content_id,
            platform=platform,
            views=views,
            likes=likes,
            comments=comments,
            shares=shares,
            engagement_rate=engagement_rate,
            recorded_at=datetime.now()
        )

        analytics_id = self.db.record_analytics(analytics)
        logger.info(f"Analytics recorded: {analytics_id}")

    def save_trend(
        self, source: str, keyword: str, rank: int,
        search_volume: int = 0, category: str = ""
    ):
        """트렌드 데이터 저장"""
        trend = TrendData(
            source=source,
            keyword=keyword,
            rank=rank,
            search_volume=search_volume,
            category=category,
            recorded_at=datetime.now()
        )

        trend_id = self.db.record_trend(trend)
        logger.debug(f"Trend saved: {keyword} (rank: {rank})")
        return trend_id

    def is_duplicate(self, meme_text: str, hours: int = 24) -> bool:
        """중복 콘텐츠 확인"""
        return self.db.is_duplicate_content(meme_text, hours)

    def get_channel_stats(self, channel_name: str) -> Dict[str, Any]:
        """채널 통계 조회"""
        return self.db.get_analytics_summary(channel_name)

    def get_daily_report(self, date: str = None) -> Dict[str, Any]:
        """일일 리포트 생성"""
        stats = self.db.get_daily_stats(date)

        # 채널별 상세 정보 추가
        for channel_name in stats["by_channel"]:
            channel_analytics = self.db.get_analytics_summary(channel_name, days=1)
            stats["by_channel"][channel_name] = {
                "created": stats["by_channel"][channel_name],
                "views": channel_analytics["total_views"],
                "engagement": channel_analytics["avg_engagement"]
            }

        return stats

    def get_trending_keywords(self, hours: int = 24, limit: int = 10) -> List[str]:
        """트렌딩 키워드 조회"""
        trends = self.db.get_recent_trends(hours=hours, limit=limit)
        return [t.keyword for t in trends]

    def get_recent_contents(
        self, channel_name: str = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """최근 콘텐츠 조회"""
        if channel_name:
            contents = self.db.get_contents_by_channel(channel_name, limit)
        else:
            # 전체 채널에서 조회
            contents = []
            channels = self.config_loader.get_all_channels()
            for ch_name in channels:
                contents.extend(self.db.get_contents_by_channel(ch_name, limit // len(channels)))

        return [c.to_dict() for c in contents]

    def cleanup_old_data(self, days: int = 90):
        """오래된 데이터 정리"""
        # TODO: 구현 - 90일 이상 된 데이터 삭제
        logger.info(f"Cleanup old data older than {days} days")
