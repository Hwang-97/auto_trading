"""
Content 모듈 - 뉴스 크롤링, 트렌드 수집, AI 콘텐츠 생성
"""

from .news_crawler import NewsCrawler
from .trend_crawler import TrendCrawler
from .quality_filter import ContentQualityFilter

# AIGenerator는 google.generativeai 의존성으로 선택적 import
# cryptography 라이브러리 오류 (pyo3_runtime.PanicException)를 피하기 위해
# BaseException으로 캐치하고 lazy import 사용
AIGenerator = None

def get_ai_generator():
    """AIGenerator를 lazy하게 로드합니다."""
    global AIGenerator
    if AIGenerator is None:
        try:
            from .ai_generator import AIGenerator as _AIGenerator
            AIGenerator = _AIGenerator
        except BaseException:
            AIGenerator = None
    return AIGenerator

__all__ = ["NewsCrawler", "TrendCrawler", "AIGenerator", "ContentQualityFilter", "get_ai_generator"]
