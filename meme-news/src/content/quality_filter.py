"""
Content Quality Filter

콘텐츠 품질 검사 및 필터링
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class QualityReport:
    """품질 검사 결과"""
    passed: bool
    score: float
    issues: List[str]
    suggestions: List[str]

    def to_dict(self) -> Dict:
        return {
            "passed": self.passed,
            "score": self.score,
            "issues": self.issues,
            "suggestions": self.suggestions
        }


class ContentQualityFilter:
    """콘텐츠 품질 필터"""

    # 금지 키워드 (비속어, 혐오 표현 등)
    BLOCKED_KEYWORDS = [
        # 비속어
        "시발", "씨발", "개새끼", "병신", "지랄",
        # 차별 표현
        "틀딱", "한남", "한녀", "김치녀",
        # 민감한 주제
        "자살", "자해", "폭력", "살인",
        # 정치
        "빨갱이", "수꼴",
    ]

    # 경고 키워드 (주의 필요)
    WARNING_KEYWORDS = [
        "논란", "비난", "고소", "소송", "사망", "사고",
        "성희롱", "폭행", "학대"
    ]

    # 스팸 패턴
    SPAM_PATTERNS = [
        r"(?i)(텔레그램|카톡|오픈채팅).*(문의|상담)",
        r"(?i)(수익|부업|재테크).*(보장|확실)",
        r"(?i)무료\s*(상담|체험|증정)",
        r"(?i)(광고|홍보|협찬).*클릭",
    ]

    # 품질 기준
    MIN_TEXT_LENGTH = 5
    MAX_TEXT_LENGTH = 100
    MIN_HASHTAG_COUNT = 3
    MAX_HASHTAG_COUNT = 15
    MIN_NARRATION_LENGTH = 20

    def __init__(self, config_loader=None):
        self.config_loader = config_loader

        # 설정에서 추가 필터 키워드 로드
        if config_loader:
            try:
                sources = config_loader.load("sources")
                filters = sources.get("keyword_filters", {})
                exclude = filters.get("exclude", {})

                self.BLOCKED_KEYWORDS.extend(exclude.get("common", []))
                self.BLOCKED_KEYWORDS.extend(exclude.get("sensitive", []))
            except Exception:
                pass

    def check_quality(self, content) -> QualityReport:
        """콘텐츠 품질 검사"""
        issues = []
        suggestions = []
        score = 100.0

        # 1. 금지 키워드 검사
        blocked_found = self._check_blocked_keywords(content)
        if blocked_found:
            issues.append(f"금지 키워드 발견: {', '.join(blocked_found)}")
            score -= 50  # 심각한 감점

        # 2. 경고 키워드 검사
        warnings_found = self._check_warning_keywords(content)
        if warnings_found:
            suggestions.append(f"주의 필요 키워드: {', '.join(warnings_found)}")
            score -= 10

        # 3. 스팸 패턴 검사
        if self._check_spam_patterns(content):
            issues.append("스팸 패턴 감지")
            score -= 30

        # 4. 텍스트 길이 검사
        length_issue, length_suggestion = self._check_text_length(content)
        if length_issue:
            issues.append(length_issue)
            score -= 15
        if length_suggestion:
            suggestions.append(length_suggestion)

        # 5. 해시태그 검사
        hashtag_issue, hashtag_suggestion = self._check_hashtags(content)
        if hashtag_issue:
            issues.append(hashtag_issue)
            score -= 10
        if hashtag_suggestion:
            suggestions.append(hashtag_suggestion)

        # 6. 나레이션 검사
        narration_issue = self._check_narration(content)
        if narration_issue:
            suggestions.append(narration_issue)
            score -= 5

        # 7. 중복 텍스트 검사
        if self._check_duplicate_text(content):
            issues.append("상단/하단 텍스트가 동일함")
            score -= 10

        # 8. 이모지 과다 사용 검사
        if self._check_excessive_emoji(content):
            suggestions.append("이모지 사용량 줄이기 권장")
            score -= 5

        # 점수 정규화
        score = max(0, min(100, score))

        # 50점 이상이면 통과
        passed = score >= 50 and len([i for i in issues if "금지" in i]) == 0

        return QualityReport(
            passed=passed,
            score=score,
            issues=issues,
            suggestions=suggestions
        )

    def _check_blocked_keywords(self, content) -> List[str]:
        """금지 키워드 검사"""
        found = []
        text = self._get_all_text(content).lower()

        for keyword in self.BLOCKED_KEYWORDS:
            if keyword.lower() in text:
                found.append(keyword)

        return found

    def _check_warning_keywords(self, content) -> List[str]:
        """경고 키워드 검사"""
        found = []
        text = self._get_all_text(content).lower()

        for keyword in self.WARNING_KEYWORDS:
            if keyword.lower() in text:
                found.append(keyword)

        return found

    def _check_spam_patterns(self, content) -> bool:
        """스팸 패턴 검사"""
        text = self._get_all_text(content)

        for pattern in self.SPAM_PATTERNS:
            if re.search(pattern, text):
                return True

        return False

    def _check_text_length(self, content) -> Tuple[Optional[str], Optional[str]]:
        """텍스트 길이 검사"""
        issue = None
        suggestion = None

        top_text = getattr(content, 'top_text', '') or ''
        bottom_text = getattr(content, 'bottom_text', '') or ''

        if len(top_text) > 0 and len(top_text) < self.MIN_TEXT_LENGTH:
            issue = f"상단 텍스트가 너무 짧음 ({len(top_text)}자)"

        if len(top_text) > self.MAX_TEXT_LENGTH:
            issue = f"상단 텍스트가 너무 김 ({len(top_text)}자)"
            suggestion = f"상단 텍스트를 {self.MAX_TEXT_LENGTH}자 이내로 줄이세요"

        if len(bottom_text) > self.MAX_TEXT_LENGTH:
            issue = f"하단 텍스트가 너무 김 ({len(bottom_text)}자)"

        return issue, suggestion

    def _check_hashtags(self, content) -> Tuple[Optional[str], Optional[str]]:
        """해시태그 검사"""
        issue = None
        suggestion = None

        hashtags = getattr(content, 'hashtags', []) or []

        if len(hashtags) < self.MIN_HASHTAG_COUNT:
            suggestion = f"해시태그를 {self.MIN_HASHTAG_COUNT}개 이상 추가하세요"

        if len(hashtags) > self.MAX_HASHTAG_COUNT:
            issue = f"해시태그가 너무 많음 ({len(hashtags)}개)"
            suggestion = f"해시태그를 {self.MAX_HASHTAG_COUNT}개 이하로 줄이세요"

        # #Shorts 태그 확인
        has_shorts = any("#shorts" in h.lower() for h in hashtags)
        if not has_shorts:
            suggestion = "#Shorts 해시태그를 추가하세요"

        return issue, suggestion

    def _check_narration(self, content) -> Optional[str]:
        """나레이션 검사"""
        narration = getattr(content, 'narration', '') or ''

        if len(narration) < self.MIN_NARRATION_LENGTH:
            return f"나레이션이 너무 짧음 ({len(narration)}자)"

        return None

    def _check_duplicate_text(self, content) -> bool:
        """중복 텍스트 검사"""
        top_text = (getattr(content, 'top_text', '') or '').strip()
        bottom_text = (getattr(content, 'bottom_text', '') or '').strip()

        if top_text and bottom_text and top_text == bottom_text:
            return True

        return False

    def _check_excessive_emoji(self, content) -> bool:
        """이모지 과다 사용 검사"""
        text = self._get_all_text(content)

        # 이모지 패턴
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags
            "]+",
            flags=re.UNICODE
        )

        emojis = emoji_pattern.findall(text)
        total_emoji_count = sum(len(e) for e in emojis)

        # 전체 텍스트의 10% 이상이 이모지면 과다
        if len(text) > 0 and total_emoji_count / len(text) > 0.1:
            return True

        return False

    def _get_all_text(self, content) -> str:
        """콘텐츠의 모든 텍스트 추출"""
        parts = [
            getattr(content, 'meme_text', '') or '',
            getattr(content, 'top_text', '') or '',
            getattr(content, 'bottom_text', '') or '',
            getattr(content, 'narration', '') or '',
        ]

        # 해시태그도 포함
        hashtags = getattr(content, 'hashtags', []) or []
        parts.extend(hashtags)

        return ' '.join(parts)

    def filter_hashtags(self, hashtags: List[str], platform: str = "youtube") -> List[str]:
        """플랫폼별 해시태그 필터링"""
        # 중복 제거
        unique_hashtags = list(dict.fromkeys(hashtags))

        # 플랫폼별 최대 개수
        max_count = {
            "youtube": 15,
            "tiktok": 5,
            "instagram": 30
        }.get(platform, 10)

        # 필수 태그 확인
        required = {"youtube": "#Shorts", "tiktok": "#fyp"}.get(platform)
        if required and required not in unique_hashtags:
            unique_hashtags.insert(0, required)

        return unique_hashtags[:max_count]

    def sanitize_text(self, text: str) -> str:
        """텍스트 정제"""
        if not text:
            return ""

        # 연속 공백 제거
        text = re.sub(r'\s+', ' ', text)

        # 앞뒤 공백 제거
        text = text.strip()

        # 금지 키워드 마스킹
        for keyword in self.BLOCKED_KEYWORDS:
            if keyword.lower() in text.lower():
                text = re.sub(
                    re.escape(keyword),
                    '*' * len(keyword),
                    text,
                    flags=re.IGNORECASE
                )

        return text
