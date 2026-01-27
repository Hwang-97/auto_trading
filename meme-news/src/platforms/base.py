"""
플랫폼 베이스 클래스

업로드, 인증, 에러 처리 및 재시도 로직을 포함합니다.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from ..core.pipeline import MemeContent
from ..utils.logger import get_logger
from ..utils.retry import async_retry, AsyncCircuitBreaker, RetryError

logger = get_logger(__name__)


class UploadStatus(Enum):
    """업로드 상태"""
    PENDING = "pending"
    UPLOADING = "uploading"
    SUCCESS = "success"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    AUTH_ERROR = "auth_error"


class PlatformError(Exception):
    """플랫폼 에러 기본 클래스"""
    def __init__(self, message: str, platform: str, recoverable: bool = True):
        super().__init__(message)
        self.platform = platform
        self.recoverable = recoverable


class AuthenticationError(PlatformError):
    """인증 에러"""
    def __init__(self, message: str, platform: str):
        super().__init__(message, platform, recoverable=True)


class UploadError(PlatformError):
    """업로드 에러"""
    pass


class RateLimitError(PlatformError):
    """레이트 리밋 에러"""
    def __init__(self, message: str, platform: str, retry_after: int = 60):
        super().__init__(message, platform, recoverable=True)
        self.retry_after = retry_after


class QuotaExceededError(PlatformError):
    """할당량 초과 에러"""
    def __init__(self, message: str, platform: str):
        super().__init__(message, platform, recoverable=False)


class ContentRejectedError(PlatformError):
    """콘텐츠 거부 에러"""
    def __init__(self, message: str, platform: str, reason: str = None):
        super().__init__(message, platform, recoverable=False)
        self.reason = reason


@dataclass
class UploadResult:
    """업로드 결과"""
    status: UploadStatus
    platform: str
    content_id: Optional[str] = None
    url: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    uploaded_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "platform": self.platform,
            "content_id": self.content_id,
            "url": self.url,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "metadata": self.metadata
        }


class BasePlatform(ABC):
    """플랫폼 업로드 기본 클래스 (에러 처리 및 재시도 포함)"""

    # 기본 재시도 설정
    MAX_RETRIES = 3
    RETRY_DELAY = 5.0
    MAX_RETRY_DELAY = 120.0

    def __init__(self, config_loader):
        self.config_loader = config_loader
        self.platforms_config = config_loader.load("platforms")
        self._authenticated = False

        # 콜백
        self._on_upload_start: Optional[Callable] = None
        self._on_upload_complete: Optional[Callable] = None
        self._on_upload_error: Optional[Callable] = None

        # Circuit Breaker
        self._circuit_breaker = AsyncCircuitBreaker(
            failure_threshold=5,
            recovery_timeout=300.0,  # 5분
            expected_exceptions=(ConnectionError, TimeoutError)
        )

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """플랫폼 이름을 반환합니다."""
        pass

    @property
    def config(self) -> dict:
        """플랫폼별 설정을 반환합니다."""
        return self.platforms_config.get("platforms", {}).get(self.platform_name, {})

    @property
    def is_enabled(self) -> bool:
        """플랫폼이 활성화되어 있는지 확인합니다."""
        return self.config.get("enabled", False)

    @property
    def retry_config(self) -> dict:
        """재시도 설정을 반환합니다."""
        return self.config.get("retry", {
            "max_retries": self.MAX_RETRIES,
            "delay": self.RETRY_DELAY,
            "max_delay": self.MAX_RETRY_DELAY
        })

    # ===== 콜백 설정 =====

    def on_upload_start(self, callback: Callable) -> None:
        """업로드 시작 콜백 설정"""
        self._on_upload_start = callback

    def on_upload_complete(self, callback: Callable) -> None:
        """업로드 완료 콜백 설정"""
        self._on_upload_complete = callback

    def on_upload_error(self, callback: Callable) -> None:
        """업로드 에러 콜백 설정"""
        self._on_upload_error = callback

    # ===== 추상 메서드 =====

    @abstractmethod
    async def _authenticate_impl(self) -> bool:
        """플랫폼 인증 구현"""
        pass

    @abstractmethod
    async def _upload_impl(self, content: MemeContent, metadata: dict) -> UploadResult:
        """업로드 구현"""
        pass

    @abstractmethod
    async def _get_analytics_impl(self, content_id: str) -> dict:
        """분석 데이터 조회 구현"""
        pass

    # ===== 공개 메서드 (에러 처리 포함) =====

    async def authenticate(self) -> bool:
        """플랫폼 인증을 수행합니다 (재시도 포함)."""
        if self._authenticated:
            return True

        retry_config = self.retry_config
        max_retries = retry_config.get("max_retries", self.MAX_RETRIES)
        delay = retry_config.get("delay", self.RETRY_DELAY)

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Authenticating with {self.platform_name} (attempt {attempt})")
                self._authenticated = await self._authenticate_impl()

                if self._authenticated:
                    logger.info(f"Successfully authenticated with {self.platform_name}")
                    return True
                else:
                    logger.warning(f"Authentication failed for {self.platform_name}")

            except Exception as e:
                logger.error(f"Authentication error for {self.platform_name}: {e}")

                if attempt < max_retries:
                    wait_time = delay * (2 ** (attempt - 1))
                    logger.info(f"Retrying authentication in {wait_time:.1f}s...")
                    await asyncio.sleep(wait_time)
                else:
                    raise AuthenticationError(
                        f"Failed to authenticate after {max_retries} attempts: {e}",
                        self.platform_name
                    )

        return False

    async def upload(self, content: MemeContent, metadata: dict = None) -> UploadResult:
        """
        콘텐츠를 업로드합니다 (재시도 및 에러 처리 포함).

        Args:
            content: MemeContent 객체
            metadata: 추가 메타데이터

        Returns:
            UploadResult 객체
        """
        metadata = metadata or {}
        retry_config = self.retry_config
        max_retries = retry_config.get("max_retries", self.MAX_RETRIES)
        delay = retry_config.get("delay", self.RETRY_DELAY)
        max_delay = retry_config.get("max_delay", self.MAX_RETRY_DELAY)

        # Circuit Breaker 확인
        if not self._circuit_breaker.can_execute():
            logger.warning(f"Circuit breaker open for {self.platform_name}")
            return UploadResult(
                status=UploadStatus.FAILED,
                platform=self.platform_name,
                error_message="Circuit breaker is open - too many recent failures"
            )

        # 콘텐츠 검증
        if not await self.validate_content(content):
            return UploadResult(
                status=UploadStatus.FAILED,
                platform=self.platform_name,
                error_message="Content validation failed"
            )

        # 인증 확인
        if not self._authenticated:
            try:
                await self.authenticate()
            except AuthenticationError as e:
                return UploadResult(
                    status=UploadStatus.AUTH_ERROR,
                    platform=self.platform_name,
                    error_message=str(e)
                )

        # 업로드 시작 콜백
        if self._on_upload_start:
            self._on_upload_start(content, self.platform_name)

        # 재시도 루프
        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(
                    f"Uploading to {self.platform_name} (attempt {attempt}/{max_retries})"
                )

                result = await self._upload_impl(content, metadata)
                result.retry_count = attempt - 1

                if result.status == UploadStatus.SUCCESS:
                    self._circuit_breaker.record_success()

                    # 완료 콜백
                    if self._on_upload_complete:
                        self._on_upload_complete(result)

                    self.log_upload_result(True, result.url)
                    return result

                # 복구 불가능한 에러
                if result.status in (UploadStatus.AUTH_ERROR,):
                    return result

            except RateLimitError as e:
                logger.warning(f"Rate limited by {self.platform_name}: {e}")
                wait_time = e.retry_after

                if attempt < max_retries:
                    logger.info(f"Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                else:
                    return UploadResult(
                        status=UploadStatus.RATE_LIMITED,
                        platform=self.platform_name,
                        error_message=str(e),
                        retry_count=attempt
                    )

            except QuotaExceededError as e:
                logger.error(f"Quota exceeded for {self.platform_name}: {e}")
                return UploadResult(
                    status=UploadStatus.FAILED,
                    platform=self.platform_name,
                    error_message=str(e),
                    retry_count=attempt
                )

            except ContentRejectedError as e:
                logger.error(f"Content rejected by {self.platform_name}: {e}")
                return UploadResult(
                    status=UploadStatus.FAILED,
                    platform=self.platform_name,
                    error_message=f"Content rejected: {e.reason}",
                    retry_count=attempt
                )

            except (ConnectionError, TimeoutError) as e:
                self._circuit_breaker.record_failure()
                last_error = e
                logger.warning(f"Connection error for {self.platform_name}: {e}")

                if attempt < max_retries:
                    wait_time = min(delay * (2 ** (attempt - 1)), max_delay)
                    logger.info(f"Retrying in {wait_time:.1f}s...")
                    await asyncio.sleep(wait_time)

            except Exception as e:
                last_error = e
                logger.error(f"Unexpected error uploading to {self.platform_name}: {e}")

                if attempt < max_retries:
                    wait_time = min(delay * (2 ** (attempt - 1)), max_delay)
                    await asyncio.sleep(wait_time)

        # 모든 재시도 실패
        error_msg = f"Upload failed after {max_retries} attempts: {last_error}"
        self.log_upload_result(False)

        # 에러 콜백
        if self._on_upload_error:
            self._on_upload_error(self.platform_name, last_error)

        return UploadResult(
            status=UploadStatus.FAILED,
            platform=self.platform_name,
            error_message=error_msg,
            retry_count=max_retries
        )

    async def get_analytics(self, content_id: str) -> dict:
        """콘텐츠 분석 데이터를 가져옵니다."""
        try:
            return await self._get_analytics_impl(content_id)
        except Exception as e:
            logger.error(f"Error getting analytics for {content_id}: {e}")
            return {}

    # ===== 유틸리티 메서드 =====

    def get_default_tags(self) -> List[str]:
        """기본 태그 목록을 반환합니다."""
        return self.config.get("tags", {}).get("default", [])

    def get_hashtags(self) -> List[str]:
        """기본 해시태그 목록을 반환합니다."""
        return self.config.get("hashtags", {}).get("default", [])

    def format_caption(self, content: MemeContent) -> str:
        """캡션을 플랫폼에 맞게 포맷팅합니다."""
        max_length = self.config.get("caption_max_length", 2200)
        caption = content.meme_text or ""

        # 해시태그 추가
        hashtags = self.get_hashtags()
        if hashtags:
            hashtag_str = " ".join(hashtags)
            if len(caption) + len(hashtag_str) + 2 <= max_length:
                caption = f"{caption}\n\n{hashtag_str}"

        return caption[:max_length]

    async def validate_content(self, content: MemeContent) -> bool:
        """업로드 전 콘텐츠를 검증합니다."""
        if not content.video_path and not content.image_path:
            logger.error("No media content to upload")
            return False
        return True

    def log_upload_result(self, success: bool, url: Optional[str] = None):
        """업로드 결과를 로깅합니다."""
        if success:
            logger.info(f"Successfully uploaded to {self.platform_name}: {url}")
        else:
            logger.error(f"Failed to upload to {self.platform_name}")

    def reset_circuit_breaker(self):
        """Circuit Breaker를 리셋합니다."""
        self._circuit_breaker._failure_count = 0
        self._circuit_breaker._state = "closed"
        logger.info(f"Circuit breaker reset for {self.platform_name}")


class UploadManager:
    """여러 플랫폼에 대한 업로드를 관리합니다."""

    def __init__(self, config_loader):
        self.config_loader = config_loader
        self.platforms: Dict[str, BasePlatform] = {}
        self._results: List[UploadResult] = []

    def register_platform(self, platform: BasePlatform) -> None:
        """플랫폼을 등록합니다."""
        self.platforms[platform.platform_name] = platform

    async def upload_to_all(
        self,
        content: MemeContent,
        platforms: List[str] = None,
        parallel: bool = True
    ) -> List[UploadResult]:
        """
        모든 활성화된 플랫폼에 업로드합니다.

        Args:
            content: MemeContent 객체
            platforms: 업로드할 플랫폼 목록 (None이면 활성화된 모든 플랫폼)
            parallel: True면 병렬 업로드

        Returns:
            UploadResult 목록
        """
        # 업로드할 플랫폼 결정
        target_platforms = []
        for name, platform in self.platforms.items():
            if platforms and name not in platforms:
                continue
            if platform.is_enabled:
                target_platforms.append(platform)

        if not target_platforms:
            logger.warning("No enabled platforms to upload to")
            return []

        logger.info(f"Uploading to {len(target_platforms)} platforms")

        if parallel:
            # 병렬 업로드
            tasks = [
                platform.upload(content)
                for platform in target_platforms
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 예외를 UploadResult로 변환
            final_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    final_results.append(UploadResult(
                        status=UploadStatus.FAILED,
                        platform=target_platforms[i].platform_name,
                        error_message=str(result)
                    ))
                else:
                    final_results.append(result)

            self._results = final_results
            return final_results

        else:
            # 순차 업로드
            results = []
            for platform in target_platforms:
                try:
                    result = await platform.upload(content)
                    results.append(result)
                except Exception as e:
                    results.append(UploadResult(
                        status=UploadStatus.FAILED,
                        platform=platform.platform_name,
                        error_message=str(e)
                    ))

            self._results = results
            return results

    def get_success_count(self) -> int:
        """성공한 업로드 수를 반환합니다."""
        return sum(1 for r in self._results if r.status == UploadStatus.SUCCESS)

    def get_failed_count(self) -> int:
        """실패한 업로드 수를 반환합니다."""
        return sum(1 for r in self._results if r.status == UploadStatus.FAILED)

    def get_results_summary(self) -> dict:
        """업로드 결과 요약을 반환합니다."""
        return {
            "total": len(self._results),
            "success": self.get_success_count(),
            "failed": self.get_failed_count(),
            "results": [r.to_dict() for r in self._results]
        }
