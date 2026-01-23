#!/usr/bin/env python3
"""
MemeNews - 뉴스/트렌드 기반 밈 콘텐츠 자동 생성 및 배포 시스템

뉴스와 트렌드를 기반으로 밈을 자동 생성하고
YouTube Shorts, TikTok, Instagram Reels에 업로드합니다.

Usage:
    python main.py --channel daily_meme  # 특정 채널 실행
    python main.py --all                  # 전체 채널 실행
    python main.py --schedule             # 스케줄러 모드
    python main.py --dry-run              # 테스트 모드 (업로드 안함)
"""

import argparse
import asyncio
import signal
import sys
from pathlib import Path
from typing import List, Optional

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from src.core.config_loader import ConfigLoader
from src.core.pipeline import Pipeline, MemeContent
from src.core.scheduler import Scheduler
from src.utils.logger import setup_logging, get_logger
from src.utils.notifier import Notifier

# 플랫폼 모듈 선택적 import (cryptography 오류 대응)
PLATFORMS_AVAILABLE = False
YouTubePlatform = None
TikTokPlatform = None
InstagramPlatform = None
PlatformOptimizer = None

def _check_cryptography():
    """cryptography 라이브러리 사용 가능 여부 확인"""
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, "-c", "from cryptography.fernet import Fernet; print('ok')"],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0 and 'ok' in result.stdout
    except Exception:
        return False

def _try_import_platforms():
    """플랫폼 모듈을 안전하게 import합니다."""
    global PLATFORMS_AVAILABLE, YouTubePlatform, TikTokPlatform, InstagramPlatform, PlatformOptimizer

    if not _check_cryptography():
        return

    try:
        from src.platforms import YouTubePlatform as YT, TikTokPlatform as TT, InstagramPlatform as IG
        from src.optimizer.platform_optimizer import PlatformOptimizer as PO

        YouTubePlatform = YT
        TikTokPlatform = TT
        InstagramPlatform = IG
        PlatformOptimizer = PO
        PLATFORMS_AVAILABLE = True
    except BaseException:
        pass

_try_import_platforms()


logger = get_logger(__name__)


