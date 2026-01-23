"""
비디오 생성 모듈

FFmpeg와 gTTS를 사용하여 숏폼 비디오를 생성합니다.
15-30초 길이의 세로 형식 (1080x1920) 비디오를 지원합니다.
"""

import asyncio
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

from gtts import gTTS

from ..utils.logger import get_logger

if TYPE_CHECKING:
    from ..core.pipeline import MemeContent

logger = get_logger(__name__)


class VideoGenerator:
    """밈 비디오를 생성하는 클래스"""

    # 숏폼 비디오 스펙
    WIDTH = 1080
    HEIGHT = 1920
    FPS = 30
    MIN_DURATION = 15  # 최소 15초
    MAX_DURATION = 30  # 최대 30초

    def __init__(self, config_loader):
        """
        VideoGenerator를 초기화합니다.

        Args:
            config_loader: ConfigLoader 인스턴스
        """
        self.config_loader = config_loader
        self.config = config_loader.load("config")
        self.platforms_config = config_loader.load("platforms")

        paths = self.config.get("paths", {})
        self.output_dir = Path(paths.get("output_dir", "output"))
        self.temp_dir = Path(paths.get("temp_dir", "temp"))
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    async def generate(self, content: "MemeContent") -> Optional[str]:
        """
        밈 비디오를 생성합니다.

        Args:
            content: MemeContent 객체

        Returns:
            생성된 비디오 경로 또는 None
        """
        try:
            # 나레이션 텍스트 결정
            narration_text = self._get_narration_text(content)
            if not narration_text:
                logger.warning("No narration text available for video")
                # 기본 텍스트 사용
                narration_text = content.top_text or "오늘의 밈입니다"

            # 1. TTS 오디오 생성
            audio_path = await self._generate_tts(narration_text)
            if not audio_path:
                logger.error("Failed to generate TTS audio")
                return None

            # 2. 오디오 길이 확인
            audio_duration = await self._get_audio_duration(audio_path)
            target_duration = max(self.MIN_DURATION, min(audio_duration + 2, self.MAX_DURATION))

            # 3. 이미지 준비
            image_path = content.image_path
            if not image_path or not os.path.exists(image_path):
                # 이미지가 없으면 생성
                from .image_gen import ImageGenerator
                image_gen = ImageGenerator(self.config_loader)
                image_path = await image_gen.generate(content)

            if not image_path:
                logger.error("No image available for video")
                return None

            # 4. FFmpeg로 비디오 생성
            output_path = await self._compose_video(
                image_path=image_path,
                audio_path=audio_path,
                duration=target_duration,
                channel_name=content.channel_name
            )

            return output_path

        except Exception as e:
            logger.error(f"Error generating video: {e}")
            return None

    def _get_narration_text(self, content: "MemeContent") -> str:
        """
        비디오에 사용할 나레이션 텍스트를 결정합니다.

        Args:
            content: MemeContent 객체

        Returns:
            나레이션 텍스트
        """
        # 우선순위: narration > script > meme_text
        if content.narration:
            return content.narration

        if content.script:
            # 스크립트에서 나레이션 부분만 추출
            return self._extract_narration_from_script(content.script)

        # top_text와 bottom_text 결합
        parts = []
        if content.top_text:
            parts.append(content.top_text)
        if content.bottom_text:
            parts.append(content.bottom_text)

        return " ".join(parts) if parts else content.meme_text

    def _extract_narration_from_script(self, script: str) -> str:
        """
        스크립트에서 나레이션 텍스트를 추출합니다.

        Args:
            script: 전체 스크립트

        Returns:
            추출된 나레이션
        """
        # 타임코드 제거
        text = re.sub(r'\[\d+-?\d*초?\]', '', script)
        # 레이블 제거
        text = re.sub(r'(후킹|본문|엔딩|나레이션):\s*', '', text)
        # 특수문자 정리
        text = re.sub(r'[-*#]', '', text)
        # 연속 공백 제거
        text = re.sub(r'\s+', ' ', text)

        return text.strip()[:500]  # 최대 500자

    async def _generate_tts(self, text: str) -> Optional[str]:
        """
        TTS를 사용하여 오디오를 생성합니다.

        Args:
            text: 변환할 텍스트

        Returns:
            생성된 오디오 파일 경로 또는 None
        """
        try:
            # 텍스트 정리
            clean_text = self._clean_text_for_tts(text)
            if not clean_text:
                return None

            # gTTS로 음성 생성
            tts = gTTS(text=clean_text, lang="ko", slow=False)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            audio_path = self.temp_dir / f"tts_{timestamp}.mp3"
            tts.save(str(audio_path))

            logger.info(f"TTS audio generated: {audio_path}")
            return str(audio_path)

        except Exception as e:
            logger.error(f"Error generating TTS: {e}")
            return None

    def _clean_text_for_tts(self, text: str) -> str:
        """
        TTS용 텍스트를 정리합니다.

        Args:
            text: 원본 텍스트

        Returns:
            정리된 텍스트
        """
        # 이모지 및 특수문자 제거 (한글, 영문, 숫자, 기본 문장부호만 유지)
        clean = re.sub(r'[^\w\s가-힣a-zA-Z0-9.,!?~]', '', text)
        # 연속 공백 제거
        clean = re.sub(r'\s+', ' ', clean)
        # 길이 제한
        return clean.strip()[:800]

    async def _get_audio_duration(self, audio_path: str) -> float:
        """
        오디오 파일의 길이를 가져옵니다.

        Args:
            audio_path: 오디오 파일 경로

        Returns:
            오디오 길이 (초)
        """
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return float(result.stdout.strip())
        except Exception as e:
            logger.warning(f"Could not get audio duration: {e}")

        return 10.0  # 기본값

    async def _compose_video(
        self,
        image_path: str,
        audio_path: str,
        duration: float,
        channel_name: str
    ) -> Optional[str]:
        """
        FFmpeg를 사용하여 비디오를 합성합니다.

        Args:
            image_path: 이미지 파일 경로
            audio_path: 오디오 파일 경로
            duration: 비디오 길이 (초)
            channel_name: 채널 이름

        Returns:
            생성된 비디오 파일 경로 또는 None
        """
        output_path = self._get_output_path(channel_name)

        try:
            # FFmpeg 명령 구성
            # 이미지를 루프하고 오디오를 추가
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", image_path,
                "-i", audio_path,
                "-c:v", "libx264",
                "-tune", "stillimage",
                "-c:a", "aac",
                "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                "-vf", f"scale={self.WIDTH}:{self.HEIGHT}:force_original_aspect_ratio=decrease,pad={self.WIDTH}:{self.HEIGHT}:(ow-iw)/2:(oh-ih)/2",
                "-r", str(self.FPS),
                "-t", str(duration),
                "-shortest",
                "-movflags", "+faststart",
                str(output_path)
            ]

            logger.info(f"Running FFmpeg to create video...")

            # FFmpeg 실행
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr}")
                return None

            logger.info(f"Video generated: {output_path}")
            return str(output_path)

        except subprocess.TimeoutExpired:
            logger.error("FFmpeg timed out")
            return None
        except FileNotFoundError:
            logger.error("FFmpeg not found. Please install FFmpeg.")
            return None
        except Exception as e:
            logger.error(f"Error composing video: {e}")
            return None

    def _get_output_path(self, channel_name: str) -> Path:
        """
        출력 파일 경로를 생성합니다.

        Args:
            channel_name: 채널 이름

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

        return daily_dir / f"video_{timestamp}.mp4"

    def cleanup_temp_files(self) -> None:
        """임시 파일들을 정리합니다."""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                self.temp_dir.mkdir(parents=True, exist_ok=True)
            logger.info("Temp files cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up temp files: {e}")

    async def check_ffmpeg(self) -> bool:
        """FFmpeg가 설치되어 있는지 확인합니다."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
