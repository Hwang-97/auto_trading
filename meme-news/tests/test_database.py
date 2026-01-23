"""
Database Tests
"""

import pytest
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.models import Database, Content, Upload, Analytics, TrendData


class TestDatabase:
    """Database 테스트"""

    @pytest.fixture
    def db(self, temp_dir):
        """테스트용 데이터베이스"""
        db_path = temp_dir / "test.db"
        return Database(str(db_path))

    def test_database_initialization(self, db):
        """데이터베이스 초기화 테스트"""
        assert db.db_path.exists()

    def test_create_content(self, db):
        """콘텐츠 생성 테스트"""
        content = Content(
            channel_name="test_channel",
            content_type="daily",
            meme_text="테스트 밈",
            top_text="상단 텍스트",
            bottom_text="하단 텍스트",
            created_at=datetime.now()
        )

        content_id = db.create_content(content)

        assert content_id is not None
        assert content_id > 0

    def test_get_content(self, db):
        """콘텐츠 조회 테스트"""
        # 생성
        content = Content(
            channel_name="test_channel",
            content_type="daily",
            meme_text="조회 테스트",
            created_at=datetime.now()
        )
        content_id = db.create_content(content)

        # 조회
        retrieved = db.get_content(content_id)

        assert retrieved is not None
        assert retrieved.meme_text == "조회 테스트"
        assert retrieved.channel_name == "test_channel"

    def test_get_content_not_found(self, db):
        """존재하지 않는 콘텐츠 조회 테스트"""
        result = db.get_content(99999)
        assert result is None

    def test_update_content_status(self, db):
        """콘텐츠 상태 업데이트 테스트"""
        content = Content(
            channel_name="test",
            content_type="daily",
            status="created",
            created_at=datetime.now()
        )
        content_id = db.create_content(content)

        db.update_content_status(content_id, "uploaded")

        updated = db.get_content(content_id)
        assert updated.status == "uploaded"

    def test_get_contents_by_channel(self, db):
        """채널별 콘텐츠 조회 테스트"""
        # 여러 콘텐츠 생성
        for i in range(5):
            content = Content(
                channel_name="channel_a",
                content_type="daily",
                meme_text=f"밈 {i}",
                created_at=datetime.now()
            )
            db.create_content(content)

        for i in range(3):
            content = Content(
                channel_name="channel_b",
                content_type="trend",
                meme_text=f"트렌드 {i}",
                created_at=datetime.now()
            )
            db.create_content(content)

        # 채널별 조회
        channel_a = db.get_contents_by_channel("channel_a")
        channel_b = db.get_contents_by_channel("channel_b")

        assert len(channel_a) == 5
        assert len(channel_b) == 3


class TestUpload:
    """Upload 테스트"""

    @pytest.fixture
    def db(self, temp_dir):
        db_path = temp_dir / "test_upload.db"
        return Database(str(db_path))

    def test_create_upload(self, db):
        """업로드 생성 테스트"""
        # 먼저 콘텐츠 생성
        content = Content(
            channel_name="test",
            content_type="daily",
            created_at=datetime.now()
        )
        content_id = db.create_content(content)

        # 업로드 생성
        upload = Upload(
            content_id=content_id,
            platform="youtube",
            status="pending"
        )
        upload_id = db.create_upload(upload)

        assert upload_id is not None
        assert upload_id > 0

    def test_update_upload_status_success(self, db):
        """업로드 성공 상태 업데이트 테스트"""
        content = Content(
            channel_name="test",
            content_type="daily",
            created_at=datetime.now()
        )
        content_id = db.create_content(content)

        upload = Upload(content_id=content_id, platform="youtube")
        upload_id = db.create_upload(upload)

        db.update_upload_status(
            upload_id, "success",
            platform_id="video_123"
        )

        # 검증은 pending uploads로
        pending = db.get_pending_uploads()
        assert len(pending) == 0

    def test_get_pending_uploads(self, db):
        """대기 중인 업로드 조회 테스트"""
        content = Content(
            channel_name="test",
            content_type="daily",
            created_at=datetime.now()
        )
        content_id = db.create_content(content)

        # 여러 플랫폼에 대한 업로드 생성
        for platform in ["youtube", "tiktok", "instagram"]:
            upload = Upload(
                content_id=content_id,
                platform=platform,
                status="pending"
            )
            db.create_upload(upload)

        # 전체 대기 조회
        all_pending = db.get_pending_uploads()
        assert len(all_pending) == 3

        # 플랫폼별 조회
        youtube_pending = db.get_pending_uploads("youtube")
        assert len(youtube_pending) == 1


class TestAnalytics:
    """Analytics 테스트"""

    @pytest.fixture
    def db(self, temp_dir):
        db_path = temp_dir / "test_analytics.db"
        return Database(str(db_path))

    def test_record_analytics(self, db):
        """분석 데이터 기록 테스트"""
        content = Content(
            channel_name="test",
            content_type="daily",
            created_at=datetime.now()
        )
        content_id = db.create_content(content)

        analytics = Analytics(
            content_id=content_id,
            platform="youtube",
            views=1000,
            likes=50,
            comments=10,
            engagement_rate=6.0,
            recorded_at=datetime.now()
        )

        analytics_id = db.record_analytics(analytics)

        assert analytics_id is not None

    def test_get_analytics_summary(self, db):
        """분석 요약 조회 테스트"""
        content = Content(
            channel_name="test_channel",
            content_type="daily",
            created_at=datetime.now()
        )
        content_id = db.create_content(content)

        analytics = Analytics(
            content_id=content_id,
            platform="youtube",
            views=500,
            likes=25,
            recorded_at=datetime.now()
        )
        db.record_analytics(analytics)

        summary = db.get_analytics_summary("test_channel", days=1)

        assert summary is not None
        assert "total_views" in summary
        assert "total_contents" in summary


class TestTrends:
    """Trends 테스트"""

    @pytest.fixture
    def db(self, temp_dir):
        db_path = temp_dir / "test_trends.db"
        return Database(str(db_path))

    def test_record_trend(self, db):
        """트렌드 기록 테스트"""
        trend = TrendData(
            source="google",
            keyword="테스트 키워드",
            rank=1,
            search_volume=10000,
            recorded_at=datetime.now()
        )

        trend_id = db.record_trend(trend)

        assert trend_id is not None

    def test_get_recent_trends(self, db):
        """최근 트렌드 조회 테스트"""
        # 여러 트렌드 기록
        for i in range(10):
            trend = TrendData(
                source="google",
                keyword=f"키워드 {i}",
                rank=i + 1,
                recorded_at=datetime.now()
            )
            db.record_trend(trend)

        trends = db.get_recent_trends("google", hours=1, limit=5)

        assert len(trends) == 5
        assert trends[0].rank == 1

    def test_is_duplicate_content(self, db):
        """중복 콘텐츠 확인 테스트"""
        content = Content(
            channel_name="test",
            content_type="daily",
            meme_text="중복 테스트 텍스트",
            created_at=datetime.now()
        )
        db.create_content(content)

        # 중복 확인
        is_dup = db.is_duplicate_content("중복 테스트 텍스트")
        assert is_dup is True

        is_not_dup = db.is_duplicate_content("새로운 텍스트")
        assert is_not_dup is False