class MemeNewsApp:
    """MemeNews 메인 애플리케이션"""

    def __init__(self, dry_run: bool = False):
        """
        MemeNewsApp을 초기화합니다.

        Args:
            dry_run: True면 실제 업로드 없이 테스트만 수행
        """
        self.config_loader = ConfigLoader("config")
        self.pipeline = Pipeline(self.config_loader)
        self.scheduler = Scheduler(self.config_loader)
        self.optimizer = PlatformOptimizer(self.config_loader) if PlatformOptimizer else None
        self.notifier = Notifier(self.config_loader)
        self.dry_run = dry_run

        # 플랫폼 초기화 (선택적)
        self.platforms = {}
        if PLATFORMS_AVAILABLE:
            if YouTubePlatform:
                self.platforms["youtube"] = YouTubePlatform(self.config_loader)
            if TikTokPlatform:
                self.platforms["tiktok"] = TikTokPlatform(self.config_loader)
            if InstagramPlatform:
                self.platforms["instagram"] = InstagramPlatform(self.config_loader)

        self._running = False

    async def initialize(self) -> None:
        """애플리케이션을 초기화합니다."""
        # 로깅 설정
        config = self.config_loader.load("config")
        logging_config = config.get("logging", {})

        file_config = logging_config.get("file", {})
        log_file = file_config.get("path") if file_config.get("enabled") else None

        setup_logging(
            level=logging_config.get("level", "INFO"),
            log_file=log_file,
            max_size_mb=file_config.get("max_size_mb", 10),
            backup_count=file_config.get("backup_count", 5),
        )

        # 파이프라인 초기화
        await self.pipeline.initialize()

        if self.dry_run:
            logger.info("MemeNews initialized in DRY RUN mode")
        else:
            logger.info("MemeNews initialized successfully")

    async def run_channel(self, channel_name: str) -> Optional[MemeContent]:
        """
        특정 채널에 대해 콘텐츠를 생성하고 업로드합니다.

        Args:
            channel_name: 채널 이름 (daily_meme, trend_meme, it_meme)

        Returns:
            생성된 MemeContent 또는 None
        """
        channel_config = self.config_loader.get_channel(channel_name)
        if not channel_config:
            logger.error(f"Channel not found: {channel_name}")
            return None

        channel_display_name = channel_config.get("name", channel_name)
        logger.info(f"Starting content generation for channel: {channel_display_name}")

        try:
            # 콘텐츠 생성
            content = await self.pipeline.run_channel(channel_name, dry_run=self.dry_run)

            if not content:
                logger.warning(f"No content generated for {channel_name}")
                return None

            logger.info(f"Content generated for {channel_name}")
            logger.info(f"  - Top text: {content.top_text[:50]}..." if content.top_text else "")
            logger.info(f"  - Bottom text: {content.bottom_text[:50]}..." if content.bottom_text else "")
            logger.info(f"  - Image: {content.image_path}")
            logger.info(f"  - Video: {content.video_path}")

            if self.dry_run:
                logger.info(f"[DRY RUN] Would upload to platforms: {channel_config.get('platforms', [])}")
                return content

            # 플랫폼에 업로드
            platforms = channel_config.get("platforms", [])
            await self._upload_to_platforms(content, platforms)

            # 성공 알림
            await self.notifier.notify(
                title=f"[{channel_display_name}] 콘텐츠 생성 완료",
                message=f"밈이 성공적으로 생성되었습니다.\n{content.top_text}",
                level="success"
            )

            return content

        except Exception as e:
            logger.error(f"Error running channel {channel_name}: {e}")
            await self.notifier.notify_error(channel_name, str(e))
            return None

    async def run_all_channels(self) -> List[MemeContent]:
        """
        모든 활성화된 채널을 실행합니다.

        Returns:
            생성된 MemeContent 목록
        """
        channels = self.config_loader.get_all_channels()
        results = []

        for channel_name in channels:
            logger.info(f"Processing channel: {channel_name}")
            content = await self.run_channel(channel_name)
            if content:
                results.append(content)

        logger.info(f"Completed {len(results)} channels")
        return results

    async def _upload_to_platforms(
        self,
        content: MemeContent,
        platform_names: List[str]
    ) -> None:
        """
        콘텐츠를 지정된 플랫폼에 업로드합니다.

        Args:
            content: 업로드할 MemeContent
            platform_names: 플랫폼 이름 목록
        """
        for platform_name in platform_names:
            platform = self.platforms.get(platform_name)
            if not platform:
                logger.warning(f"Unknown platform: {platform_name}")
                continue

            if not platform.is_enabled:
                logger.debug(f"Platform {platform_name} is not enabled")
                continue

            try:
                # 플랫폼별 최적화
                title = content.top_text or "오늘의 밈"
                optimized_title = self.optimizer.optimize_title(title, platform_name)
                hashtags = self.optimizer.optimize_hashtags(
                    content.hashtags or [], platform_name, content
                )

                metadata = {
                    "title": optimized_title,
                    "tags": hashtags,
                    "description": content.meme_text or content.narration or "",
                }

                # 업로드
                if platform_name == "youtube":
                    # YouTube는 자동 업로드
                    result = await platform.upload(content, metadata)
                    if result:
                        await self.notifier.notify_upload_success(
                            platform_name, optimized_title, result
                        )
                    else:
                        await self._notify_manual_upload(platform_name, content)
                else:
                    # TikTok, Instagram은 수동 업로드 안내
                    await self._notify_manual_upload(platform_name, content)

            except Exception as e:
                logger.error(f"Upload to {platform_name} failed: {e}")
                await self.notifier.notify_upload_failure(platform_name, str(e))

    async def _notify_manual_upload(
        self,
        platform_name: str,
        content: MemeContent
    ) -> None:
        """
        수동 업로드가 필요한 플랫폼에 대해 알림을 전송합니다.

        Args:
            platform_name: 플랫폼 이름
            content: MemeContent
        """
        message = f"""
[{platform_name.upper()}] 수동 업로드가 필요합니다.

파일 위치:
- 비디오: {content.video_path}
- 이미지: {content.image_path}

제안 캡션:
{content.top_text}
{content.bottom_text}

해시태그:
{' '.join(content.hashtags[:5])}
"""
        await self.notifier.notify(
            title=f"[{platform_name.upper()}] 수동 업로드 필요",
            message=message.strip(),
            level="info"
        )

    async def start_scheduler(self) -> None:
        """스케줄러를 시작합니다."""
        logger.info("Starting scheduler...")

        # 채널 설정에서 스케줄 구성
        self.scheduler.setup_from_channels(self)
        self.scheduler.print_schedule()
        self.scheduler.start()

        self._running = True

        # 시그널 핸들러 설정
        try:
            loop = asyncio.get_event_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, self._shutdown)
        except NotImplementedError:
            # Windows에서는 add_signal_handler가 지원되지 않음
            pass

        logger.info("Scheduler started. Press Ctrl+C to stop.")

        # 메인 루프
        while self._running:
            await asyncio.sleep(1)

        self.scheduler.stop()
        logger.info("Scheduler stopped")

    def _shutdown(self) -> None:
        """애플리케이션을 종료합니다."""
        logger.info("Shutdown signal received")
        self._running = False

    # 레거시 호환 메서드들
    async def run_daily(self) -> Optional[MemeContent]:
        """일일 밈 콘텐츠를 생성합니다."""
        return await self.run_channel("daily_meme")

    async def run_trend(self) -> Optional[MemeContent]:
        """트렌드 밈 콘텐츠를 생성합니다."""
        return await self.run_channel("trend_meme")

    async def run_it(self) -> Optional[MemeContent]:
        """IT 밈 콘텐츠를 생성합니다."""
        return await self.run_channel("it_meme")


