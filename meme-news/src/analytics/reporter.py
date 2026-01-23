"""
Analytics Reporter

분석 리포트 생성
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List

from ..database.models import Database
from ..utils.logger import get_logger

logger = get_logger(__name__)


class AnalyticsReporter:
    """분석 리포트 생성 클래스"""

    def __init__(self, config_loader):
        self.config_loader = config_loader
        self.db = Database(config_loader.get_database_path())

    def generate_daily_report(self, date: str = None) -> Dict[str, Any]:
        """일일 리포트 생성"""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        stats = self.db.get_daily_stats(date)
        summary = self.db.get_analytics_summary(days=1)

        report = {
            "report_type": "daily",
            "date": date,
            "generated_at": datetime.now().isoformat(),
            "content_stats": {
                "total_created": stats.get("total", 0),
                "uploaded": stats.get("uploaded", 0),
                "failed": stats.get("failed", 0),
                "success_rate": self._calc_rate(
                    stats.get("uploaded", 0), stats.get("total", 0)
                )
            },
            "channel_breakdown": stats.get("by_channel", {}),
            "engagement_summary": {
                "total_views": summary.get("total_views", 0),
                "total_likes": summary.get("total_likes", 0),
                "total_comments": summary.get("total_comments", 0),
                "avg_engagement_rate": summary.get("avg_engagement", 0.0)
            }
        }

        return report

    def generate_weekly_report(self) -> Dict[str, Any]:
        """주간 리포트 생성"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        daily_reports = []
        for i in range(7):
            date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
            daily_reports.append(self.db.get_daily_stats(date))

        summary = self.db.get_analytics_summary(days=7)

        # 집계
        total_created = sum(d.get("total", 0) for d in daily_reports)
        total_uploaded = sum(d.get("uploaded", 0) for d in daily_reports)

        report = {
            "report_type": "weekly",
            "period": {
                "start": start_date.strftime("%Y-%m-%d"),
                "end": end_date.strftime("%Y-%m-%d")
            },
            "generated_at": datetime.now().isoformat(),
            "content_stats": {
                "total_created": total_created,
                "uploaded": total_uploaded,
                "daily_average": total_created / 7,
                "success_rate": self._calc_rate(total_uploaded, total_created)
            },
            "engagement_summary": summary,
            "daily_breakdown": [
                {
                    "date": (start_date + timedelta(days=i)).strftime("%Y-%m-%d"),
                    "created": daily_reports[i].get("total", 0)
                }
                for i in range(7)
            ]
        }

        return report

    def generate_channel_report(
        self, channel_name: str, days: int = 30
    ) -> Dict[str, Any]:
        """채널별 리포트 생성"""
        contents = self.db.get_contents_by_channel(channel_name, limit=100)
        summary = self.db.get_analytics_summary(channel_name, days)

        # 상태별 분류
        status_counts = {"created": 0, "uploaded": 0, "failed": 0}
        for content in contents:
            status = content.status
            if status in status_counts:
                status_counts[status] += 1

        report = {
            "report_type": "channel",
            "channel_name": channel_name,
            "period_days": days,
            "generated_at": datetime.now().isoformat(),
            "content_stats": {
                "total": len(contents),
                **status_counts,
                "success_rate": self._calc_rate(
                    status_counts["uploaded"], len(contents)
                )
            },
            "engagement_summary": summary,
            "recent_contents": [
                {
                    "id": c.id,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                    "status": c.status,
                    "quality_score": c.quality_score
                }
                for c in contents[:10]
            ]
        }

        return report

    def generate_performance_summary(self, days: int = 30) -> Dict[str, Any]:
        """성과 요약 리포트"""
        channels = self.config_loader.get_all_channels()

        channel_summaries = {}
        for channel_name in channels:
            summary = self.db.get_analytics_summary(channel_name, days)
            channel_summaries[channel_name] = summary

        total_summary = self.db.get_analytics_summary(days=days)

        report = {
            "report_type": "performance_summary",
            "period_days": days,
            "generated_at": datetime.now().isoformat(),
            "total_summary": total_summary,
            "by_channel": channel_summaries,
            "recommendations": self._generate_recommendations(channel_summaries)
        }

        return report

    def _calc_rate(self, numerator: int, denominator: int) -> float:
        """비율 계산"""
        if denominator == 0:
            return 0.0
        return round(numerator / denominator * 100, 2)

    def _generate_recommendations(
        self, channel_summaries: Dict[str, Dict]
    ) -> List[str]:
        """개선 권장사항 생성"""
        recommendations = []

        for channel_name, summary in channel_summaries.items():
            views = summary.get("total_views", 0)
            engagement = summary.get("avg_engagement", 0.0)

            if views == 0:
                recommendations.append(
                    f"{channel_name}: 콘텐츠 조회수가 없습니다. 업로드 상태를 확인하세요."
                )
            elif engagement < 1.0:
                recommendations.append(
                    f"{channel_name}: 참여율이 낮습니다 ({engagement:.2f}%). "
                    "콘텐츠 품질 개선이 필요합니다."
                )

        if not recommendations:
            recommendations.append("전반적인 성과가 양호합니다.")

        return recommendations

    def format_slack_report(self, report: Dict[str, Any]) -> str:
        """Slack 형식 리포트"""
        report_type = report.get("report_type", "unknown")

        if report_type == "daily":
            content_stats = report.get("content_stats", {})
            return (
                f"*📊 일일 리포트 ({report.get('date')})*\n"
                f"• 생성: {content_stats.get('total_created', 0)}개\n"
                f"• 업로드: {content_stats.get('uploaded', 0)}개\n"
                f"• 성공률: {content_stats.get('success_rate', 0)}%"
            )
        elif report_type == "weekly":
            content_stats = report.get("content_stats", {})
            return (
                f"*📈 주간 리포트*\n"
                f"• 기간: {report.get('period', {}).get('start')} ~ "
                f"{report.get('period', {}).get('end')}\n"
                f"• 총 생성: {content_stats.get('total_created', 0)}개\n"
                f"• 일 평균: {content_stats.get('daily_average', 0):.1f}개"
            )

        return str(report)

    def format_discord_report(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Discord embed 형식 리포트"""
        report_type = report.get("report_type", "unknown")

        embed = {
            "title": f"📊 MemeNews {report_type.upper()} Report",
            "color": 0x667eea,
            "timestamp": report.get("generated_at"),
            "fields": []
        }

        if report_type == "daily":
            content_stats = report.get("content_stats", {})
            embed["fields"] = [
                {
                    "name": "생성",
                    "value": str(content_stats.get("total_created", 0)),
                    "inline": True
                },
                {
                    "name": "업로드",
                    "value": str(content_stats.get("uploaded", 0)),
                    "inline": True
                },
                {
                    "name": "성공률",
                    "value": f"{content_stats.get('success_rate', 0)}%",
                    "inline": True
                }
            ]

        return embed
