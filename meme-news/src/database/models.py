"""
Database Models for MemeNews

SQLite 기반 데이터 저장소 모델 정의
"""

import json
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from contextlib import contextmanager

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Content:
    """생성된 콘텐츠 모델"""
    id: Optional[int] = None
    channel_name: str = ""
    content_type: str = ""
    meme_text: str = ""
    top_text: str = ""
    bottom_text: str = ""
    narration: str = ""
    hashtags: str = ""  # JSON string
    image_path: Optional[str] = None
    video_path: Optional[str] = None
    quality_score: float = 0.0
    status: str = "created"  # created, uploaded, failed
    created_at: datetime = field(default_factory=datetime.now)
    metadata: str = "{}"  # JSON string

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        d = asdict(self)
        d["created_at"] = self.created_at.isoformat()
        return d

    @classmethod
    def from_row(cls, row: tuple, columns: List[str]) -> "Content":
        """데이터베이스 행에서 생성"""
        data = dict(zip(columns, row))
        if data.get("created_at"):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)


@dataclass
class Upload:
    """업로드 기록 모델"""
    id: Optional[int] = None
    content_id: int = 0
    platform: str = ""
    platform_id: str = ""  # YouTube video ID, etc.
    status: str = "pending"  # pending, success, failed
    error_message: Optional[str] = None
    uploaded_at: Optional[datetime] = None
    retry_count: int = 0
    metadata: str = "{}"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.uploaded_at:
            d["uploaded_at"] = self.uploaded_at.isoformat()
        return d

    @classmethod
    def from_row(cls, row: tuple, columns: List[str]) -> "Upload":
        data = dict(zip(columns, row))
        if data.get("uploaded_at"):
            data["uploaded_at"] = datetime.fromisoformat(data["uploaded_at"])
        return cls(**data)


@dataclass
class Analytics:
    """분석 데이터 모델"""
    id: Optional[int] = None
    content_id: int = 0
    platform: str = ""
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    engagement_rate: float = 0.0
    recorded_at: datetime = field(default_factory=datetime.now)
    metadata: str = "{}"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["recorded_at"] = self.recorded_at.isoformat()
        return d

    @classmethod
    def from_row(cls, row: tuple, columns: List[str]) -> "Analytics":
        data = dict(zip(columns, row))
        if data.get("recorded_at"):
            data["recorded_at"] = datetime.fromisoformat(data["recorded_at"])
        return cls(**data)


@dataclass
class TrendData:
    """트렌드 데이터 모델"""
    id: Optional[int] = None
    source: str = ""  # google, naver, twitter
    keyword: str = ""
    rank: int = 0
    search_volume: int = 0
    category: str = ""
    recorded_at: datetime = field(default_factory=datetime.now)
    metadata: str = "{}"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["recorded_at"] = self.recorded_at.isoformat()
        return d

    @classmethod
    def from_row(cls, row: tuple, columns: List[str]) -> "TrendData":
        data = dict(zip(columns, row))
        if data.get("recorded_at"):
            data["recorded_at"] = datetime.fromisoformat(data["recorded_at"])
        return cls(**data)


