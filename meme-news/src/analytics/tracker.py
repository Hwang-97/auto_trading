"""
Analytics Tracker

콘텐츠 성과 추적 및 분석
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from collections import defaultdict

from ..database.models import Database, Analytics
from ..utils.logger import get_logger

logger = get_logger(__name__)


class AnalyticsTracker:
    """분석 데이터 추적 클래스"""

    def __init__(self, config_loader):
        self.config_loader = config_loader
        self.db = Database(config_loader.get_database_path())
        self._cache = {}
        self._cache_ttl = 300  # 5분 캐시

    def track_content_created(
        self, content_id: int, channel_name: str, content_type: str
    ):
        """콘텐츠 생성 추적"""
        logger.info(f"Content created: {content_id} ({channel_name}/{content_type})")

    def track_upload(
        self, content_id: int, platform: str, success: bool,
        platform_id: str = None, error: str = None
    ):
        """업로드 추적"""
        status = "success" if success else "failed"
        logger.info(f"Upload tracked: {content_id} -> {platform} ({status})")

    def track_engagement(
        self, content_id: int, platform: str,
        views: int = 0, likes: int = 0, comments: int = 0, shares: int = 0
    ):
        """참여도 추적"""
        # 참여율 계산
        engagement_rate = 0.0
        if views > 0:
            engagement_rate = (likes + comments + shares) / views * 100

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

        self.db.record_analytics(analytics)
        logger.info(
            f"Engagement tracked: {content_id} - "
            f"views={views}, likes={likes}, engagement={engagement_rate:.2f}%"
        )

    def get_channel_performance(
        self, channel_name: str, days: int = 30
    ) -> Dict[str, Any]:
        """채널 성과 조회"""
        summary = self.db.get_analytics_summary(channel_name, days)

        # 일별 추이 계산
        daily_stats = []
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            stats = self.db.get_daily_stats(date)
            daily_stats.append({
                "date": date,
                "created": stats.get("by_channel", {}).get(channel_name, 0)
            })

        return {
            "summary": summary,
            "daily_trend": list(reversed(daily_stats)),
            "period_days": days
        }

    def get_platform_comparison(self, days: int = 30) -> Dict[str, Any]:
        """플랫폼별 성과 비교"""
        platforms = ["youtube", "tiktok", "instagram"]
        comparison = {}

        for platform in platforms:
            # 플랫폼별 통계 (간단히 구현)
            comparison[platform] = {
                "total_uploads": 0,
                "total_views": 0,
                "avg_engagement": 0.0
            }

        return comparison

    def get_top_performing_content(
        self, limit: int = 10, days: int = 30
    ) -> List[Dict[str, Any]]:
        """최고 성과 콘텐츠 조회"""
        # 참여율 기준 상위 콘텐츠
        results = []

        # TODO: 실제 쿼리로 구현
        return results

    def get_optimal_posting_times(
        self, channel_name: str = None
    ) -> Dict[str, List[str]]:
        """최적 게시 시간 분석"""
        # 시간대별 참여율 분석하여 최적 시간 추천
        # TODO: 실제 데이터 분석으로 구현

        # 기본 추천 시간
        return {
            "weekday": ["08:00", "12:00", "18:00", "21:00"],
            "weekend": ["10:00", "14:00", "20:00"],
            "best_days": ["화요일", "수요일", "목요일"]
        }

    def calculate_growth_rate(
        self, channel_name: str = None, days: int = 7
    ) -> Dict[str, float]:
        """성장률 계산"""
        current_period = self.db.get_analytics_summary(channel_name, days)
        previous_period = self.db.get_analytics_summary(channel_name, days * 2)

        def calc_rate(current, previous):
            if previous == 0:
                return 100.0 if current > 0 else 0.0
            return ((current - previous) / previous) * 100

        current_views = current_period.get("total_views", 0)
        previous_views = previous_period.get("total_views", 0) - current_views

        current_content = current_period.get("total_contents", 0)
        previous_content = previous_period.get("total_contents", 0) - current_content

        return {
            "views_growth": calc_rate(current_views, previous_views),
            "content_growth": calc_rate(current_content, previous_content),
            "period_days": days
        }

    def get_hashtag_performance(self, days: int = 30) -> List[Dict[str, Any]]:
        """해시태그 성과 분석"""
        # TODO: 해시태그별 성과 분석
        return []

    def get_content_type_analysis(self, days: int = 30) -> Dict[str, Any]:
        """콘텐츠 유형별 분석"""
        content_types = ["daily", "trend", "it"]
        analysis = {}

        for ct in content_types:
            analysis[ct] = {
                "count": 0,
                "avg_views": 0,
                "avg_engagement": 0.0
            }

        return analysis
