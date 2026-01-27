"""
트렌드 크롤러 모듈

다양한 소스에서 실시간 트렌드를 수집합니다:
- Google Trends (RSS 피드 기반)
- Naver 실시간 검색어
- 네이버 뉴스 트렌드
"""

import asyncio
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urlencode

import aiohttp

from ..utils.logger import get_logger

logger = get_logger(__name__)

# BeautifulSoup 선택적 import
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    logger.warning("BeautifulSoup not available, some crawling features disabled")


class TrendCrawler:
    """실시간 트렌드를 수집하는 클래스"""

    # Google Trends RSS URL (국가별)
    GOOGLE_TRENDS_RSS = {
        "KR": "https://trends.google.com/trending/rss?geo=KR",
        "US": "https://trends.google.com/trending/rss?geo=US",
        "JP": "https://trends.google.com/trending/rss?geo=JP",
    }

    # 네이버 실시간 검색어 API (비공식)
    NAVER_REALTIME_URL = "https://www.naver.com/"

    # 기본 User-Agent
    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    def __init__(self, config_loader):
        self.config_loader = config_loader
        self.sources_config = config_loader.load("sources")
        self.trend_sources = self.sources_config.get("trend_sources", [])
        self._cache = {}
        self._cache_ttl = 300  # 5분 캐시

    async def get_trends(self, limit: int = 10) -> List[str]:
        """모든 소스에서 트렌드를 수집합니다."""
        tasks = []

        for source in self.trend_sources:
            if not source.get("enabled", True):
                continue

            source_type = source.get("type")
            if source_type == "api":
                tasks.append(self._get_api_trends(source))
            elif source_type == "crawl":
                tasks.append(self._crawl_trends(source))

        # 기본 소스 추가 (설정이 없어도 동작)
        if not tasks:
            tasks.append(self._get_google_trends("KR"))
            tasks.append(self._get_naver_trends())

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_trends = []
        for result in results:
            if isinstance(result, list):
                all_trends.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Trend crawling error: {result}")

        # 중복 제거 및 상위 트렌드 반환
        unique_trends = list(dict.fromkeys(all_trends))
        return unique_trends[:limit]

    async def get_trends_with_metadata(
        self, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """메타데이터와 함께 트렌드를 수집합니다."""
        tasks = [
            self._get_google_trends_with_metadata("KR"),
            self._get_naver_trends_with_metadata(),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_trends = []
        for result in results:
            if isinstance(result, list):
                all_trends.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Trend crawling error: {result}")

        # 중복 제거 (키워드 기준)
        seen = set()
        unique_trends = []
        for trend in all_trends:
            keyword = trend.get("keyword", "").lower()
            if keyword and keyword not in seen:
                seen.add(keyword)
                unique_trends.append(trend)

        # rank 기준 정렬
        unique_trends.sort(key=lambda x: x.get("rank", 999))
        return unique_trends[:limit]

    async def _get_api_trends(self, source: dict) -> List[str]:
        """API를 통해 트렌드를 가져옵니다."""
        source_name = source.get("name", "Unknown")
        logger.info(f"Fetching trends from API: {source_name}")

        if "google" in source_name.lower():
            return await self._get_google_trends(source.get("region", "KR"))

        if "twitter" in source_name.lower() or "x" in source_name.lower():
            return await self._get_twitter_trends(source.get("region", "KR"))

        if "naver" in source_name.lower():
            return await self._get_naver_trends()

        return []

    async def _get_google_trends(self, region: str = "KR") -> List[str]:
        """Google Trends RSS에서 트렌드를 가져옵니다."""
        cache_key = f"google_trends_{region}"

        # 캐시 확인
        if cache_key in self._cache:
            cached_time, cached_data = self._cache[cache_key]
            if (datetime.now() - cached_time).seconds < self._cache_ttl:
                return cached_data

        url = self.GOOGLE_TRENDS_RSS.get(region, self.GOOGLE_TRENDS_RSS["KR"])

        try:
            async with aiohttp.ClientSession() as session:
                headers = {"User-Agent": self.DEFAULT_USER_AGENT}
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status != 200:
                        logger.warning(f"Google Trends RSS failed: {response.status}")
                        return []

                    xml_content = await response.text()
                    trends = self._parse_google_rss(xml_content)

                    # 캐시 저장
                    self._cache[cache_key] = (datetime.now(), trends)
                    logger.info(f"Fetched {len(trends)} trends from Google ({region})")
                    return trends

        except asyncio.TimeoutError:
            logger.error("Google Trends request timeout")
            return []
        except Exception as e:
            logger.error(f"Error fetching Google Trends: {e}")
            return []

    async def _get_google_trends_with_metadata(
        self, region: str = "KR"
    ) -> List[Dict[str, Any]]:
        """메타데이터와 함께 Google Trends를 가져옵니다."""
        url = self.GOOGLE_TRENDS_RSS.get(region, self.GOOGLE_TRENDS_RSS["KR"])

        try:
            async with aiohttp.ClientSession() as session:
                headers = {"User-Agent": self.DEFAULT_USER_AGENT}
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status != 200:
                        return []

                    xml_content = await response.text()
                    return self._parse_google_rss_with_metadata(xml_content, region)

        except Exception as e:
            logger.error(f"Error fetching Google Trends: {e}")
            return []

    def _parse_google_rss(self, xml_content: str) -> List[str]:
        """Google Trends RSS XML을 파싱합니다."""
        trends = []
        try:
            root = ET.fromstring(xml_content)

            # RSS 아이템 찾기
            for item in root.findall(".//item"):
                title = item.find("title")
                if title is not None and title.text:
                    trends.append(title.text.strip())

        except ET.ParseError as e:
            logger.error(f"XML parse error: {e}")

        return trends

    def _parse_google_rss_with_metadata(
        self, xml_content: str, region: str
    ) -> List[Dict[str, Any]]:
        """메타데이터와 함께 Google Trends RSS를 파싱합니다."""
        trends = []
        try:
            root = ET.fromstring(xml_content)

            for idx, item in enumerate(root.findall(".//item"), 1):
                title = item.find("title")
                if title is None or not title.text:
                    continue

                # 트래픽 정보 추출 시도
                traffic_elem = item.find(
                    ".//{https://trends.google.com/trending/rss}approx_traffic"
                )
                traffic = traffic_elem.text if traffic_elem is not None else "N/A"

                # 뉴스 링크 추출
                news_items = item.findall(
                    ".//{https://trends.google.com/trending/rss}news_item"
                )
                news_count = len(news_items)

                trends.append({
                    "keyword": title.text.strip(),
                    "source": "google",
                    "region": region,
                    "rank": idx,
                    "traffic": traffic,
                    "news_count": news_count,
                    "category": "trending",
                    "recorded_at": datetime.now().isoformat()
                })

        except ET.ParseError as e:
            logger.error(f"XML parse error: {e}")

        return trends

    async def _get_naver_trends(self) -> List[str]:
        """네이버에서 실시간 검색어 트렌드를 가져옵니다."""
        cache_key = "naver_trends"

        # 캐시 확인
        if cache_key in self._cache:
            cached_time, cached_data = self._cache[cache_key]
            if (datetime.now() - cached_time).seconds < self._cache_ttl:
                return cached_data

        # 네이버 DataLab 급상승 검색어
        datalab_url = "https://datalab.naver.com/keyword/realtimeList.naver"

        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "User-Agent": self.DEFAULT_USER_AGENT,
                    "Referer": "https://datalab.naver.com/",
                }
                async with session.get(
                    datalab_url, headers=headers, timeout=10
                ) as response:
                    if response.status != 200:
                        # 대체 소스 시도
                        return await self._get_naver_news_keywords()

                    data = await response.json()
                    trends = self._parse_naver_datalab(data)

                    # 캐시 저장
                    self._cache[cache_key] = (datetime.now(), trends)
                    logger.info(f"Fetched {len(trends)} trends from Naver")
                    return trends

        except Exception as e:
            logger.warning(f"Naver DataLab failed: {e}, trying news keywords")
            return await self._get_naver_news_keywords()

    async def _get_naver_trends_with_metadata(self) -> List[Dict[str, Any]]:
        """메타데이터와 함께 네이버 트렌드를 가져옵니다."""
        datalab_url = "https://datalab.naver.com/keyword/realtimeList.naver"

        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "User-Agent": self.DEFAULT_USER_AGENT,
                    "Referer": "https://datalab.naver.com/",
                }
                async with session.get(
                    datalab_url, headers=headers, timeout=10
                ) as response:
                    if response.status != 200:
                        return []

                    data = await response.json()
                    return self._parse_naver_datalab_with_metadata(data)

        except Exception as e:
            logger.error(f"Error fetching Naver trends: {e}")
            return []

    def _parse_naver_datalab(self, data: dict) -> List[str]:
        """네이버 DataLab JSON을 파싱합니다."""
        trends = []
        try:
            # DataLab API 응답 구조에 따라 파싱
            keyword_list = data.get("keywordList", [])
            for item in keyword_list:
                keyword = item.get("keyword") or item.get("title")
                if keyword:
                    trends.append(keyword)
        except Exception as e:
            logger.error(f"Naver DataLab parse error: {e}")

        return trends

    def _parse_naver_datalab_with_metadata(
        self, data: dict
    ) -> List[Dict[str, Any]]:
        """메타데이터와 함께 네이버 DataLab을 파싱합니다."""
        trends = []
        try:
            keyword_list = data.get("keywordList", [])
            for idx, item in enumerate(keyword_list, 1):
                keyword = item.get("keyword") or item.get("title")
                if not keyword:
                    continue

                trends.append({
                    "keyword": keyword,
                    "source": "naver",
                    "region": "KR",
                    "rank": item.get("rank", idx),
                    "traffic": item.get("searchCnt", "N/A"),
                    "category": item.get("category", "general"),
                    "recorded_at": datetime.now().isoformat()
                })
        except Exception as e:
            logger.error(f"Naver DataLab parse error: {e}")

        return trends

    async def _get_naver_news_keywords(self) -> List[str]:
        """네이버 뉴스에서 키워드를 추출합니다 (대체 소스)."""
        if not BS4_AVAILABLE:
            return []

        news_url = "https://news.naver.com/"

        try:
            async with aiohttp.ClientSession() as session:
                headers = {"User-Agent": self.DEFAULT_USER_AGENT}
                async with session.get(
                    news_url, headers=headers, timeout=10
                ) as response:
                    if response.status != 200:
                        return []

                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")

                    trends = []

                    # 주요 뉴스 헤드라인에서 키워드 추출
                    headlines = soup.select(
                        ".cjs_t, .hdline_article_tit, .news_tit"
                    )
                    for headline in headlines[:20]:
                        text = headline.get_text(strip=True)
                        # 간단한 키워드 추출 (명사 추출 등은 별도 NLP 필요)
                        if text and len(text) > 3:
                            # 따옴표 안의 키워드 추출
                            quoted = re.findall(r"['\"](.+?)['\"]", text)
                            if quoted:
                                trends.extend(quoted)
                            # 또는 제목 자체를 트렌드로
                            elif len(text) < 30:
                                trends.append(text)

                    logger.info(f"Extracted {len(trends)} keywords from Naver News")
                    return list(dict.fromkeys(trends))[:10]

        except Exception as e:
            logger.error(f"Error extracting Naver news keywords: {e}")
            return []

    async def _get_twitter_trends(self, region: str = "KR") -> List[str]:
        """Twitter/X 트렌드를 가져옵니다 (제한적 기능)."""
        # Twitter API는 인증 필요, 대안으로 트렌드 스크래핑 시도
        # 실제 프로덕션에서는 Twitter API v2 사용 권장

        logger.info(f"Twitter trends for {region}: API authentication required")

        # 한국 관련 기본 트렌드 태그 (fallback)
        return []

    async def _crawl_trends(self, source: dict) -> List[str]:
        """웹 크롤링으로 트렌드를 가져옵니다."""
        if not BS4_AVAILABLE:
            logger.warning("BeautifulSoup not available for crawling")
            return []

        url = source.get("url")
        source_name = source.get("name", "Unknown")

        if not url:
            return []

        try:
            async with aiohttp.ClientSession() as session:
                headers = {"User-Agent": self.DEFAULT_USER_AGENT}
                async with session.get(
                    url, headers=headers, timeout=10
                ) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to fetch {url}: {response.status}")
                        return []

                    html = await response.text()
                    return self._parse_trends_html(html, source_name)

        except Exception as e:
            logger.error(f"Error crawling trends from {url}: {e}")
            return []

    def _parse_trends_html(self, html: str, source_name: str) -> List[str]:
        """HTML에서 트렌드 키워드를 추출합니다."""
        if not BS4_AVAILABLE:
            return []

        soup = BeautifulSoup(html, "html.parser")
        trends = []

        # Naver DataLab 파싱
        if "naver" in source_name.lower():
            trend_elements = soup.select(
                ".keyword_rank .item_title, .realtime_kwd_text"
            )
            for elem in trend_elements:
                text = elem.get_text(strip=True)
                if text:
                    trends.append(text)

        # 일반적인 트렌드 리스트 패턴
        else:
            # 순위 기반 리스트
            rank_elements = soup.select(
                "[class*='rank'] a, [class*='trend'] a, [class*='keyword'] a"
            )
            for elem in rank_elements[:20]:
                text = elem.get_text(strip=True)
                if text and len(text) > 1:
                    trends.append(text)

        logger.info(f"Parsed {len(trends)} trends from {source_name}")
        return trends

    async def get_trend_context(self, trend: str) -> Dict[str, Any]:
        """특정 트렌드에 대한 추가 맥락을 가져옵니다."""
        context = {
            "keyword": trend,
            "related_keywords": [],
            "news_count": 0,
            "sentiment": "neutral",
            "category": "unknown",
            "search_volume": 0,
        }

        try:
            # 네이버 뉴스 검색으로 관련 정보 수집
            news_info = await self._search_naver_news(trend)
            context["news_count"] = news_info.get("count", 0)
            context["related_keywords"] = news_info.get("keywords", [])

            # 카테고리 추론
            context["category"] = self._infer_category(trend, news_info)

        except Exception as e:
            logger.error(f"Error getting trend context for {trend}: {e}")

        return context

    async def _search_naver_news(self, keyword: str) -> Dict[str, Any]:
        """네이버 뉴스에서 키워드 검색 결과를 가져옵니다."""
        if not BS4_AVAILABLE:
            return {"count": 0, "keywords": []}

        encoded_keyword = quote(keyword)
        search_url = f"https://search.naver.com/search.naver?where=news&query={encoded_keyword}"

        try:
            async with aiohttp.ClientSession() as session:
                headers = {"User-Agent": self.DEFAULT_USER_AGENT}
                async with session.get(
                    search_url, headers=headers, timeout=10
                ) as response:
                    if response.status != 200:
                        return {"count": 0, "keywords": []}

                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")

                    # 뉴스 개수 추출
                    count_elem = soup.select_one(".title_desc")
                    count = 0
                    if count_elem:
                        count_match = re.search(
                            r"([\d,]+)\s*건", count_elem.get_text()
                        )
                        if count_match:
                            count = int(count_match.group(1).replace(",", ""))

                    # 관련 검색어 추출
                    related = []
                    related_elems = soup.select(".related_keyword a")
                    for elem in related_elems[:5]:
                        text = elem.get_text(strip=True)
                        if text:
                            related.append(text)

                    return {"count": count, "keywords": related}

        except Exception as e:
            logger.error(f"Error searching Naver news: {e}")
            return {"count": 0, "keywords": []}

    def _infer_category(
        self, keyword: str, news_info: Dict[str, Any]
    ) -> str:
        """키워드의 카테고리를 추론합니다."""
        keyword_lower = keyword.lower()

        # 카테고리 키워드 매핑
        categories = {
            "entertainment": ["가수", "배우", "드라마", "영화", "아이돌", "연예", "콘서트"],
            "sports": ["축구", "야구", "농구", "올림픽", "선수", "경기", "스포츠"],
            "politics": ["정치", "대통령", "국회", "선거", "정당", "법안"],
            "economy": ["주식", "코인", "환율", "금리", "경제", "투자", "부동산"],
            "tech": ["AI", "인공지능", "IT", "테크", "앱", "서비스", "출시"],
            "social": ["사건", "사고", "논란", "이슈", "화제"],
        }

        for category, keywords in categories.items():
            for kw in keywords:
                if kw in keyword_lower:
                    return category

        # 뉴스 수가 많으면 이슈성
        if news_info.get("count", 0) > 100:
            return "trending"

        return "general"

    async def get_all_trends_categorized(
        self, limit_per_category: int = 5
    ) -> Dict[str, List[Dict[str, Any]]]:
        """카테고리별로 분류된 트렌드를 가져옵니다."""
        trends = await self.get_trends_with_metadata(limit=50)

        categorized = {}
        for trend in trends:
            # 카테고리 추론
            if "category" not in trend or trend["category"] == "trending":
                trend["category"] = self._infer_category(
                    trend["keyword"], {}
                )

            category = trend.get("category", "general")
            if category not in categorized:
                categorized[category] = []

            if len(categorized[category]) < limit_per_category:
                categorized[category].append(trend)

        return categorized

    def clear_cache(self):
        """캐시를 초기화합니다."""
        self._cache.clear()
        logger.info("Trend cache cleared")
