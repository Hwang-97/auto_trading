"""
콘텐츠 생성 파이프라인 모듈

뉴스 수집부터 밈 생성까지 전체 파이프라인을 관리합니다.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from ..utils.logger import get_logger

logger = get_logger(__name__)


class ContentType(Enum):
    """콘텐츠 유형"""
    DAILY = "daily"
    TREND = "trend"
    IT = "it"
    STOCK = "stock"


@dataclass
class NewsItem:
    """뉴스 아이템 데이터 클래스"""
    title: str
    content: str
    source: str
    url: str
    published_at: datetime
    category: str
    relevance_score: float = 0.0


@dataclass
class MemeContent:
    """밈 콘텐츠 데이터 클래스"""
    channel_name: str = ""
    content_type: ContentType = ContentType.DAILY
    news_items: List[NewsItem] = field(default_factory=list)
    meme_text: str = ""
    top_text: str = ""
    bottom_text: str = ""
    narration: str = ""
    image_path: Optional[str] = None
    video_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    script: Optional[str] = None
    hashtags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


class Pipeline:
    """콘텐츠 생성 파이프라인"""

    def __init__(self, config_loader):
        """
        파이프라인을 초기화합니다.

        Args:
            config_loader: ConfigLoader 인스턴스
        """
        self.config_loader = config_loader
        self.news_crawler = None
        self.trend_crawler = None
        self.ai_generator = None
        self.text_gen = None
        self.image_gen = None
        self.video_gen = None
        self._initialized = False

    async def initialize(self) -> None:
        """파이프라인 컴포넌트들을 초기화합니다."""
        if self._initialized:
            return

        from ..content.news_crawler import NewsCrawler
        from ..content.trend_crawler import TrendCrawler
        from ..content.ai_generator import AIGenerator
        from ..meme.text_gen import TextGenerator
        from ..meme.image_gen import ImageGenerator
        from ..meme.video_gen import VideoGenerator

        self.news_crawler = NewsCrawler(self.config_loader)
        self.trend_crawler = TrendCrawler(self.config_loader)
        self.ai_generator = AIGenerator(self.config_loader)
        self.text_gen = TextGenerator(self.config_loader)
        self.image_gen = ImageGenerator(self.config_loader)
        self.video_gen = VideoGenerator(self.config_loader)

        self._initialized = True
        logger.info("Pipeline initialized successfully")

    async def run_channel(
        self,
        channel_name: str,
        dry_run: bool = False
    ) -> Optional[MemeContent]:
        """
        특정 채널에 대해 파이프라인을 실행합니다.

        Args:
            channel_name: 채널 이름 (daily_meme, trend_meme, it_meme)
            dry_run: True면 실제 생성 없이 테스트만 수행

        Returns:
            생성된 MemeContent 또는 None
        """
        if not self._initialized:
            await self.initialize()

        channel_config = self.config_loader.get_channel(channel_name)
        if not channel_config:
            logger.error(f"Channel not found: {channel_name}")
            return None

        category = channel_config.get("category", "daily")
        content_type = ContentType(category)

        logger.info(f"Starting pipeline for channel: {channel_name} ({category})")

        if dry_run:
            logger.info("[DRY RUN] Would generate content for channel: %s", channel_name)
            return MemeContent(
                channel_name=channel_name,
                content_type=content_type,
                meme_text="[DRY RUN] 테스트 밈 텍스트",
            )

        try:
            # 1. 콘텐츠 소스에서 데이터 수집
            news_items = await self._collect_content(content_type, channel_config)
            if not news_items:
                logger.warning(f"No content collected for {channel_name}")
                return None

            logger.info(f"Collected {len(news_items)} items for {channel_name}")

            # 2. 밈 콘텐츠 객체 생성
            meme_content = MemeContent(
                channel_name=channel_name,
                content_type=content_type,
                news_items=news_items,
            )

            # 3. AI로 밈 텍스트 생성
            meme_result = await self._generate_meme_text(meme_content, channel_config)
            meme_content.meme_text = meme_result.get("meme_text", "")
            meme_content.top_text = meme_result.get("top_text", "")
            meme_content.bottom_text = meme_result.get("bottom_text", "")
            meme_content.narration = meme_result.get("narration", "")
            meme_content.hashtags = meme_result.get("hashtags", [])

            # 4. 이미지 생성
            meme_content.image_path = await self.image_gen.generate(meme_content)

            # 5. 스크립트 생성
            meme_content.script = await self.ai_generator.generate_script(
                meme_content,
                duration=30
            )

            # 6. 영상 생성
            meme_content.video_path = await self.video_gen.generate(meme_content)

            # 7. 썸네일 생성
            meme_content.thumbnail_path = await self.image_gen.generate_thumbnail(meme_content)

            logger.info(f"Pipeline completed for {channel_name}")
            return meme_content

        except Exception as e:
            logger.error(f"Pipeline error for {channel_name}: {e}")
            raise

    async def run(self, content_type: ContentType) -> Optional[MemeContent]:
        """
        콘텐츠 타입에 대해 파이프라인을 실행합니다 (레거시 호환).

        Args:
            content_type: 콘텐츠 유형

        Returns:
            생성된 MemeContent 또는 None
        """
        # 콘텐츠 타입에 해당하는 채널 찾기
        channel_map = {
            ContentType.DAILY: "daily_meme",
            ContentType.TREND: "trend_meme",
            ContentType.IT: "it_meme",
            ContentType.STOCK: "it_meme",
        }
        channel_name = channel_map.get(content_type, "daily_meme")
        return await self.run_channel(channel_name)

    async def _collect_content(
        self,
        content_type: ContentType,
        channel_config: Dict[str, Any]
    ) -> List[NewsItem]:
        """
        콘텐츠 타입에 따라 데이터를 수집합니다.

        Args:
            content_type: 콘텐츠 유형
            channel_config: 채널 설정

        Returns:
            수집된 뉴스 아이템 목록
        """
        source_config = self.config_loader.get_source(content_type.value)

        if content_type == ContentType.DAILY:
            # 일상: AI 생성을 위한 주제 가져오기
            topics = source_config.get("topics", []) if source_config else []
            return await self._generate_daily_topics(topics)

        elif content_type == ContentType.TREND:
            # 트렌드: 실시간 트렌드 수집
            trends = await self.trend_crawler.get_trends(limit=10)
            if trends:
                return await self.news_crawler.crawl_by_keywords(trends, limit=5)
            return []

        elif content_type in (ContentType.IT, ContentType.STOCK):
            # IT/주식: RSS 피드 크롤링
            return await self.news_crawler.crawl_by_category(content_type.value, limit=10)

        return []

    async def _generate_daily_topics(
        self,
        topics: List[Dict[str, Any]]
    ) -> List[NewsItem]:
        """
        일상 주제를 기반으로 가상의 뉴스 아이템을 생성합니다.

        Args:
            topics: 주제 목록

        Returns:
            생성된 뉴스 아이템 목록
        """
        import random

        if not topics:
            topics = [
                {"name": "직장생활", "keywords": ["출근", "월요병", "야근"]},
                {"name": "일상", "keywords": ["주말", "배달", "넷플릭스"]},
            ]

        # 가중치 기반으로 주제 선택
        weights = [t.get("weight", 1.0) for t in topics]
        selected_topic = random.choices(topics, weights=weights, k=1)[0]

        # 가상의 뉴스 아이템 생성 (AI가 실제 내용을 채울 것임)
        keyword = random.choice(selected_topic.get("keywords", ["일상"]))

        return [NewsItem(
            title=f"{selected_topic['name']} - {keyword}",
            content=f"{keyword} 관련 공감 콘텐츠",
            source="ai_generated",
            url="",
            published_at=datetime.now(),
            category="daily",
            relevance_score=1.0,
        )]

    async def _generate_meme_text(
        self,
        content: MemeContent,
        channel_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        AI를 사용하여 밈 텍스트를 생성합니다.

        Args:
            content: MemeContent 객체
            channel_config: 채널 설정

        Returns:
            생성된 밈 텍스트 정보 딕셔너리
        """
        content_config = channel_config.get("content", {})
        style = content_config.get("style", "humorous")

        # 콘텐츠 타입에 맞는 프롬프트 선택
        if content.content_type == ContentType.DAILY:
            result = await self.ai_generator.generate_daily_meme(
                topic=content.news_items[0].title if content.news_items else "일상",
                style=style
            )
        elif content.content_type == ContentType.TREND:
            result = await self.ai_generator.generate_trend_meme(
                keyword=content.news_items[0].title if content.news_items else "트렌드",
                context=content.news_items[0].content if content.news_items else ""
            )
        else:
            result = await self.ai_generator.generate_news_meme(
                news_item=content.news_items[0] if content.news_items else None,
                style=style
            )

        return result

    async def run_daily(self) -> Optional[MemeContent]:
        """일일 뉴스 콘텐츠를 생성합니다."""
        return await self.run(ContentType.DAILY)

    async def run_trend(self) -> Optional[MemeContent]:
        """트렌드 뉴스 콘텐츠를 생성합니다."""
        return await self.run(ContentType.TREND)

    async def run_it(self) -> Optional[MemeContent]:
        """IT 뉴스 콘텐츠를 생성합니다."""
        return await self.run(ContentType.IT)
