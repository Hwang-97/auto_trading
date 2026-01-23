"""
스케줄러 모듈 - 작업 예약 및 실행

채널별 스케줄에 따라 콘텐츠 생성 작업을 예약하고 실행합니다.
"""

import asyncio
from datetime import datetime
from typing import Callable, Dict, List, Optional, TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ..utils.logger import get_logger

if TYPE_CHECKING:
    from .config_loader import ConfigLoader

logger = get_logger(__name__)


class Scheduler:
    """콘텐츠 생성 작업을 스케줄링하는 클래스"""

    def __init__(self, config_loader: "ConfigLoader"):
        """
        스케줄러를 초기화합니다.

        Args:
            config_loader: ConfigLoader 인스턴스
        """
        self.config_loader = config_loader
        self.scheduler = AsyncIOScheduler(timezone="Asia/Seoul")
        self._jobs: Dict[str, str] = {}
        self._running = False

    def start(self) -> None:
        """스케줄러를 시작합니다."""
        if not self.scheduler.running:
            self.scheduler.start()
            self._running = True
            logger.info("Scheduler started")

    def stop(self) -> None:
        """스케줄러를 중지합니다."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            self._running = False
            logger.info("Scheduler stopped")

    @property
    def is_running(self) -> bool:
        """스케줄러 실행 상태를 반환합니다."""
        return self._running

    def add_time_job(
        self,
        job_id: str,
        func: Callable,
        time_str: str,
        args: Optional[List] = None,
    ) -> None:
        """
        특정 시간에 실행되는 작업을 추가합니다.

        Args:
            job_id: 작업 ID
            func: 실행할 함수
            time_str: 시간 문자열 (예: "09:00")
            args: 함수 인자
        """
        try:
            hour, minute = map(int, time_str.split(":"))

            trigger = CronTrigger(hour=hour, minute=minute)

            job = self.scheduler.add_job(
                func,
                trigger=trigger,
                id=job_id,
                args=args or [],
                replace_existing=True,
            )
            self._jobs[job_id] = job.id
            logger.info(f"Added time job: {job_id} at {time_str}")

        except ValueError as e:
            logger.error(f"Invalid time format '{time_str}': {e}")
            raise

    def add_cron_job(
        self,
        job_id: str,
        func: Callable,
        cron_expression: str,
        args: Optional[List] = None,
    ) -> None:
        """
        크론 표현식으로 작업을 추가합니다.

        Args:
            job_id: 작업 ID
            func: 실행할 함수
            cron_expression: 크론 표현식 (분 시 일 월 요일)
            args: 함수 인자
        """
        parts = cron_expression.split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {cron_expression}")

        minute, hour, day, month, day_of_week = parts

        trigger = CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
        )

        job = self.scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            args=args or [],
            replace_existing=True,
        )
        self._jobs[job_id] = job.id
        logger.info(f"Added cron job: {job_id} with schedule: {cron_expression}")

    def remove_job(self, job_id: str) -> None:
        """작업을 제거합니다."""
        if job_id in self._jobs:
            try:
                self.scheduler.remove_job(job_id)
                del self._jobs[job_id]
                logger.info(f"Removed job: {job_id}")
            except Exception as e:
                logger.error(f"Error removing job {job_id}: {e}")

    def get_jobs(self) -> List[Dict]:
        """등록된 모든 작업을 반환합니다."""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "next_run_time": str(job.next_run_time) if job.next_run_time else "Not scheduled",
                "trigger": str(job.trigger),
            })
        return jobs

    def setup_from_channels(self, app) -> None:
        """
        채널 설정에서 스케줄을 설정합니다.

        Args:
            app: MemeNewsApp 인스턴스 (run_channel 메서드 필요)
        """
        channels = self.config_loader.get_all_channels()

        for channel_name, channel_config in channels.items():
            if not channel_config.get("enabled", True):
                continue

            schedule = channel_config.get("schedule", {})
            times = schedule.get("times", [])

            for idx, time_str in enumerate(times):
                job_id = f"{channel_name}_{idx}"

                # 비동기 함수를 래핑
                async def job_wrapper(ch_name=channel_name):
                    await app.run_channel(ch_name)

                self.add_time_job(
                    job_id=job_id,
                    func=job_wrapper,
                    time_str=time_str,
                )

            logger.info(
                f"Scheduled {len(times)} jobs for channel: {channel_name} "
                f"at times: {times}"
            )

        logger.info("Scheduler configured from channel settings")

    def setup_from_config(self, pipeline) -> None:
        """
        설정 파일에서 스케줄을 설정합니다 (레거시 호환).

        Args:
            pipeline: Pipeline 인스턴스
        """
        config = self.config_loader.load("config")
        schedule_config = config.get("schedule", {})

        # Daily news
        daily = schedule_config.get("daily_news", {})
        if daily.get("enabled"):
            self.add_cron_job(
                "daily_news",
                pipeline.run_daily,
                daily.get("cron", "0 9 * * *"),
            )

        # Trend news
        trend = schedule_config.get("trend_news", {})
        if trend.get("enabled"):
            # 4시간마다 실행
            self.add_cron_job(
                "trend_news",
                pipeline.run_trend,
                "0 */4 * * *",
            )

        # IT news
        it = schedule_config.get("it_news", {})
        if it.get("enabled"):
            self.add_cron_job(
                "it_news",
                pipeline.run_it,
                it.get("cron", "0 18 * * *"),
            )

        logger.info("Scheduler configured from config file")

    def print_schedule(self) -> None:
        """현재 스케줄을 출력합니다."""
        jobs = self.get_jobs()
        if not jobs:
            logger.info("No scheduled jobs")
            return

        logger.info("=== Scheduled Jobs ===")
        for job in jobs:
            logger.info(
                f"  - {job['id']}: next run at {job['next_run_time']}"
            )
