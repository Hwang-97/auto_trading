"""
이미지 생성 모듈

밈 이미지와 썸네일을 생성합니다.
세로 형식 (1080x1920) 이미지와 그라데이션 배경을 지원합니다.
"""

import os
import random
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple, TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from ..utils.logger import get_logger

if TYPE_CHECKING:
    from ..core.pipeline import MemeContent

logger = get_logger(__name__)

# 그라데이션 색상 프리셋
GRADIENT_PRESETS = {
    "sunset": [(255, 94, 98), (255, 195, 113)],
    "ocean": [(0, 180, 216), (0, 119, 182)],
    "purple": [(131, 58, 180), (253, 29, 29)],
    "mint": [(11, 232, 129), (88, 167, 255)],
    "fire": [(245, 0, 87), (255, 193, 7)],
    "night": [(30, 60, 114), (42, 82, 152)],
    "pink": [(255, 175, 189), (255, 195, 160)],
    "cool": [(74, 194, 154), (189, 151, 243)],
}


class ImageGenerator:
    """밈 이미지 및 썸네일을 생성하는 클래스"""

    # 숏폼 비디오용 이미지 크기 (9:16 비율)
    SHORTS_WIDTH = 1080
    SHORTS_HEIGHT = 1920

    # 썸네일 크기
    THUMBNAIL_WIDTH = 1280
    THUMBNAIL_HEIGHT = 720

    def __init__(self, config_loader):
        """
        ImageGenerator를 초기화합니다.

        Args:
            config_loader: ConfigLoader 인스턴스
        """
        self.config_loader = config_loader
        self.config = config_loader.load("config")
        self.platforms_config = config_loader.load("platforms")

        paths = self.config.get("paths", {})
        self.output_dir = Path(paths.get("output_dir", "output"))
        self.templates_dir = Path(paths.get("templates_dir", "templates/meme_templates"))
        self.fonts_dir = Path(paths.get("fonts_dir", "assets/fonts"))

        # 기본 폰트 경로
        self.font_paths = [
            "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]

    async def generate(self, content: "MemeContent") -> Optional[str]:
        """
        밈 이미지를 생성합니다 (1080x1920, 그라데이션 배경).

        Args:
            content: MemeContent 객체

        Returns:
            생성된 이미지 경로 또는 None
        """
        try:
            width, height = self.SHORTS_WIDTH, self.SHORTS_HEIGHT

            # 1. 그라데이션 배경 생성
            image = self._create_gradient_background(width, height)
            draw = ImageDraw.Draw(image)

            # 2. 상단 텍스트 추가
            top_text = content.top_text or ""
            if top_text:
                self._add_meme_text(
                    draw, top_text, width,
                    y_position=int(height * 0.15),
                    font_size=72,
                    max_width=width - 80
                )

            # 3. 하단 텍스트 추가
            bottom_text = content.bottom_text or ""
            if bottom_text:
                self._add_meme_text(
                    draw, bottom_text, width,
                    y_position=int(height * 0.75),
                    font_size=72,
                    max_width=width - 80
                )

            # 4. 채널 워터마크 추가 (선택)
            if content.channel_name:
                self._add_watermark(draw, content.channel_name, width, height)

            # 5. 저장
            output_path = self._get_output_path(content.channel_name, "meme")
            image.save(output_path, quality=95)
            logger.info(f"Meme image saved: {output_path}")

            return str(output_path)

        except Exception as e:
            logger.error(f"Error generating meme image: {e}")
            return None

    async def generate_thumbnail(self, content: "MemeContent") -> Optional[str]:
        """
        YouTube 썸네일을 생성합니다 (1280x720).

        Args:
            content: MemeContent 객체

        Returns:
            생성된 썸네일 경로 또는 None
        """
        try:
            width, height = self.THUMBNAIL_WIDTH, self.THUMBNAIL_HEIGHT

            # 그라데이션 배경
            image = self._create_gradient_background(width, height, preset="fire")
            draw = ImageDraw.Draw(image)

            # 제목 텍스트
            title = content.top_text or ""
            if not title and content.news_items:
                title = content.news_items[0].title[:30]
            if not title:
                title = "오늘의 밈"

            # 큰 텍스트로 추가
            self._add_meme_text(
                draw, title, width,
                y_position=height // 2 - 40,
                font_size=80,
                max_width=width - 100
            )

            # 저장
            output_path = self._get_output_path(content.channel_name, "thumbnail")
            image.save(output_path, quality=95)
            logger.info(f"Thumbnail saved: {output_path}")

            return str(output_path)

        except Exception as e:
            logger.error(f"Error generating thumbnail: {e}")
            return None

    def _create_gradient_background(
        self,
        width: int,
        height: int,
        preset: Optional[str] = None,
        colors: Optional[List[Tuple[int, int, int]]] = None
    ) -> Image.Image:
        """
        그라데이션 배경 이미지를 생성합니다.

        Args:
            width: 이미지 너비
            height: 이미지 높이
            preset: 프리셋 이름
            colors: 커스텀 색상 리스트

        Returns:
            그라데이션 이미지
        """
        # 색상 선택
        if colors:
            gradient_colors = colors
        elif preset and preset in GRADIENT_PRESETS:
            gradient_colors = GRADIENT_PRESETS[preset]
        else:
            # 랜덤 프리셋 선택
            preset_name = random.choice(list(GRADIENT_PRESETS.keys()))
            gradient_colors = GRADIENT_PRESETS[preset_name]

        # 그라데이션 이미지 생성
        image = Image.new("RGB", (width, height))

        color1 = gradient_colors[0]
        color2 = gradient_colors[1] if len(gradient_colors) > 1 else gradient_colors[0]

        for y in range(height):
            # 선형 보간
            ratio = y / height
            r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
            g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
            b = int(color1[2] * (1 - ratio) + color2[2] * ratio)

            for x in range(width):
                image.putpixel((x, y), (r, g, b))

        return image

    def _get_font(self, size: int) -> ImageFont.FreeTypeFont:
        """
        사용 가능한 폰트를 로드합니다.

        Args:
            size: 폰트 크기

        Returns:
            폰트 객체
        """
        # 커스텀 폰트 경로 확인
        for font_path in self.font_paths:
            if os.path.exists(font_path):
                try:
                    return ImageFont.truetype(font_path, size)
                except OSError:
                    continue

        # assets/fonts 디렉토리 확인
        if self.fonts_dir.exists():
            for font_file in self.fonts_dir.glob("*.ttf"):
                try:
                    return ImageFont.truetype(str(font_file), size)
                except OSError:
                    continue

        # 기본 폰트 사용
        logger.warning("Using default font - Korean text may not render correctly")
        return ImageFont.load_default()

    def _add_meme_text(
        self,
        draw: ImageDraw.Draw,
        text: str,
        width: int,
        y_position: int,
        font_size: int = 64,
        max_width: int = 1000,
        text_color: str = "white",
        stroke_color: str = "black",
        stroke_width: int = 4
    ) -> None:
        """
        밈 스타일의 텍스트를 추가합니다.

        Args:
            draw: ImageDraw 객체
            text: 추가할 텍스트
            width: 이미지 너비
            y_position: Y 시작 위치
            font_size: 폰트 크기
            max_width: 최대 텍스트 너비
            text_color: 텍스트 색상
            stroke_color: 테두리 색상
            stroke_width: 테두리 두께
        """
        font = self._get_font(font_size)

        # 텍스트 줄바꿈
        lines = self._wrap_text(text, font, max_width)

        # 줄 높이 계산
        line_height = font_size + 15

        # 각 줄 그리기
        current_y = y_position
        for line in lines:
            # 텍스트 너비 계산
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2

            # 테두리 효과 (여러 방향으로 그리기)
            for dx in range(-stroke_width, stroke_width + 1):
                for dy in range(-stroke_width, stroke_width + 1):
                    if dx != 0 or dy != 0:
                        draw.text((x + dx, current_y + dy), line, font=font, fill=stroke_color)

            # 메인 텍스트
            draw.text((x, current_y), line, font=font, fill=text_color)

            current_y += line_height

    def _add_watermark(
        self,
        draw: ImageDraw.Draw,
        channel_name: str,
        width: int,
        height: int
    ) -> None:
        """
        채널 워터마크를 추가합니다.

        Args:
            draw: ImageDraw 객체
            channel_name: 채널 이름
            width: 이미지 너비
            height: 이미지 높이
        """
        font = self._get_font(28)

        # 채널 이름 가져오기
        channel_config = self.config_loader.get_channel(channel_name)
        display_name = channel_name
        if channel_config:
            display_name = channel_config.get("name", channel_name)

        text = f"@{display_name}"

        # 우하단에 배치
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        x = width - text_width - 30
        y = height - 60

        # 반투명 효과를 위해 회색으로
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 180))

    def _wrap_text(
        self,
        text: str,
        font: ImageFont.FreeTypeFont,
        max_width: int
    ) -> List[str]:
        """
        텍스트를 지정된 너비에 맞게 줄바꿈합니다.

        Args:
            text: 원본 텍스트
            font: 폰트 객체
            max_width: 최대 너비

        Returns:
            줄바꿈된 텍스트 리스트
        """
        # 한글은 글자 단위로 분리
        words = list(text)
        lines = []
        current_line = ""

        for char in words:
            test_line = current_line + char
            try:
                bbox = font.getbbox(test_line)
                text_width = bbox[2] - bbox[0]
            except AttributeError:
                text_width = len(test_line) * 30

            if text_width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = char

        if current_line:
            lines.append(current_line)

        return lines if lines else [text]

    def _get_output_path(self, channel_name: str, prefix: str) -> Path:
        """
        출력 파일 경로를 생성합니다.

        Args:
            channel_name: 채널 이름
            prefix: 파일 접두사

        Returns:
            출력 파일 경로
        """
        today = datetime.now().strftime("%Y%m%d")
        timestamp = datetime.now().strftime("%H%M%S")

        if channel_name:
            output_path = self.config_loader.get_output_path(channel_name)
        else:
            output_path = self.output_dir / "daily"

        daily_dir = output_path / today
        daily_dir.mkdir(parents=True, exist_ok=True)

        return daily_dir / f"{prefix}_{timestamp}.png"

    async def load_template(self, template_name: str) -> Optional[Image.Image]:
        """템플릿 이미지를 로드합니다."""
        template_path = self.templates_dir / f"{template_name}.png"
        if template_path.exists():
            return Image.open(template_path)
        return None
