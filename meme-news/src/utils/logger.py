"""
로깅 유틸리티 모듈
"""

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


_loggers = {}


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    max_size_mb: int = 10,
    backup_count: int = 5,
) -> logging.Logger:
    """로깅을 설정합니다."""
    # 로그 레벨 매핑
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    log_level = level_map.get(level.upper(), logging.INFO)

    # 루트 로거 설정
    root_logger = logging.getLogger("memenews")
    root_logger.setLevel(log_level)

    # 기존 핸들러 제거
    root_logger.handlers.clear()

    # 포맷터
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 파일 핸들러
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_size_mb * 1024 * 1024,
            backupCount=backup_count,
            encoding="utf-8"
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """명명된 로거를 반환합니다."""
    if name in _loggers:
        return _loggers[name]

    # 기본 memenews 로거의 자식 로거 생성
    logger = logging.getLogger(f"memenews.{name}")

    # 부모 로거가 설정되어 있지 않으면 기본 설정
    parent = logging.getLogger("memenews")
    if not parent.handlers:
        setup_logging()

    _loggers[name] = logger
    return logger


class LogContext:
    """로그 컨텍스트 관리자"""

    def __init__(self, logger: logging.Logger, operation: str):
        self.logger = logger
        self.operation = operation
        self.start_time = None

    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.info(f"Starting: {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = (datetime.now() - self.start_time).total_seconds()

        if exc_type is not None:
            self.logger.error(
                f"Failed: {self.operation} (took {elapsed:.2f}s) - {exc_val}"
            )
            return False

        self.logger.info(f"Completed: {self.operation} (took {elapsed:.2f}s)")
        return True


def log_function_call(func):
    """함수 호출을 로깅하는 데코레이터"""
    logger = get_logger(func.__module__)

    async def async_wrapper(*args, **kwargs):
        logger.debug(f"Calling {func.__name__}")
        try:
            result = await func(*args, **kwargs)
            logger.debug(f"Completed {func.__name__}")
            return result
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            raise

    def sync_wrapper(*args, **kwargs):
        logger.debug(f"Calling {func.__name__}")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"Completed {func.__name__}")
            return result
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            raise

    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper
