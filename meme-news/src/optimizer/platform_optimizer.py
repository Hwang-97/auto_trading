"""
플랫폼별 콘텐츠 최적화 모듈
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from ..core.pipeline import MemeContent
from ..utils.logger import get_logger

logger = get_logger(__name__)


class PlatformOptimizer:
    """플랫폼별 콘텐츠 최적화 클래스"""

    def __init__(self, config_loader):
        self.config_loader = config_loader
        self.platforms_config = config_loader.load("platforms")
        self.optimization_config = self.platforms_config.get("optimization", {})

    def get_best_posting_time(self, platform: str) -> datetime:
        """플랫폼별 최적의 게시 시간을 반환합니다."""
        posting_times = self.optimization_config.get("posting_times", {})
        platform_times = posting_times.get(platform, {})

        best_hours = platform_times.get("best_hours", [9, 12, 18])
        best_days = platform_times.get("best_days", ["mon", "tue", "wed", "thu", "fri"])

        now = datetime.now()
        current_day = now.strftime("%a").lower()
        current_hour = now.hour

        # 오늘이 최적의 날인지 확인
        if current_day in best_days:
            # 다음 최적 시간 찾기
            for hour in best_hours:
                if hour > current_hour:
                    return now.replace(hour=hour, minute=0, second=0, microsecond=0)

        # 다음 최적의 날 찾기
        days_map = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
        current_day_num = now.weekday()

        for i in range(1, 8):
            next_day = (current_day_num + i) % 7
            next_day_name = list(days_map.keys())[next_day]
            if next_day_name in best_days:
                next_date = now + timedelta(days=i)
                best_hour = best_hours[0] if best_hours else 9
                return next_date.replace(hour=best_hour, minute=0, second=0, microsecond=0)

        # 폴백: 다음 날 오전 9시
        return (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)

    def optimize_title(self, title: str, platform: str) -> str:
        """플랫폼에 맞게 제목을 최적화합니다."""
        max_lengths = {
            "youtube": 100,
            "tiktok": 150,
            "instagram": 125,
        }
        max_length = max_lengths.get(platform, 100)

        # 길이 제한
        if len(title) > max_length:
            title = title[:max_length - 3] + "..."

        # 플랫폼별 최적화
        if platform == "youtube":
            # YouTube: 클릭 유도 문구 추가
            if not any(char in title for char in ["!", "?", "..."]):
                title = title.rstrip(".") + "!"
        elif platform == "tiktok":
            # TikTok: 짧고 임팩트 있게
            if len(title) > 50:
                title = self._shorten_title(title, 50)

        return title

    def _shorten_title(self, title: str, max_length: int) -> str:
        """제목을 줄입니다."""
        if len(title) <= max_length:
            return title

        # 주요 키워드 유지하며 줄이기
        words = title.split()
        result = []
        current_length = 0

        for word in words:
            if current_length + len(word) + 1 <= max_length - 3:
                result.append(word)
                current_length += len(word) + 1
            else:
                break

        return " ".join(result) + "..."

    def optimize_hashtags(
        self, hashtags: List[str], platform: str, content: MemeContent
    ) -> List[str]:
        """플랫폼에 맞게 해시태그를 최적화합니다."""
        max_hashtags = {
            "youtube": 15,
            "tiktok": 5,
            "instagram": 30,
        }
        max_count = max_hashtags.get(platform, 10)

        # 중복 제거
        unique_hashtags = list(dict.fromkeys(hashtags))

        # # 접두사 확인
        formatted = []
        for tag in unique_hashtags:
            if not tag.startswith("#"):
                tag = f"#{tag}"
            formatted.append(tag)

        # 플랫폼별 기본 태그 추가
        platform_config = self.platforms_config.get("platforms", {}).get(platform, {})
        default_hashtags = platform_config.get("hashtags", {}).get("default", [])

        for tag in default_hashtags:
            if tag not in formatted:
                formatted.append(tag)

        return formatted[:max_count]

    def get_ab_test_variants(
        self, content: MemeContent, element: str = "title"
    ) -> List[str]:
        """A/B 테스트용 변형을 생성합니다."""
        ab_config = self.optimization_config.get("ab_testing", {})

        if not ab_config.get("enabled"):
            return []

        variants = []

        if element == "title" and content.news_items:
            original_title = content.news_items[0].title
            num_variants = ab_config.get("title_variants", 2)

            # 변형 생성
            variants.append(original_title)

            # 질문형 변형
            if not original_title.endswith("?"):
                variants.append(f"{original_title.rstrip('.')}?")

            # 감탄형 변형
            if not original_title.endswith("!"):
                variants.append(f"{original_title.rstrip('.')}!")

            # 숫자 강조 변형
            variants.append(f"[속보] {original_title}")

            return variants[:num_variants]

        elif element == "thumbnail":
            num_variants = ab_config.get("thumbnail_variants", 3)
            # 썸네일 변형 아이디어 반환
            return [
                {"style": "bold_text", "color_scheme": "red_white"},
                {"style": "minimal", "color_scheme": "black_yellow"},
                {"style": "emoji_focus", "color_scheme": "gradient"},
            ][:num_variants]

        return variants

    def analyze_performance(self, analytics_data: Dict[str, dict]) -> dict:
        """성과 데이터를 분석합니다."""
        if not analytics_data:
            return {}

        total_views = 0
        total_likes = 0
        total_comments = 0
        platforms_analyzed = 0

        for platform, data in analytics_data.items():
            if data:
                total_views += data.get("views", 0)
                total_likes += data.get("likes", 0)
                total_comments += data.get("comments", 0)
                platforms_analyzed += 1

        if platforms_analyzed == 0:
            return {}

        # 성과 지표 계산
        engagement_rate = (
            (total_likes + total_comments) / total_views * 100
            if total_views > 0 else 0
        )

        return {
            "total_views": total_views,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "engagement_rate": round(engagement_rate, 2),
            "platforms_analyzed": platforms_analyzed,
            "performance_score": self._calculate_performance_score(
                total_views, total_likes, total_comments
            ),
        }

    def _calculate_performance_score(
        self, views: int, likes: int, comments: int
    ) -> str:
        """성과 점수를 계산합니다."""
        # 가중치 적용 점수
        score = views * 1 + likes * 10 + comments * 20

        if score >= 10000:
            return "excellent"
        elif score >= 5000:
            return "good"
        elif score >= 1000:
            return "average"
        else:
            return "needs_improvement"

    def get_content_recommendations(
        self, past_performance: List[dict]
    ) -> List[str]:
        """과거 성과 기반 콘텐츠 추천을 제공합니다."""
        recommendations = []

        if not past_performance:
            return ["데이터가 충분하지 않습니다. 더 많은 콘텐츠를 업로드해주세요."]

        # 평균 성과 계산
        avg_views = sum(p.get("views", 0) for p in past_performance) / len(past_performance)
        avg_engagement = sum(p.get("engagement_rate", 0) for p in past_performance) / len(past_performance)

        if avg_engagement < 2:
            recommendations.append("참여율이 낮습니다. 더 자극적인 제목과 썸네일을 시도해보세요.")

        if avg_views < 1000:
            recommendations.append("조회수가 낮습니다. 트렌드 키워드를 더 활용해보세요.")

        # 최적 게시 시간 추천
        recommendations.append(
            "최적 게시 시간: YouTube는 오후 6시, TikTok은 저녁 7시를 추천합니다."
        )

        return recommendations
