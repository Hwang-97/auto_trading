"""
콘텐츠 생성 파이프라인 모듈

뉴스 수집부터 밈 생성까지 전체 파이프라인을 관리합니다.
상태 영속성과 에러 복구 기능을 포함합니다.
"""

import asyncio
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

from ..utils.logger import get_logger

logger = get_logger(__name__)


class ContentType(Enum):
    """콘텐츠 유형"""
    DAILY = "daily"
    TREND = "trend"
    IT = "it"
    STOCK = "stock"


class PipelineStep(Enum):
    """파이프라인 단계"""
    INIT = "init"
    COLLECT = "collect"
    GENERATE_TEXT = "generate_text"
    GENERATE_IMAGE = "generate_image"
    GENERATE_SCRIPT = "generate_script"
    GENERATE_VIDEO = "generate_video"
    GENERATE_THUMBNAIL = "generate_thumbnail"
    COMPLETE = "complete"
    FAILED = "failed"


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

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "title": self.title,
            "content": self.content,
            "source": self.source,
            "url": self.url,
            "published_at": self.published_at.isoformat(),
            "category": self.category,
            "relevance_score": self.relevance_score
        }
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NewsItem":
        data = data.copy()
        if "published_at" in data and isinstance(data["published_at"], str):
            data["published_at"] = datetime.fromisoformat(data["published_at"])
        return cls(**data)


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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel_name": self.channel_name,
            "content_type": self.content_type.value,
            "news_items": [item.to_dict() for item in self.news_items],
            "meme_text": self.meme_text,
            "top_text": self.top_text,
            "bottom_text": self.bottom_text,
            "narration": self.narration,
            "image_path": self.image_path,
            "video_path": self.video_path,
            "thumbnail_path": self.thumbnail_path,
            "script": self.script,
            "hashtags": self.hashtags,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemeContent":
        data = data.copy()
        data["content_type"] = ContentType(data.get("content_type", "daily"))
        data["news_items"] = [
            NewsItem.from_dict(item) for item in data.get("news_items", [])
        ]
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)


@dataclass
class PipelineState:
    """파이프라인 상태"""
    id: str
    channel_name: str
    current_step: PipelineStep
    content: Optional[MemeContent]
    started_at: datetime
    updated_at: datetime
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    step_history: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "channel_name": self.channel_name,
            "current_step": self.current_step.value,
            "content": self.content.to_dict() if self.content else None,
            "started_at": self.started_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "error_message": self.error_message,
            "step_history": self.step_history
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PipelineState":
        data = data.copy()
        data["current_step"] = PipelineStep(data["current_step"])
        if data.get("content"):
            data["content"] = MemeContent.from_dict(data["content"])
        data["started_at"] = datetime.fromisoformat(data["started_at"])
        data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        return cls(**data)


class PipelineStateManager:
    """파이프라인 상태 관리자"""

    def __init__(self, state_dir: str = "data/pipeline_states"):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def _get_state_path(self, state_id: str) -> Path:
        return self.state_dir / f"{state_id}.json"

    def save_state(self, state: PipelineState) -> None:
        """상태를 파일에 저장"""
        state_path = self._get_state_path(state.id)
        with open(state_path, 'w', encoding='utf-8') as f:
            json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)
        logger.debug(f"State saved: {state.id}")

    def load_state(self, state_id: str) -> Optional[PipelineState]:
        """파일에서 상태를 로드"""
        state_path = self._get_state_path(state_id)
        if not state_path.exists():
            return None

        try:
            with open(state_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return PipelineState.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load state {state_id}: {e}")
            return None

    def delete_state(self, state_id: str) -> None:
        """상태 파일 삭제"""
        state_path = self._get_state_path(state_id)
        if state_path.exists():
            state_path.unlink()
            logger.debug(f"State deleted: {state_id}")

    def get_pending_states(self) -> List[PipelineState]:
        """완료되지 않은 상태 목록 조회"""
        pending = []
        for state_file in self.state_dir.glob("*.json"):
            state = self.load_state(state_file.stem)
            if state and state.current_step not in (PipelineStep.COMPLETE, PipelineStep.FAILED):
                pending.append(state)
        return pending

    def cleanup_old_states(self, days: int = 7) -> int:
        """오래된 상태 파일 정리"""
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=days)
        cleaned = 0

        for state_file in self.state_dir.glob("*.json"):
            state = self.load_state(state_file.stem)
            if state and state.updated_at < cutoff:
                self.delete_state(state.id)
                cleaned += 1

        logger.info(f"Cleaned up {cleaned} old pipeline states")
        return cleaned


