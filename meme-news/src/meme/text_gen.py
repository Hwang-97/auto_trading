"""
밈 텍스트 생성 모듈
"""

from typing import List, Optional, Tuple

from ..utils.logger import get_logger

logger = get_logger(__name__)


class TextGenerator:
    """밈 텍스트를 생성하고 포맷팅하는 클래스"""

    def __init__(self, config_loader):
        self.config_loader = config_loader
        self.prompts = config_loader.load("prompts")

    def format_meme_text(
        self, top_text: str, bottom_text: str, style: str = "impact"
    ) -> dict:
        """밈 텍스트를 포맷팅합니다."""
        styles = {
            "impact": {
                "font": "Impact",
                "size": 48,
                "color": "white",
                "stroke_color": "black",
                "stroke_width": 3,
                "uppercase": True,
            },
            "modern": {
                "font": "Arial Bold",
                "size": 36,
                "color": "white",
                "stroke_color": "black",
                "stroke_width": 2,
                "uppercase": False,
            },
            "korean": {
                "font": "NanumGothic Bold",
                "size": 40,
                "color": "white",
                "stroke_color": "black",
                "stroke_width": 2,
                "uppercase": False,
            },
        }

        style_config = styles.get(style, styles["impact"])

        if style_config.get("uppercase"):
            top_text = top_text.upper()
            bottom_text = bottom_text.upper()

        return {
            "top_text": top_text,
            "bottom_text": bottom_text,
            "style": style_config,
        }

    def parse_meme_response(self, ai_response: str) -> Tuple[str, str]:
        """AI 응답에서 상단/하단 텍스트를 추출합니다."""
        lines = ai_response.strip().split("\n")
        top_text = ""
        bottom_text = ""

        for line in lines:
            line_lower = line.lower()
            if "상단" in line_lower or "top" in line_lower:
                # 콜론 이후의 텍스트 추출
                if ":" in line:
                    top_text = line.split(":", 1)[1].strip()
            elif "하단" in line_lower or "bottom" in line_lower:
                if ":" in line:
                    bottom_text = line.split(":", 1)[1].strip()

        # 파싱 실패 시 전체 텍스트 사용
        if not top_text and not bottom_text:
            if len(lines) >= 2:
                top_text = lines[0].strip()
                bottom_text = lines[-1].strip()
            else:
                top_text = ai_response.strip()

        return top_text, bottom_text

    def generate_caption(
        self, news_title: str, platform: str = "youtube"
    ) -> str:
        """플랫폼에 맞는 캡션을 생성합니다."""
        platforms_config = self.config_loader.load("platforms")
        platform_config = platforms_config.get("platforms", {}).get(platform, {})

        max_length = platform_config.get("caption_max_length", 2200)

        # 기본 캡션 생성
        caption = f"{news_title}\n\n"

        # 설명 템플릿 추가 (유튜브)
        if platform == "youtube":
            description_template = platform_config.get("description_template", "")
            if description_template:
                caption = description_template.format(title=news_title)

        # 길이 제한
        if len(caption) > max_length:
            caption = caption[:max_length - 3] + "..."

        return caption

    def generate_title(
        self, news_items: List, style: str = "clickbait"
    ) -> str:
        """영상 제목을 생성합니다."""
        if not news_items:
            return "오늘의 밈 뉴스"

        main_news = news_items[0] if news_items else None

        if style == "clickbait":
            templates = [
                "충격! {topic}... 결국 이렇게 됐습니다",
                "{topic} 알고보니 대반전",
                "레전드 {topic} 총정리",
                "실화냐? {topic}",
            ]
        elif style == "informative":
            templates = [
                "[오늘의 뉴스] {topic}",
                "{topic} - 핵심 요약",
                "{topic}, 무슨 일?",
            ]
        else:
            templates = ["{topic}"]

        import random
        template = random.choice(templates)

        topic = main_news.title[:30] if main_news else "오늘의 이슈"
        return template.format(topic=topic)

    def wrap_text(self, text: str, max_width: int = 20) -> List[str]:
        """텍스트를 지정된 너비로 줄바꿈합니다."""
        words = text.split()
        lines = []
        current_line = []
        current_length = 0

        for word in words:
            word_length = len(word)
            if current_length + word_length + len(current_line) <= max_width:
                current_line.append(word)
                current_length += word_length
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
                current_length = word_length

        if current_line:
            lines.append(" ".join(current_line))

        return lines
