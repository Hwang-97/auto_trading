"""
뉴스 크롤러 모듈
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional

import aiohttp

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    feedparser = None
    FEEDPARSER_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BeautifulSoup = None
    BS4_AVAILABLE = False

from ..core.pipeline import NewsItem
from ..utils.logger import get_logger

logger = get_logger(__name__)


class NewsCrawler:
    """RSS 피드 및 웹 크롤링으로 뉴스를 수집하는 클래스"""

    def __init__(self, config_loader):
        self.config_loader = config_loader
        self.sources_config = config_loader.load("sources")
        self.crawl_settings = self.sources_config.get("crawl_settings", {})
        self.filters = self.sources_config.get("filters", {})

    async def crawl_daily_news(self, limit: int = 10) -> List[NewsItem]:
        """일반 뉴스를 크롤링합니다."""
        feeds = self.sources_config.get("rss_feeds", {}).get("general", [])
        return await self._crawl_feeds(feeds, limit)

    async def crawl_tech_news(self, limit: int = 10) -> List[NewsItem]:
        """IT/테크 뉴스를 크롤링합니다."""
        feeds = self.sources_config.get("rss_feeds", {}).get("tech", [])
        return await self._crawl_feeds(feeds, limit)

    async def crawl_by_category(
        self, category: str, limit: int = 10
    ) -> List[NewsItem]:
        """특정 카테고리의 뉴스를 크롤링합니다.

        Args:
            category: 카테고리 이름 (it, stock, daily 등)
            limit: 최대 반환 개수

        Returns:
            뉴스 아이템 리스트
        """
        # sources.yaml에서 카테고리별 RSS 피드 가져오기
        source_config = self.config_loader.get_source(category)
        if not source_config:
            logger.warning(f"No source config found for category: {category}")
            return []

        # sources.yaml에서는 'feeds' 키를 사용
        feeds = source_config.get("feeds", [])
        if not feeds:
            logger.warning(f"No feeds found for category: {category}")
            return []

        return await self._crawl_feeds(feeds, limit)

    async def crawl_by_keywords(
        self, keywords: List[str], limit: int = 10
    ) -> List[NewsItem]:
        """키워드로 뉴스를 검색합니다."""
        all_news = []
        all_feeds = []
        for category in self.sources_config.get("rss_feeds", {}).values():
            all_feeds.extend(category)

        news_items = await self._crawl_feeds(all_feeds, limit * 2)

        for item in news_items:
            for keyword in keywords:
                if keyword.lower() in item.title.lower() or keyword.lower() in item.content.lower():
                    item.relevance_score = self._calculate_relevance(item, keywords)
                    all_news.append(item)
                    break

        all_news.sort(key=lambda x: x.relevance_score, reverse=True)
        return all_news[:limit]

    async def _crawl_feeds(
        self, feeds: List[dict], limit: int
    ) -> List[NewsItem]:
        """RSS 피드들을 크롤링합니다."""
        tasks = [self._parse_feed(feed) for feed in feeds]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_items = []
        for result in results:
            if isinstance(result, list):
                all_items.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Feed parsing error: {result}")

        # 시간순 정렬 및 필터링
        all_items = self._filter_items(all_items)
        all_items.sort(key=lambda x: x.published_at, reverse=True)

        return all_items[:limit]

    async def _parse_feed(self, feed_config: dict) -> List[NewsItem]:
        """단일 RSS 피드를 파싱합니다."""
        if not FEEDPARSER_AVAILABLE:
            logger.warning("feedparser not available, skipping RSS feed parsing")
            return []

        url = feed_config.get("url")
        source = feed_config.get("name")
        category = feed_config.get("category", "general")

        try:
            async with aiohttp.ClientSession() as session:
                headers = {"User-Agent": self.crawl_settings.get("user_agent", "MemeNews Bot/1.0")}
                timeout = aiohttp.ClientTimeout(total=self.crawl_settings.get("timeout", 30))

                async with session.get(url, headers=headers, timeout=timeout) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to fetch {url}: {response.status}")
                        return []

                    content = await response.text()
                    feed = feedparser.parse(content)

            items = []
            for entry in feed.entries[:20]:
                try:
                    published = self._parse_date(entry.get("published", ""))
                    item = NewsItem(
                        title=entry.get("title", ""),
                        content=self._clean_content(entry.get("summary", "")),
                        source=source,
                        url=entry.get("link", ""),
                        published_at=published,
                        category=category,
                    )
                    items.append(item)
                except Exception as e:
                    logger.debug(f"Error parsing entry: {e}")

            logger.info(f"Parsed {len(items)} items from {source}")
            return items

        except Exception as e:
            logger.error(f"Error fetching feed {url}: {e}")
            return []

    def _parse_date(self, date_str: str) -> datetime:
        """날짜 문자열을 파싱합니다."""
        if not date_str:
            return datetime.now()

        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except Exception:
            return datetime.now()

    def _clean_content(self, content: str) -> str:
        """HTML 태그를 제거하고 텍스트를 정리합니다."""
        if BS4_AVAILABLE and BeautifulSoup:
            soup = BeautifulSoup(content, "html.parser")
            text = soup.get_text(separator=" ", strip=True)
        else:
            # 간단한 HTML 태그 제거
            import re
            text = re.sub(r'<[^>]+>', '', content)
            text = ' '.join(text.split())
        return text[:1000]  # 길이 제한

    def _filter_items(self, items: List[NewsItem]) -> List[NewsItem]:
        """필터링 조건을 적용합니다."""
        exclude_keywords = self.filters.get("exclude_keywords", [])
        min_length = self.filters.get("min_content_length", 100)
        max_age = self.filters.get("max_age_hours", 24)
        cutoff_time = datetime.now() - timedelta(hours=max_age)

        filtered = []
        for item in items:
            # 제외 키워드 체크
            if any(kw in item.title for kw in exclude_keywords):
                continue

            # 최소 길이 체크
            if len(item.content) < min_length:
                continue

            # 시간 체크
            if item.published_at < cutoff_time:
                continue

            filtered.append(item)

        return filtered

    def _calculate_relevance(self, item: NewsItem, keywords: List[str]) -> float:
        """키워드 관련성 점수를 계산합니다."""
        score = 0.0
        text = (item.title + " " + item.content).lower()

        for keyword in keywords:
            keyword_lower = keyword.lower()
            # 제목에 있으면 높은 점수
            if keyword_lower in item.title.lower():
                score += 0.5
            # 본문에 있으면 추가 점수
            count = text.count(keyword_lower)
            score += min(count * 0.1, 0.3)

        return min(score, 1.0)