class Pipeline:
    """콘텐츠 생성 파이프라인 (상태 영속성 지원)"""

    def __init__(self, config_loader, state_dir: str = None):
        """
        파이프라인을 초기화합니다.

        Args:
            config_loader: ConfigLoader 인스턴스
            state_dir: 상태 저장 디렉토리
        """
        self.config_loader = config_loader
        self.news_crawler = None
        self.trend_crawler = None
        self.ai_generator = None
        self.text_gen = None
        self.image_gen = None
        self.video_gen = None
        self._initialized = False

        # 상태 관리자
        if state_dir is None:
            state_dir = str(Path(config_loader.get_output_path()) / "pipeline_states")
        self.state_manager = PipelineStateManager(state_dir)

        # 콜백
        self._on_step_complete: Optional[Callable] = None
        self._on_error: Optional[Callable] = None

    def on_step_complete(self, callback: Callable) -> None:
        """단계 완료 콜백 설정"""
        self._on_step_complete = callback

    def on_error(self, callback: Callable) -> None:
        """에러 콜백 설정"""
        self._on_error = callback

    async def initialize(self) -> None:
        """파이프라인 컴포넌트들을 초기화합니다."""
        if self._initialized:
            return

        from ..content.news_crawler import NewsCrawler
        from ..content.trend_crawler import TrendCrawler
        from ..meme.text_gen import TextGenerator
        from ..meme.image_gen import ImageGenerator
        from ..meme.video_gen import VideoGenerator

        # AIGenerator는 선택적 import
        try:
            from ..content.ai_generator import AIGenerator
            self.ai_generator = AIGenerator(self.config_loader)
        except Exception as e:
            logger.warning(f"AIGenerator not available: {e}")
            self.ai_generator = None

        self.news_crawler = NewsCrawler(self.config_loader)
        self.trend_crawler = TrendCrawler(self.config_loader)
        self.text_gen = TextGenerator(self.config_loader)
        self.image_gen = ImageGenerator(self.config_loader)
        self.video_gen = VideoGenerator(self.config_loader)

        self._initialized = True
        logger.info("Pipeline initialized successfully")

    async def run_channel(
        self,
        channel_name: str,
        dry_run: bool = False,
        resume_state_id: str = None
    ) -> Optional[MemeContent]:
        """
        특정 채널에 대해 파이프라인을 실행합니다.

        Args:
            channel_name: 채널 이름
            dry_run: True면 실제 생성 없이 테스트만 수행
            resume_state_id: 재개할 상태 ID

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

        # 상태 초기화 또는 복구
        if resume_state_id:
            state = self.state_manager.load_state(resume_state_id)
            if not state:
                logger.error(f"State not found: {resume_state_id}")
                return None
            logger.info(f"Resuming pipeline from step: {state.current_step.value}")
        else:
            state_id = f"{channel_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            state = PipelineState(
                id=state_id,
                channel_name=channel_name,
                current_step=PipelineStep.INIT,
                content=MemeContent(
                    channel_name=channel_name,
                    content_type=content_type
                ),
                started_at=datetime.now(),
                updated_at=datetime.now()
            )

        logger.info(f"Starting pipeline for channel: {channel_name} ({category})")

        if dry_run:
            logger.info("[DRY RUN] Would generate content for channel: %s", channel_name)
            return MemeContent(
                channel_name=channel_name,
                content_type=content_type,
                meme_text="[DRY RUN] 테스트 밈 텍스트",
            )

        try:
            # 파이프라인 단계별 실행
            result = await self._execute_pipeline(state, channel_config)

            # 성공 시 상태 파일 삭제
            if result:
                self.state_manager.delete_state(state.id)

            return result

        except Exception as e:
            logger.error(f"Pipeline error for {channel_name}: {e}")
            state.error_message = str(e)
            state.current_step = PipelineStep.FAILED
            state.updated_at = datetime.now()
            self.state_manager.save_state(state)

            if self._on_error:
                self._on_error(state, e)

            raise

    async def _execute_pipeline(
        self,
        state: PipelineState,
        channel_config: Dict[str, Any]
    ) -> Optional[MemeContent]:
        """파이프라인 단계별 실행"""

        steps = [
            (PipelineStep.COLLECT, self._step_collect),
            (PipelineStep.GENERATE_TEXT, self._step_generate_text),
            (PipelineStep.GENERATE_IMAGE, self._step_generate_image),
            (PipelineStep.GENERATE_SCRIPT, self._step_generate_script),
            (PipelineStep.GENERATE_VIDEO, self._step_generate_video),
            (PipelineStep.GENERATE_THUMBNAIL, self._step_generate_thumbnail),
        ]

        # 현재 단계 이후부터 실행
        current_idx = 0
        for i, (step, _) in enumerate(steps):
            if step == state.current_step:
                current_idx = i
                break

        for step, handler in steps[current_idx:]:
            state.current_step = step
            state.updated_at = datetime.now()
            self.state_manager.save_state(state)

            try:
                logger.info(f"Executing step: {step.value}")
                await handler(state, channel_config)

                # 단계 기록
                state.step_history.append({
                    "step": step.value,
                    "completed_at": datetime.now().isoformat(),
                    "success": True
                })

                if self._on_step_complete:
                    self._on_step_complete(state, step)

            except Exception as e:
                logger.error(f"Step {step.value} failed: {e}")

                # 재시도
                if state.retry_count < state.max_retries:
                    state.retry_count += 1
                    logger.info(f"Retrying step {step.value} ({state.retry_count}/{state.max_retries})")
                    await asyncio.sleep(2 ** state.retry_count)  # 지수 백오프
                    continue

                state.step_history.append({
                    "step": step.value,
                    "completed_at": datetime.now().isoformat(),
                    "success": False,
                    "error": str(e)
                })
                raise

        # 완료
        state.current_step = PipelineStep.COMPLETE
        state.updated_at = datetime.now()
        self.state_manager.save_state(state)

        logger.info(f"Pipeline completed for {state.channel_name}")
        return state.content

    async def _step_collect(
        self, state: PipelineState, channel_config: Dict[str, Any]
    ) -> None:
        """콘텐츠 수집 단계"""
        content_type = state.content.content_type
        news_items = await self._collect_content(content_type, channel_config)

        if not news_items:
            logger.warning(f"No content collected for {state.channel_name}")
            # 기본 콘텐츠 생성
            news_items = [NewsItem(
                title="오늘의 이슈",
                content="일상 공감 콘텐츠",
                source="default",
                url="",
                published_at=datetime.now(),
                category=content_type.value
            )]

        state.content.news_items = news_items
        logger.info(f"Collected {len(news_items)} items")

    async def _step_generate_text(
        self, state: PipelineState, channel_config: Dict[str, Any]
    ) -> None:
        """텍스트 생성 단계"""
        if not self.ai_generator:
            # AI 없이 기본 텍스트 생성
            state.content.meme_text = state.content.news_items[0].title if state.content.news_items else "오늘의 밈"
            state.content.top_text = ""
            state.content.bottom_text = state.content.meme_text
            state.content.narration = state.content.meme_text
            state.content.hashtags = ["#밈", "#Shorts", "#일상"]
            return

        meme_result = await self._generate_meme_text(state.content, channel_config)
        state.content.meme_text = meme_result.get("meme_text", "")
        state.content.top_text = meme_result.get("top_text", "")
        state.content.bottom_text = meme_result.get("bottom_text", "")
        state.content.narration = meme_result.get("narration", "")
        state.content.hashtags = meme_result.get("hashtags", [])

    async def _step_generate_image(
        self, state: PipelineState, channel_config: Dict[str, Any]
    ) -> None:
        """이미지 생성 단계"""
        state.content.image_path = await self.image_gen.generate(state.content)
        logger.info(f"Image generated: {state.content.image_path}")

    async def _step_generate_script(
        self, state: PipelineState, channel_config: Dict[str, Any]
    ) -> None:
        """스크립트 생성 단계"""
        if self.ai_generator:
            state.content.script = await self.ai_generator.generate_script(
                state.content,
                duration=30
            )
        else:
            state.content.script = state.content.narration

    async def _step_generate_video(
        self, state: PipelineState, channel_config: Dict[str, Any]
    ) -> None:
        """비디오 생성 단계"""
        state.content.video_path = await self.video_gen.generate(state.content)
        logger.info(f"Video generated: {state.content.video_path}")

    async def _step_generate_thumbnail(
        self, state: PipelineState, channel_config: Dict[str, Any]
    ) -> None:
        """썸네일 생성 단계"""
        state.content.thumbnail_path = await self.image_gen.generate_thumbnail(state.content)
        logger.info(f"Thumbnail generated: {state.content.thumbnail_path}")

    async def run(self, content_type: ContentType) -> Optional[MemeContent]:
        """
        콘텐츠 타입에 대해 파이프라인을 실행합니다 (레거시 호환).
        """
        channel_map = {
            ContentType.DAILY: "daily_meme",
            ContentType.TREND: "trend_meme",
            ContentType.IT: "it_meme",
            ContentType.STOCK: "it_meme",
        }
        channel_name = channel_map.get(content_type, "daily_meme")
        return await self.run_channel(channel_name)

    async def resume_pending(self) -> List[MemeContent]:
        """미완료된 파이프라인 재개"""
        pending_states = self.state_manager.get_pending_states()
        results = []

        for state in pending_states:
            logger.info(f"Resuming pending pipeline: {state.id}")
            try:
                channel_config = self.config_loader.get_channel(state.channel_name)
                if channel_config:
                    result = await self._execute_pipeline(state, channel_config)
                    if result:
                        results.append(result)
                        self.state_manager.delete_state(state.id)
            except Exception as e:
                logger.error(f"Failed to resume pipeline {state.id}: {e}")

        return results

    async def _collect_content(
        self,
        content_type: ContentType,
        channel_config: Dict[str, Any]
    ) -> List[NewsItem]:
        """콘텐츠 타입에 따라 데이터를 수집합니다."""
        source_config = self.config_loader.get_source(content_type.value)

        if content_type == ContentType.DAILY:
            topics = source_config.get("topics", []) if source_config else []
            return await self._generate_daily_topics(topics)

        elif content_type == ContentType.TREND:
            trends = await self.trend_crawler.get_trends(limit=10)
            if trends:
                return await self.news_crawler.crawl_by_keywords(trends, limit=5)
            return []

        elif content_type in (ContentType.IT, ContentType.STOCK):
            return await self.news_crawler.crawl_by_category(content_type.value, limit=10)

        return []

    async def _generate_daily_topics(
        self,
        topics: List[Dict[str, Any]]
    ) -> List[NewsItem]:
        """일상 주제를 기반으로 가상의 뉴스 아이템을 생성합니다."""
        import random

        if not topics:
            topics = [
                {"name": "직장생활", "keywords": ["출근", "월요병", "야근"]},
                {"name": "일상", "keywords": ["주말", "배달", "넷플릭스"]},
            ]

        weights = [t.get("weight", 1.0) for t in topics]
        selected_topic = random.choices(topics, weights=weights, k=1)[0]
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
        """AI를 사용하여 밈 텍스트를 생성합니다."""
        content_config = channel_config.get("content", {})
        style = content_config.get("style", "humorous")

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
