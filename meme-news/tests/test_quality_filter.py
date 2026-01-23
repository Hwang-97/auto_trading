"""
Quality Filter Tests
"""

import pytest
from pathlib import Path
from dataclasses import dataclass

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.content.quality_filter import ContentQualityFilter, QualityReport


@dataclass
class MockContent:
    """테스트용 Mock 콘텐츠"""
    meme_text: str = ""
    top_text: str = ""
    bottom_text: str = ""
    narration: str = ""
    hashtags: list = None

    def __post_init__(self):
        if self.hashtags is None:
            self.hashtags = []


class TestContentQualityFilter:
    """ContentQualityFilter 테스트"""

    @pytest.fixture
    def quality_filter(self):
        """QualityFilter 인스턴스"""
        return ContentQualityFilter()

    def test_quality_report_creation(self):
        """QualityReport 생성 테스트"""
        report = QualityReport(
            passed=True,
            score=85.0,
            issues=[],
            suggestions=["테스트 제안"]
        )

        assert report.passed is True
        assert report.score == 85.0
        assert len(report.suggestions) == 1

    def test_quality_check_normal_content(self, quality_filter):
        """정상 콘텐츠 품질 검사 테스트"""
        content = MockContent(
            top_text="월요일 아침에 일어나면",
            bottom_text="어쩔 수 없지 출근해야지",
            narration="월요일 아침, 알람 소리에 눈을 뜨는 순간의 절망감을 표현했습니다.",
            hashtags=["#월요병", "#직장인", "#출근", "#공감", "#Shorts"]
        )

        report = quality_filter.check_quality(content)

        assert report.passed is True
        assert report.score >= 50

    def test_blocked_keyword_detection(self, quality_filter):
        """금지 키워드 감지 테스트"""
        content = MockContent(
            top_text="시발 월요일",
            bottom_text="출근하기 싫다"
        )

        report = quality_filter.check_quality(content)

        assert report.passed is False
        assert any("금지" in issue for issue in report.issues)

    def test_warning_keyword_detection(self, quality_filter):
        """경고 키워드 감지 테스트"""
        content = MockContent(
            top_text="이 논란은 심각해",
            bottom_text="정말 문제다",
            narration="논란이 되고 있는 상황을 설명합니다."
        )

        report = quality_filter.check_quality(content)

        # 경고는 suggestions에 포함
        has_warning = any("주의" in s for s in report.suggestions)
        assert has_warning

    def test_spam_pattern_detection(self, quality_filter):
        """스팸 패턴 감지 테스트"""
        content = MockContent(
            top_text="텔레그램으로 문의하세요",
            bottom_text="수익 보장합니다"
        )

        report = quality_filter.check_quality(content)

        assert any("스팸" in issue for issue in report.issues)

    def test_text_length_too_long(self, quality_filter):
        """텍스트 길이 초과 테스트"""
        long_text = "아" * 150  # 100자 초과

        content = MockContent(
            top_text=long_text,
            bottom_text="정상"
        )

        report = quality_filter.check_quality(content)

        assert any("김" in issue for issue in report.issues)

    def test_hashtag_count_warning(self, quality_filter):
        """해시태그 개수 경고 테스트"""
        content = MockContent(
            top_text="테스트",
            bottom_text="밈",
            hashtags=["#태그"]  # 3개 미만
        )

        report = quality_filter.check_quality(content)

        has_hashtag_suggestion = any(
            "해시태그" in s for s in report.suggestions
        )
        assert has_hashtag_suggestion

    def test_duplicate_text_detection(self, quality_filter):
        """중복 텍스트 감지 테스트"""
        content = MockContent(
            top_text="같은 텍스트",
            bottom_text="같은 텍스트"
        )

        report = quality_filter.check_quality(content)

        assert any("동일" in issue for issue in report.issues)

    def test_shorts_hashtag_suggestion(self, quality_filter):
        """#Shorts 해시태그 제안 테스트"""
        content = MockContent(
            top_text="테스트",
            bottom_text="밈",
            hashtags=["#테스트", "#밈", "#일상"]  # #Shorts 없음
        )

        report = quality_filter.check_quality(content)

        has_shorts_suggestion = any(
            "#Shorts" in s for s in report.suggestions
        )
        assert has_shorts_suggestion


class TestHashtagFiltering:
    """해시태그 필터링 테스트"""

    @pytest.fixture
    def quality_filter(self):
        return ContentQualityFilter()

    def test_filter_hashtags_youtube(self, quality_filter):
        """YouTube 해시태그 필터링 테스트"""
        hashtags = ["#밈", "#테스트", "#재미"]

        filtered = quality_filter.filter_hashtags(hashtags, "youtube")

        assert "#Shorts" in filtered
        assert len(filtered) <= 15

    def test_filter_hashtags_tiktok(self, quality_filter):
        """TikTok 해시태그 필터링 테스트"""
        hashtags = ["#밈", "#테스트", "#재미", "#일상", "#공감", "#틱톡"]

        filtered = quality_filter.filter_hashtags(hashtags, "tiktok")

        assert "#fyp" in filtered
        assert len(filtered) <= 5

    def test_filter_hashtags_removes_duplicates(self, quality_filter):
        """중복 해시태그 제거 테스트"""
        hashtags = ["#밈", "#밈", "#테스트", "#밈"]

        filtered = quality_filter.filter_hashtags(hashtags, "youtube")

        # 중복 제거 후 유니크한 태그만
        unique_without_required = [h for h in filtered if h != "#Shorts"]
        assert len(unique_without_required) <= 2


class TestTextSanitization:
    """텍스트 정제 테스트"""

    @pytest.fixture
    def quality_filter(self):
        return ContentQualityFilter()

    def test_sanitize_removes_extra_spaces(self, quality_filter):
        """연속 공백 제거 테스트"""
        text = "테스트    여러   공백"

        sanitized = quality_filter.sanitize_text(text)

        assert "  " not in sanitized
        assert sanitized == "테스트 여러 공백"

    def test_sanitize_trims_whitespace(self, quality_filter):
        """앞뒤 공백 제거 테스트"""
        text = "   테스트   "

        sanitized = quality_filter.sanitize_text(text)

        assert sanitized == "테스트"

    def test_sanitize_masks_blocked_keywords(self, quality_filter):
        """금지 키워드 마스킹 테스트"""
        text = "시발 정말 짜증나"

        sanitized = quality_filter.sanitize_text(text)

        assert "시발" not in sanitized
        assert "**" in sanitized

    def test_sanitize_empty_string(self, quality_filter):
        """빈 문자열 정제 테스트"""
        sanitized = quality_filter.sanitize_text("")
        assert sanitized == ""

        sanitized = quality_filter.sanitize_text(None)
        assert sanitized == ""
