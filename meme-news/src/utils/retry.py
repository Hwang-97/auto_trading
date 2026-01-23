"""
Retry Utility with Exponential Backoff

API 호출 재시도 로직
"""

import asyncio
import functools
import random
from typing import Callable, Tuple, Type, Union

from .logger import get_logger

logger = get_logger(__name__)


class RetryError(Exception):
    """재시도 실패 예외"""

    def __init__(self, message: str, last_exception: Exception = None):
        super().__init__(message)
        self.last_exception = last_exception


def retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Callable = None
):
    """
    동기 함수용 재시도 데코레이터

    Args:
        max_attempts: 최대 시도 횟수
        initial_delay: 초기 대기 시간 (초)
        max_delay: 최대 대기 시간 (초)
        exponential_base: 지수 배수
        jitter: 지터 추가 여부 (thundering herd 방지)
        exceptions: 재시도할 예외 타입들
        on_retry: 재시도 시 호출할 콜백 함수
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise RetryError(
                            f"Failed after {max_attempts} attempts",
                            last_exception
                        )

                    # 대기 시간 계산
                    delay = min(
                        initial_delay * (exponential_base ** (attempt - 1)),
                        max_delay
                    )

                    # 지터 추가
                    if jitter:
                        delay = delay * (0.5 + random.random())

                    logger.warning(
                        f"{func.__name__} attempt {attempt} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )

                    if on_retry:
                        on_retry(attempt, e, delay)

                    import time
                    time.sleep(delay)

            raise RetryError(
                f"Failed after {max_attempts} attempts",
                last_exception
            )

        return wrapper
    return decorator


def async_retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Callable = None
):
    """
    비동기 함수용 재시도 데코레이터

    Args:
        max_attempts: 최대 시도 횟수
        initial_delay: 초기 대기 시간 (초)
        max_delay: 최대 대기 시간 (초)
        exponential_base: 지수 배수
        jitter: 지터 추가 여부
        exceptions: 재시도할 예외 타입들
        on_retry: 재시도 시 호출할 콜백 함수
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise RetryError(
                            f"Failed after {max_attempts} attempts",
                            last_exception
                        )

                    # 대기 시간 계산
                    delay = min(
                        initial_delay * (exponential_base ** (attempt - 1)),
                        max_delay
                    )

                    # 지터 추가
                    if jitter:
                        delay = delay * (0.5 + random.random())

                    logger.warning(
                        f"{func.__name__} attempt {attempt} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )

                    if on_retry:
                        if asyncio.iscoroutinefunction(on_retry):
                            await on_retry(attempt, e, delay)
                        else:
                            on_retry(attempt, e, delay)

                    await asyncio.sleep(delay)

            raise RetryError(
                f"Failed after {max_attempts} attempts",
                last_exception
            )

        return wrapper
    return decorator


class CircuitBreaker:
    """
    Circuit Breaker 패턴 구현

    외부 서비스 장애 시 빠른 실패로 시스템 보호
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    ):
        """
        Args:
            failure_threshold: 회로 차단 전 허용 실패 횟수
            recovery_timeout: 회로 복구 대기 시간 (초)
            expected_exceptions: 실패로 카운트할 예외 타입들
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exceptions = expected_exceptions

        self._failure_count = 0
        self._last_failure_time = None
        self._state = "closed"  # closed, open, half-open

    @property
    def state(self) -> str:
        """현재 상태 반환"""
        if self._state == "open":
            # 복구 시간이 지났으면 half-open으로 전환
            import time
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = "half-open"

        return self._state

    def record_failure(self):
        """실패 기록"""
        import time
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._failure_count >= self.failure_threshold:
            self._state = "open"
            logger.warning(
                f"Circuit breaker opened after {self._failure_count} failures"
            )

    def record_success(self):
        """성공 기록"""
        self._failure_count = 0
        self._state = "closed"

    def can_execute(self) -> bool:
        """실행 가능 여부"""
        state = self.state
        if state == "closed":
            return True
        elif state == "half-open":
            return True  # 테스트 요청 허용
        else:  # open
            return False

    def __call__(self, func):
        """데코레이터로 사용"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not self.can_execute():
                raise RetryError(
                    "Circuit breaker is open",
                    None
                )

            try:
                result = func(*args, **kwargs)
                self.record_success()
                return result
            except self.expected_exceptions as e:
                self.record_failure()
                raise

        return wrapper


class AsyncCircuitBreaker(CircuitBreaker):
    """비동기 Circuit Breaker"""

    def __call__(self, func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if not self.can_execute():
                raise RetryError(
                    "Circuit breaker is open",
                    None
                )

            try:
                result = await func(*args, **kwargs)
                self.record_success()
                return result
            except self.expected_exceptions as e:
                self.record_failure()
                raise

        return wrapper


# 사전 정의된 재시도 설정
api_retry = async_retry(
    max_attempts=3,
    initial_delay=2.0,
    max_delay=30.0,
    exceptions=(ConnectionError, TimeoutError, Exception)
)

upload_retry = async_retry(
    max_attempts=5,
    initial_delay=5.0,
    max_delay=120.0,
    exceptions=(ConnectionError, TimeoutError, Exception)
)

crawl_retry = async_retry(
    max_attempts=3,
    initial_delay=1.0,
    max_delay=10.0,
    exceptions=(ConnectionError, TimeoutError, Exception)
)