class Database:
    """SQLite 데이터베이스 관리 클래스"""

    def __init__(self, db_path: str = "data/memenews.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """데이터베이스 테이블 초기화"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Contents 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_name TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    meme_text TEXT,
                    top_text TEXT,
                    bottom_text TEXT,
                    narration TEXT,
                    hashtags TEXT,
                    image_path TEXT,
                    video_path TEXT,
                    quality_score REAL DEFAULT 0.0,
                    status TEXT DEFAULT 'created',
                    created_at TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}'
                )
            """)

            # Uploads 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS uploads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content_id INTEGER NOT NULL,
                    platform TEXT NOT NULL,
                    platform_id TEXT,
                    status TEXT DEFAULT 'pending',
                    error_message TEXT,
                    uploaded_at TEXT,
                    retry_count INTEGER DEFAULT 0,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (content_id) REFERENCES contents(id)
                )
            """)

            # Analytics 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content_id INTEGER NOT NULL,
                    platform TEXT NOT NULL,
                    views INTEGER DEFAULT 0,
                    likes INTEGER DEFAULT 0,
                    comments INTEGER DEFAULT 0,
                    shares INTEGER DEFAULT 0,
                    engagement_rate REAL DEFAULT 0.0,
                    recorded_at TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (content_id) REFERENCES contents(id)
                )
            """)

            # Trends 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trends (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    keyword TEXT NOT NULL,
                    rank INTEGER DEFAULT 0,
                    search_volume INTEGER DEFAULT 0,
                    category TEXT,
                    recorded_at TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}'
                )
            """)

            # 인덱스 생성
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_contents_channel ON contents(channel_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_contents_created ON contents(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_uploads_content ON uploads(content_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_analytics_content ON analytics(content_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trends_keyword ON trends(keyword)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trends_recorded ON trends(recorded_at)")

            conn.commit()
            logger.info(f"Database initialized: {self.db_path}")

    @contextmanager
    def _get_connection(self):
        """데이터베이스 연결 컨텍스트 매니저"""
        conn = sqlite3.connect(str(self.db_path))
        try:
            yield conn
        finally:
            conn.close()

    # ===== Content CRUD =====

    def create_content(self, content: Content) -> int:
        """콘텐츠 생성"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO contents (
                    channel_name, content_type, meme_text, top_text, bottom_text,
                    narration, hashtags, image_path, video_path, quality_score,
                    status, created_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                content.channel_name, content.content_type, content.meme_text,
                content.top_text, content.bottom_text, content.narration,
                content.hashtags, content.image_path, content.video_path,
                content.quality_score, content.status,
                content.created_at.isoformat(), content.metadata
            ))
            conn.commit()
            return cursor.lastrowid

    def get_content(self, content_id: int) -> Optional[Content]:
        """콘텐츠 조회"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM contents WHERE id = ?", (content_id,))
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return Content.from_row(row, columns)
        return None

    def get_contents_by_channel(
        self, channel_name: str, limit: int = 50
    ) -> List[Content]:
        """채널별 콘텐츠 조회"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM contents
                WHERE channel_name = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (channel_name, limit))
            columns = [desc[0] for desc in cursor.description]
            return [Content.from_row(row, columns) for row in cursor.fetchall()]

    def update_content_status(self, content_id: int, status: str):
        """콘텐츠 상태 업데이트"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE contents SET status = ? WHERE id = ?",
                (status, content_id)
            )
            conn.commit()

    # ===== Upload CRUD =====

    def create_upload(self, upload: Upload) -> int:
        """업로드 기록 생성"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO uploads (
                    content_id, platform, platform_id, status,
                    error_message, uploaded_at, retry_count, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                upload.content_id, upload.platform, upload.platform_id,
                upload.status, upload.error_message,
                upload.uploaded_at.isoformat() if upload.uploaded_at else None,
                upload.retry_count, upload.metadata
            ))
            conn.commit()
            return cursor.lastrowid

    def update_upload_status(
        self, upload_id: int, status: str,
        platform_id: str = None, error_message: str = None
    ):
        """업로드 상태 업데이트"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if status == "success":
                cursor.execute("""
                    UPDATE uploads
                    SET status = ?, platform_id = ?, uploaded_at = ?
                    WHERE id = ?
                """, (status, platform_id, datetime.now().isoformat(), upload_id))
            else:
                cursor.execute("""
                    UPDATE uploads
                    SET status = ?, error_message = ?, retry_count = retry_count + 1
                    WHERE id = ?
                """, (status, error_message, upload_id))
            conn.commit()

    def get_pending_uploads(self, platform: str = None) -> List[Upload]:
        """대기 중인 업로드 조회"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if platform:
                cursor.execute("""
                    SELECT * FROM uploads
                    WHERE status = 'pending' AND platform = ?
                    ORDER BY id
                """, (platform,))
            else:
                cursor.execute("""
                    SELECT * FROM uploads WHERE status = 'pending' ORDER BY id
                """)
            columns = [desc[0] for desc in cursor.description]
            return [Upload.from_row(row, columns) for row in cursor.fetchall()]

    # ===== Analytics CRUD =====

    def record_analytics(self, analytics: Analytics) -> int:
        """분석 데이터 기록"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO analytics (
                    content_id, platform, views, likes, comments,
                    shares, engagement_rate, recorded_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                analytics.content_id, analytics.platform, analytics.views,
                analytics.likes, analytics.comments, analytics.shares,
                analytics.engagement_rate, analytics.recorded_at.isoformat(),
                analytics.metadata
            ))
            conn.commit()
            return cursor.lastrowid

    def get_analytics_summary(
        self, channel_name: str = None, days: int = 30
    ) -> Dict[str, Any]:
        """분석 요약 조회"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            query = """
                SELECT
                    COUNT(DISTINCT c.id) as total_contents,
                    SUM(a.views) as total_views,
                    SUM(a.likes) as total_likes,
                    SUM(a.comments) as total_comments,
                    AVG(a.engagement_rate) as avg_engagement
                FROM contents c
                LEFT JOIN analytics a ON c.id = a.content_id
                WHERE c.created_at >= datetime('now', ?)
            """
            params = [f"-{days} days"]

            if channel_name:
                query += " AND c.channel_name = ?"
                params.append(channel_name)

            cursor.execute(query, params)
            row = cursor.fetchone()

            return {
                "total_contents": row[0] or 0,
                "total_views": row[1] or 0,
                "total_likes": row[2] or 0,
                "total_comments": row[3] or 0,
                "avg_engagement": row[4] or 0.0
            }

    # ===== Trends CRUD =====

    def record_trend(self, trend: TrendData) -> int:
        """트렌드 데이터 기록"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trends (
                    source, keyword, rank, search_volume,
                    category, recorded_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                trend.source, trend.keyword, trend.rank,
                trend.search_volume, trend.category,
                trend.recorded_at.isoformat(), trend.metadata
            ))
            conn.commit()
            return cursor.lastrowid

    def get_recent_trends(
        self, source: str = None, hours: int = 24, limit: int = 20
    ) -> List[TrendData]:
        """최근 트렌드 조회"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            query = """
                SELECT * FROM trends
                WHERE recorded_at >= datetime('now', ?)
            """
            params = [f"-{hours} hours"]

            if source:
                query += " AND source = ?"
                params.append(source)

            query += " ORDER BY rank ASC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            columns = [desc[0] for desc in cursor.description]
            return [TrendData.from_row(row, columns) for row in cursor.fetchall()]

    def is_duplicate_content(self, meme_text: str, hours: int = 24) -> bool:
        """중복 콘텐츠 확인"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM contents
                WHERE meme_text = ?
                AND created_at >= datetime('now', ?)
            """, (meme_text, f"-{hours} hours"))
            count = cursor.fetchone()[0]
            return count > 0

    # ===== Statistics =====

    def get_daily_stats(self, date: str = None) -> Dict[str, Any]:
        """일별 통계"""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 채널별 생성 수
            cursor.execute("""
                SELECT channel_name, COUNT(*) as count
                FROM contents
                WHERE date(created_at) = ?
                GROUP BY channel_name
            """, (date,))
            by_channel = {row[0]: row[1] for row in cursor.fetchall()}

            # 전체 통계
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'uploaded' THEN 1 ELSE 0 END) as uploaded,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM contents
                WHERE date(created_at) = ?
            """, (date,))
            row = cursor.fetchone()

            return {
                "date": date,
                "total": row[0] or 0,
                "uploaded": row[1] or 0,
                "failed": row[2] or 0,
                "by_channel": by_channel
            }

    def get_top_performing_content(
        self, limit: int = 10, days: int = 30
    ) -> List[Dict[str, Any]]:
        """참여율 기준 상위 콘텐츠 조회"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    c.id, c.channel_name, c.content_type, c.meme_text,
                    c.created_at, a.platform, a.views, a.likes,
                    a.comments, a.shares, a.engagement_rate
                FROM contents c
                JOIN analytics a ON c.id = a.content_id
                WHERE c.created_at >= datetime('now', ?)
                ORDER BY a.engagement_rate DESC, a.views DESC
                LIMIT ?
            """, (f"-{days} days", limit))

            results = []
            for row in cursor.fetchall():
                results.append({
                    "content_id": row[0],
                    "channel_name": row[1],
                    "content_type": row[2],
                    "meme_text": row[3],
                    "created_at": row[4],
                    "platform": row[5],
                    "views": row[6],
                    "likes": row[7],
                    "comments": row[8],
                    "shares": row[9],
                    "engagement_rate": row[10]
                })
            return results

    def get_platform_stats(self, days: int = 30) -> Dict[str, Dict[str, Any]]:
        """플랫폼별 통계"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    u.platform,
                    COUNT(DISTINCT u.content_id) as total_uploads,
                    SUM(CASE WHEN u.status = 'success' THEN 1 ELSE 0 END) as success_count,
                    SUM(CASE WHEN u.status = 'failed' THEN 1 ELSE 0 END) as failed_count,
                    COALESCE(SUM(a.views), 0) as total_views,
                    COALESCE(SUM(a.likes), 0) as total_likes,
                    COALESCE(AVG(a.engagement_rate), 0) as avg_engagement
                FROM uploads u
                LEFT JOIN analytics a ON u.content_id = a.content_id AND u.platform = a.platform
                JOIN contents c ON u.content_id = c.id
                WHERE c.created_at >= datetime('now', ?)
                GROUP BY u.platform
            """, (f"-{days} days",))

            results = {}
            for row in cursor.fetchall():
                results[row[0]] = {
                    "total_uploads": row[1],
                    "success_count": row[2],
                    "failed_count": row[3],
                    "total_views": row[4],
                    "total_likes": row[5],
                    "avg_engagement": row[6]
                }
            return results

    def get_hourly_engagement(self, days: int = 30) -> Dict[int, Dict[str, float]]:
        """시간대별 참여율 분석"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    CAST(strftime('%H', c.created_at) AS INTEGER) as hour,
                    AVG(a.engagement_rate) as avg_engagement,
                    AVG(a.views) as avg_views,
                    COUNT(*) as count
                FROM contents c
                JOIN analytics a ON c.id = a.content_id
                WHERE c.created_at >= datetime('now', ?)
                GROUP BY hour
                ORDER BY hour
            """, (f"-{days} days",))

            results = {}
            for row in cursor.fetchall():
                results[row[0]] = {
                    "avg_engagement": row[1] or 0,
                    "avg_views": row[2] or 0,
                    "count": row[3]
                }
            return results

    def get_hashtag_stats(self, days: int = 30) -> List[Dict[str, Any]]:
        """해시태그별 성과 분석"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    c.hashtags, AVG(a.views) as avg_views,
                    AVG(a.engagement_rate) as avg_engagement,
                    COUNT(*) as count
                FROM contents c
                JOIN analytics a ON c.id = a.content_id
                WHERE c.created_at >= datetime('now', ?)
                AND c.hashtags IS NOT NULL AND c.hashtags != ''
                GROUP BY c.hashtags
                ORDER BY avg_engagement DESC
            """, (f"-{days} days",))

            results = []
            hashtag_stats = {}

            for row in cursor.fetchall():
                try:
                    hashtags = json.loads(row[0]) if row[0] else []
                except json.JSONDecodeError:
                    hashtags = []

                for tag in hashtags:
                    if tag not in hashtag_stats:
                        hashtag_stats[tag] = {
                            "total_views": 0,
                            "total_engagement": 0,
                            "count": 0
                        }
                    hashtag_stats[tag]["total_views"] += row[1] or 0
                    hashtag_stats[tag]["total_engagement"] += row[2] or 0
                    hashtag_stats[tag]["count"] += row[3]

            for tag, stats in hashtag_stats.items():
                if stats["count"] > 0:
                    results.append({
                        "hashtag": tag,
                        "avg_views": stats["total_views"] / stats["count"],
                        "avg_engagement": stats["total_engagement"] / stats["count"],
                        "usage_count": stats["count"]
                    })

            results.sort(key=lambda x: x["avg_engagement"], reverse=True)
            return results[:50]

    def get_content_type_stats(self, days: int = 30) -> Dict[str, Dict[str, Any]]:
        """콘텐츠 유형별 통계"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    c.content_type,
                    COUNT(*) as count,
                    AVG(a.views) as avg_views,
                    AVG(a.engagement_rate) as avg_engagement,
                    SUM(a.likes) as total_likes
                FROM contents c
                LEFT JOIN analytics a ON c.id = a.content_id
                WHERE c.created_at >= datetime('now', ?)
                GROUP BY c.content_type
            """, (f"-{days} days",))

            results = {}
            for row in cursor.fetchall():
                results[row[0]] = {
                    "count": row[1],
                    "avg_views": row[2] or 0,
                    "avg_engagement": row[3] or 0,
                    "total_likes": row[4] or 0
                }
            return results

    def cleanup_old_data(self, days: int = 90, archive: bool = True) -> Dict[str, int]:
        """오래된 데이터 정리"""
        deleted = {"contents": 0, "uploads": 0, "analytics": 0, "trends": 0}

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cutoff = f"-{days} days"

            # 오래된 analytics 삭제
            cursor.execute("""
                DELETE FROM analytics
                WHERE recorded_at < datetime('now', ?)
            """, (cutoff,))
            deleted["analytics"] = cursor.rowcount

            # 오래된 uploads 삭제
            cursor.execute("""
                DELETE FROM uploads
                WHERE content_id IN (
                    SELECT id FROM contents WHERE created_at < datetime('now', ?)
                )
            """, (cutoff,))
            deleted["uploads"] = cursor.rowcount

            # 오래된 contents 삭제
            cursor.execute("""
                DELETE FROM contents
                WHERE created_at < datetime('now', ?)
            """, (cutoff,))
            deleted["contents"] = cursor.rowcount

            # 오래된 trends 삭제
            cursor.execute("""
                DELETE FROM trends
                WHERE recorded_at < datetime('now', ?)
            """, (cutoff,))
            deleted["trends"] = cursor.rowcount

            conn.commit()

            # 데이터베이스 최적화
            cursor.execute("VACUUM")

            logger.info(f"Cleanup completed: {deleted}")
            return deleted

    def get_weekday_engagement(self, days: int = 30) -> Dict[int, Dict[str, float]]:
        """요일별 참여율 분석 (0=월요일, 6=일요일)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    CAST(strftime('%w', c.created_at) AS INTEGER) as weekday,
                    AVG(a.engagement_rate) as avg_engagement,
                    AVG(a.views) as avg_views,
                    COUNT(*) as count
                FROM contents c
                JOIN analytics a ON c.id = a.content_id
                WHERE c.created_at >= datetime('now', ?)
                GROUP BY weekday
                ORDER BY weekday
            """, (f"-{days} days",))

            results = {}
            for row in cursor.fetchall():
                # SQLite의 %w: 0=일요일, 1=월요일...
                # 파이썬 weekday: 0=월요일, 6=일요일로 변환
                weekday = (row[0] - 1) % 7
                results[weekday] = {
                    "avg_engagement": row[1] or 0,
                    "avg_views": row[2] or 0,
                    "count": row[3]
                }
            return results