async def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="MemeNews - 뉴스/트렌드 기반 밈 콘텐츠 자동 생성 및 배포",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --channel daily_meme   # 일상밈공장 채널 실행
  python main.py --channel trend_meme   # 오늘의밈 채널 실행
  python main.py --channel it_meme      # IT밈 채널 실행
  python main.py --all                  # 모든 채널 실행
  python main.py --schedule             # 스케줄러 모드
  python main.py --dry-run --all        # 테스트 모드로 전체 실행
"""
    )

    parser.add_argument(
        "--channel",
        type=str,
        choices=["daily_meme", "trend_meme", "it_meme"],
        help="실행할 채널 이름"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="모든 활성화된 채널 실행"
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="스케줄러 모드로 실행"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="테스트 모드 (콘텐츠 생성만, 업로드 안함)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="디버그 모드 활성화"
    )

    # 레거시 호환
    parser.add_argument(
        "--run",
        choices=["daily", "trend", "it"],
        help="(레거시) 즉시 실행할 콘텐츠 유형"
    )

    args = parser.parse_args()

    # 애플리케이션 초기화
    app = MemeNewsApp(dry_run=args.dry_run)
    await app.initialize()

    # 실행 모드 결정
    if args.channel:
        # 특정 채널 실행
        await app.run_channel(args.channel)

    elif args.all:
        # 전체 채널 실행
        await app.run_all_channels()

    elif args.run:
        # 레거시 호환 모드
        channel_map = {
            "daily": "daily_meme",
            "trend": "trend_meme",
            "it": "it_meme"
        }
        channel_name = channel_map.get(args.run, "daily_meme")
        await app.run_channel(channel_name)

    elif args.schedule:
        # 스케줄러 모드
        await app.start_scheduler()

    else:
        # 기본: 스케줄러 모드
        await app.start_scheduler()


if __name__ == "__main__":
    asyncio.run(main())
