"""
스케줄러 제어 모듈

콘텐츠 생성 스케줄러를 관리합니다.
"""

import asyncio
import json
import os
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, List, Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config_loader import ConfigLoader
from src.core.pipeline import Pipeline


class SchedulerControl:
    """스케줄러 제어 클래스"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.stats_file = self.data_dir / "stats.json"
        self.log_file = Path("logs") / "memenews.log"
        self.config_loader = ConfigLoader()
        self._scheduler_running = False

    def _load_stats(self) -> Dict[str, Any]:
        """통계 로드"""
        if not self.stats_file.exists():
            return {
                "total_generated": 0,
                "by_channel": {},
                "by_date": {},
            }

        with open(self.stats_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_stats(self, stats: Dict[str, Any]):
        """통계 저장"""
        with open(self.stats_file, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)

    def get_total_generated(self) -> int:
        """총 생성 콘텐츠 수"""
        stats = self._load_stats()
        return stats.get("total_generated", 0)

    def get_today_generated(self) -> int:
        """오늘 생성된 콘텐츠 수"""
        stats = self._load_stats()
        today = date.today().isoformat()
        return stats.get("by_date", {}).get(today, 0)

    def get_status(self) -> Dict[str, Any]:
        """스케줄러 상태"""
        return {
            "running": self._scheduler_running,
            "last_run": self._get_last_run_time(),
            "next_run": self._get_next_run_time(),
        }

    def _get_last_run_time(self) -> Optional[str]:
        """마지막 실행 시간"""
        stats = self._load_stats()
        return stats.get("last_run")

    def _get_next_run_time(self) -> Optional[str]:
        """다음 예정 실행 시간"""
        # 채널 설정에서 다음 스케줄 계산
        channels = self.config_loader.get_all_channels()
        next_times = []

        now = datetime.now()
        for channel_name, channel_config in channels.items():
            schedule = channel_config.get("schedule", {})
            times = schedule.get("times", [])

            for time_str in times:
                hour, minute = map(int, time_str.split(":"))
                scheduled = now.replace(hour=hour, minute=minute, second=0)
                if scheduled > now:
                    next_times.append(scheduled)

        if next_times:
            return min(next_times).strftime("%Y-%m-%d %H:%M")
        return None

    def get_channel_stats(self) -> Dict[str, Dict[str, Any]]:
        """채널별 통계"""
        stats = self._load_stats()
        channels = self.config_loader.get_all_channels()

        result = {}
        for channel_name, channel_config in channels.items():
            channel_stats = stats.get("by_channel", {}).get(channel_name, {})
            result[channel_name] = {
                "name": channel_config.get("name", channel_name),
                "total": channel_stats.get("total", 0),
                "today": channel_stats.get(date.today().isoformat(), 0),
                "schedule_count": channel_config.get("schedule", {}).get("count", 0),
            }

        return result

    def get_available_channels(self) -> List[Dict[str, Any]]:
        """사용 가능한 채널 목록"""
        channels = self.config_loader.get_all_channels()
        return [
            {
                "id": channel_name,
                "name": channel_config.get("name", channel_name),
                "category": channel_config.get("category", ""),
                "platforms": channel_config.get("platforms", []),
            }
            for channel_name, channel_config in channels.items()
        ]

    async def run_channel(self, channel_name: str, dry_run: bool = False) -> Dict[str, Any]:
        """채널 실행"""
        try:
            pipeline = Pipeline(self.config_loader)
            result = await pipeline.run_channel(channel_name, dry_run=dry_run)

            if not dry_run:
                # 통계 업데이트
                self._update_stats(channel_name)

            return {
                "success": True,
                "channel": channel_name,
                "dry_run": dry_run,
                "result": result,
            }
        except Exception as e:
            return {
                "success": False,
                "channel": channel_name,
                "error": str(e),
            }

    def _update_stats(self, channel_name: str):
        """통계 업데이트"""
        stats = self._load_stats()

        # 전체 카운트
        stats["total_generated"] = stats.get("total_generated", 0) + 1

        # 날짜별
        today = date.today().isoformat()
        if "by_date" not in stats:
            stats["by_date"] = {}
        stats["by_date"][today] = stats["by_date"].get(today, 0) + 1

        # 채널별
        if "by_channel" not in stats:
            stats["by_channel"] = {}
        if channel_name not in stats["by_channel"]:
            stats["by_channel"][channel_name] = {"total": 0}

        stats["by_channel"][channel_name]["total"] = \
            stats["by_channel"][channel_name].get("total", 0) + 1
        stats["by_channel"][channel_name][today] = \
            stats["by_channel"][channel_name].get(today, 0) + 1

        # 마지막 실행 시간
        stats["last_run"] = datetime.now().isoformat()

        self._save_stats(stats)

    def get_schedule(self) -> List[Dict[str, Any]]:
        """스케줄 목록"""
        channels = self.config_loader.get_all_channels()
        schedule_list = []

        for channel_name, channel_config in channels.items():
            schedule = channel_config.get("schedule", {})
            times = schedule.get("times", [])

            for time_str in times:
                schedule_list.append({
                    "channel": channel_name,
                    "channel_name": channel_config.get("name", channel_name),
                    "time": time_str,
                    "platforms": channel_config.get("platforms", []),
                })

        # 시간순 정렬
        schedule_list.sort(key=lambda x: x["time"])
        return schedule_list

    def start(self):
        """스케줄러 시작"""
        self._scheduler_running = True

    def stop(self):
        """스케줄러 중지"""
        self._scheduler_running = False

    def get_recent_logs(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """최근 로그 조회"""
        if not self.log_file.exists():
            return []

        logs = []
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # 역순으로 읽기 (최신 로그 먼저)
            for line in reversed(lines):
                line = line.strip()
                if not line:
                    continue

                # 로그 파싱
                log_entry = self._parse_log_line(line)
                if log_entry:
                    logs.append(log_entry)

                if len(logs) >= offset + limit:
                    break

            return logs[offset:offset + limit]
        except Exception:
            return []

    def _parse_log_line(self, line: str) -> Optional[Dict[str, Any]]:
        """로그 라인 파싱"""
        try:
            # 형식: 2024-01-01 12:00:00 | INFO | module | message
            parts = line.split(" | ", 3)
            if len(parts) >= 4:
                return {
                    "timestamp": parts[0],
                    "level": parts[1],
                    "module": parts[2],
                    "message": parts[3],
                }
            return {"timestamp": "", "level": "INFO", "module": "", "message": line}
        except Exception:
            return None

    def get_output_files(self) -> Dict[str, List[Dict[str, Any]]]:
        """생성된 파일 목록"""
        output_dir = Path("output")
        files = {
            "images": [],
            "videos": [],
        }

        if (output_dir / "images").exists():
            for f in sorted((output_dir / "images").glob("*"), reverse=True)[:50]:
                if f.is_file():
                    files["images"].append({
                        "name": f.name,
                        "path": str(f),
                        "size": f.stat().st_size,
                        "created": datetime.fromtimestamp(f.stat().st_ctime).isoformat(),
                    })

        if (output_dir / "videos").exists():
            for f in sorted((output_dir / "videos").glob("*"), reverse=True)[:50]:
                if f.is_file():
                    files["videos"].append({
                        "name": f.name,
                        "path": str(f),
                        "size": f.stat().st_size,
                        "created": datetime.fromtimestamp(f.stat().st_ctime).isoformat(),
                    })

        return files
