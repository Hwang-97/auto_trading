"""
Config Loader Tests
"""

import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config_loader import ConfigLoader


class TestConfigLoader:
    """ConfigLoader 테스트"""

    @pytest.fixture
    def config_loader(self):
        """ConfigLoader 인스턴스 생성"""
        return ConfigLoader("config")

    def test_load_channels(self, config_loader):
        """채널 설정 로드 테스트"""
        channels = config_loader.get_all_channels()

        assert channels is not None
        assert len(channels) > 0
        assert "daily_meme" in channels

    def test_get_channel(self, config_loader):
        """개별 채널 조회 테스트"""
        channel = config_loader.get_channel("daily_meme")

        assert channel is not None
        assert "name" in channel
        assert "category" in channel
        assert "platforms" in channel

    def test_get_channel_not_found(self, config_loader):
        """존재하지 않는 채널 조회 테스트"""
        channel = config_loader.get_channel("nonexistent_channel")
        assert channel is None

    def test_load_sources(self, config_loader):
        """소스 설정 로드 테스트"""
        source = config_loader.get_source("daily")

        assert source is not None
        assert "type" in source

    def test_load_platforms(self, config_loader):
        """플랫폼 설정 로드 테스트"""
        platform = config_loader.get_platform("youtube")

        assert platform is not None
        assert "video" in platform
        assert "resolution" in platform["video"]

    def test_load_prompts(self, config_loader):
        """프롬프트 설정 로드 테스트"""
        prompt = config_loader.get_prompt("daily_meme_prompt")

        assert prompt is not None
        assert "system" in prompt

    def test_get_output_path(self, config_loader):
        """출력 경로 조회 테스트"""
        path = config_loader.get_output_path("images")

        assert path is not None
        assert isinstance(path, Path)

    def test_get_database_path(self, config_loader):
        """데이터베이스 경로 조회 테스트"""
        path = config_loader.get_database_path()

        assert path is not None
        assert "db" in path

    def test_get_keyword_filters(self, config_loader):
        """키워드 필터 조회 테스트"""
        filters = config_loader.get_keyword_filters("it")

        assert filters is not None
        assert "include" in filters
        assert "exclude" in filters

    def test_env_variable_fallback(self, config_loader):
        """환경 변수 폴백 테스트"""
        # API 키가 없어도 None 반환
        api_key = config_loader.get_api_key("gemini")
        # 환경 변수가 설정되지 않았으면 None
        assert api_key is None or isinstance(api_key, str)


class TestConfigValidation:
    """설정 유효성 검사 테스트"""

    @pytest.fixture
    def config_loader(self):
        return ConfigLoader("config")

    def test_channel_has_required_fields(self, config_loader):
        """채널이 필수 필드를 가지고 있는지 테스트"""
        required_fields = ["name", "category", "platforms", "schedule"]

        for channel_name, channel in config_loader.get_all_channels().items():
            for field in required_fields:
                assert field in channel, f"{channel_name} missing {field}"

    def test_platform_video_config(self, config_loader):
        """플랫폼 비디오 설정 테스트"""
        for platform_name in ["youtube", "tiktok", "instagram"]:
            platform = config_loader.get_platform(platform_name)
            assert platform is not None
            assert "video" in platform
            assert "resolution" in platform["video"]

    def test_source_types_valid(self, config_loader):
        """소스 타입이 유효한지 테스트"""
        valid_types = ["ai_generated", "realtime_trend", "rss_feed"]

        for category in ["daily", "trend", "it", "stock"]:
            source = config_loader.get_source(category)
            if source:
                assert source.get("type") in valid_types
