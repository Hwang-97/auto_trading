"""
Image Generator Tests
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.meme.image_gen import ImageGenerator, GRADIENT_PRESETS
from src.core.pipeline import MemeContent, ContentType


class TestImageGenerator:
    """ImageGenerator 테스트"""

    @pytest.fixture
    def image_generator(self, mock_config_loader, temp_dir):
        """ImageGenerator 인스턴스 생성"""
        mock_config_loader.load.return_value = {
            "paths": {"output_dir": str(temp_dir)}
        }
        return ImageGenerator(mock_config_loader)

    @pytest.fixture
    def sample_content(self):
        """테스트용 MemeContent"""
        return MemeContent(
            channel_name="test_channel",
            content_type=ContentType.DAILY,
            meme_text="테스트 밈",
            top_text="상황이 이러면",
            bottom_text="어쩔 수 없지",
            narration="테스트 나레이션"
        )

    def test_gradient_presets_exist(self):
        """그라데이션 프리셋 존재 확인"""
        assert len(GRADIENT_PRESETS) > 0
        assert "sunset" in GRADIENT_PRESETS
        assert "ocean" in GRADIENT_PRESETS

    def test_gradient_preset_format(self):
        """그라데이션 프리셋 형식 확인"""
        for name, colors in GRADIENT_PRESETS.items():
            assert len(colors) == 2, f"{name} should have 2 colors"
            for color in colors:
                assert len(color) == 3, f"{name} color should be RGB tuple"
                for value in color:
                    assert 0 <= value <= 255

    def test_image_dimensions(self, image_generator):
        """이미지 크기 확인"""
        assert image_generator.SHORTS_WIDTH == 1080
        assert image_generator.SHORTS_HEIGHT == 1920

    def test_thumbnail_dimensions(self, image_generator):
        """썸네일 크기 확인"""
        assert image_generator.THUMBNAIL_WIDTH == 1280
        assert image_generator.THUMBNAIL_HEIGHT == 720

    @pytest.mark.asyncio
    async def test_generate_creates_image(self, image_generator, sample_content, temp_dir):
        """이미지 생성 테스트"""
        # 출력 디렉토리 설정
        image_generator.output_dir = temp_dir

        output_path = await image_generator.generate(sample_content)

        assert output_path is not None
        assert Path(output_path).exists()
        assert Path(output_path).suffix == ".png"

    @pytest.mark.asyncio
    async def test_generate_with_different_presets(self, image_generator, sample_content, temp_dir):
        """다양한 프리셋으로 이미지 생성 테스트"""
        image_generator.output_dir = temp_dir

        for preset in ["sunset", "ocean", "purple"]:
            output_path = await image_generator.generate(sample_content)
            assert output_path is not None
            assert Path(output_path).exists()

    @pytest.mark.asyncio
    async def test_generate_without_text(self, image_generator, temp_dir):
        """텍스트 없이 이미지 생성 테스트"""
        image_generator.output_dir = temp_dir

        content = MemeContent(
            channel_name="test",
            content_type=ContentType.DAILY,
            meme_text="",
            top_text="",
            bottom_text=""
        )

        output_path = await image_generator.generate(content)
        assert output_path is not None


class TestImageQuality:
    """이미지 품질 테스트"""

    @pytest.fixture
    def image_generator(self, mock_config_loader, temp_dir):
        mock_config_loader.load.return_value = {
            "paths": {"output_dir": str(temp_dir)}
        }
        return ImageGenerator(mock_config_loader)

    @pytest.mark.asyncio
    async def test_image_file_size(self, image_generator, temp_dir):
        """생성된 이미지 파일 크기 확인"""
        image_generator.output_dir = temp_dir

        content = MemeContent(
            channel_name="test",
            content_type=ContentType.DAILY,
            top_text="테스트",
            bottom_text="밈"
        )

        output_path = await image_generator.generate(content)
        file_size = Path(output_path).stat().st_size

        # PNG 파일은 일반적으로 1KB 이상
        assert file_size > 1024, "Image file too small"
        # 10MB 미만이어야 함
        assert file_size < 10 * 1024 * 1024, "Image file too large"

    @pytest.mark.asyncio
    async def test_image_dimensions_correct(self, image_generator, temp_dir):
        """생성된 이미지 크기가 올바른지 확인"""
        from PIL import Image

        image_generator.output_dir = temp_dir

        content = MemeContent(
            channel_name="test",
            content_type=ContentType.DAILY,
            top_text="테스트"
        )

        output_path = await image_generator.generate(content)

        with Image.open(output_path) as img:
            assert img.width == 1080
            assert img.height == 1920
