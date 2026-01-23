"""
Pytest Configuration and Fixtures
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, AsyncMock

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_config_loader():
    """Mock ConfigLoader for testing."""
    mock = MagicMock()

    # Mock channel config
    mock.get_channel.return_value = {
        "name": "테스트밈",
        "category": "daily",
        "enabled": True,
        "platforms": ["youtube"],
        "schedule": {"count": 1, "times": ["09:00"]},
        "content": {"style": "mz_humor", "max_length": 15}
    }

    mock.get_all_channels.return_value = {
        "test_channel": mock.get_channel.return_value
    }

    # Mock source config
    mock.get_source.return_value = {
        "type": "ai_generated",
        "topics": [{"name": "테스트", "keywords": ["테스트"], "weight": 1.0}]
    }

    # Mock platform config
    mock.get_platform.return_value = {
        "video": {"resolution": "1080x1920", "duration": {"min": 15, "max": 30}},
        "hashtags": {"max": 10, "required": ["#Shorts"]}
    }

    # Mock prompt config
    mock.get_prompt.return_value = {
        "system": "테스트 시스템 프롬프트",
        "user_template": "주제: {topic}",
        "examples": []
    }

    # Mock paths
    mock.get_output_path.return_value = Path("output/test")
    mock.get_database_path.return_value = "data/test.db"
    mock.load.return_value = {"paths": {"output_dir": "output"}}

    return mock


@pytest.fixture
def sample_meme_content():
    """Sample MemeContent for testing."""
    from src.core.pipeline import MemeContent, ContentType

    return MemeContent(
        channel_name="test_channel",
        content_type=ContentType.DAILY,
        meme_text="테스트 밈 텍스트",
        top_text="상황이 이러면",
        bottom_text="어쩔 수 없지",
        narration="테스트 나레이션입니다.",
        hashtags=["#테스트", "#밈", "#Shorts"]
    )


@pytest.fixture
def sample_news_item():
    """Sample NewsItem for testing."""
    from src.core.pipeline import NewsItem
    from datetime import datetime

    return NewsItem(
        title="테스트 뉴스 제목",
        content="테스트 뉴스 본문입니다. 이것은 테스트를 위한 내용입니다.",
        source="테스트소스",
        url="https://example.com/news/1",
        published_at=datetime.now(),
        category="test"
    )


@pytest.fixture
def mock_gemini_response():
    """Mock Gemini API response."""
    return {
        "top_text": "월요일 아침",
        "bottom_text": "출근하기 싫다",
        "narration": "월요일 아침, 알람 소리에 눈을 뜨는 순간의 절망감.",
        "hashtags": ["#월요병", "#직장인", "#출근", "#공감", "#Shorts"]
    }


@pytest.fixture
def mock_async_response():
    """Mock async HTTP response."""
    mock = AsyncMock()
    mock.status = 200
    mock.text = AsyncMock(return_value="<xml>test</xml>")
    mock.json = AsyncMock(return_value={"data": "test"})
    return mock
