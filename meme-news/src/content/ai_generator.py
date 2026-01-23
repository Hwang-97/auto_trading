"""
AI 콘텐츠 생성 모듈 (Gemini API 사용)

Gemini API를 사용하여 밈 텍스트, 스크립트, 해시태그 등을 생성합니다.
"""

import asyncio
import re
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import google.generativeai as genai

from ..utils.logger import get_logger

if TYPE_CHECKING:
    from ..core.pipeline import MemeContent, NewsItem

logger = get_logger(__name__)


class AIGenerator:
    """Gemini API를 사용한 AI 콘텐츠 생성 클래스"""

    def __init__(self, config_loader):
        """
        AIGenerator를 초기화합니다.

        Args:
            config_loader: ConfigLoader 인스턴스
        """
        self.config_loader = config_loader
        self.prompts = config_loader.load("prompts")
        self.model = None
        self._setup_api()

    def _setup_api(self) -> None:
        """Gemini API를 설정합니다."""
        api_key = self.config_loader.get_api_key("gemini")
        if api_key:
            genai.configure(api_key=api_key)
            config = self.config_loader.load("config")
            ai_config = config.get("ai", {}).get("gemini", {})
            model_name = ai_config.get("model", "gemini-1.5-flash")

            # 생성 설정
            generation_config = genai.GenerationConfig(
                temperature=ai_config.get("temperature", 0.8),
                max_output_tokens=ai_config.get("max_tokens", 2048),
            )

            self.model = genai.GenerativeModel(
                model_name,
                generation_config=generation_config
            )
            logger.info(f"Gemini API configured with model: {model_name}")
        else:
            logger.warning("Gemini API key not found")

    async def generate_daily_meme(
        self,
        topic: str,
        style: str = "humorous"
    ) -> Dict[str, Any]:
        """
        일상 주제로 밈 텍스트를 생성합니다.

        Args:
            topic: 주제 (예: "직장생활 - 월요병")
            style: 스타일

        Returns:
            생성된 밈 정보 딕셔너리
        """
        if not self.model:
            logger.error("Gemini model not initialized")
            return self._empty_meme_result()

        prompt_config = self.prompts.get("daily_meme_prompt", {})
        system_prompt = prompt_config.get("system", "")
        user_template = prompt_config.get("user_template", "")

        # 주제에서 키워드 추출
        parts = topic.split(" - ")
        topic_name = parts[0] if parts else topic
        keywords = parts[1] if len(parts) > 1 else topic_name

        user_prompt = user_template.format(
            topic=topic_name,
            keywords=keywords
        )

        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                f"{system_prompt}\n\n{user_prompt}"
            )
            return self._parse_meme_response(response.text)
        except Exception as e:
            logger.error(f"Error generating daily meme: {e}")
            return self._empty_meme_result()

    async def generate_news_meme(
        self,
        news_item: Optional["NewsItem"],
        style: str = "witty"
    ) -> Dict[str, Any]:
        """
        뉴스를 기반으로 밈 텍스트를 생성합니다.

        Args:
            news_item: 뉴스 아이템
            style: 스타일

        Returns:
            생성된 밈 정보 딕셔너리
        """
        if not self.model or not news_item:
            return self._empty_meme_result()

        prompt_config = self.prompts.get("news_meme_prompt", {})
        system_prompt = prompt_config.get("system", "")
        user_template = prompt_config.get("user_template", "")

        user_prompt = user_template.format(
            title=news_item.title,
            summary=news_item.content[:500],
            category=news_item.category
        )

        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                f"{system_prompt}\n\n{user_prompt}"
            )
            return self._parse_meme_response(response.text)
        except Exception as e:
            logger.error(f"Error generating news meme: {e}")
            return self._empty_meme_result()

    async def generate_trend_meme(
        self,
        keyword: str,
        context: str = "",
        popularity: str = "높음"
    ) -> Dict[str, Any]:
        """
        트렌드 키워드로 밈 텍스트를 생성합니다.

        Args:
            keyword: 트렌드 키워드
            context: 관련 맥락
            popularity: 인기도

        Returns:
            생성된 밈 정보 딕셔너리
        """
        if not self.model:
            return self._empty_meme_result()

        prompt_config = self.prompts.get("trend_meme_prompt", {})
        system_prompt = prompt_config.get("system", "")
        user_template = prompt_config.get("user_template", "")

        user_prompt = user_template.format(
            keyword=keyword,
            context=context or "실시간 트렌드",
            popularity=popularity
        )

        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                f"{system_prompt}\n\n{user_prompt}"
            )
            return self._parse_meme_response(response.text)
        except Exception as e:
            logger.error(f"Error generating trend meme: {e}")
            return self._empty_meme_result()

    async def generate_script(
        self,
        content: "MemeContent",
        duration: int = 30
    ) -> str:
        """
        영상 스크립트를 생성합니다.

        Args:
            content: MemeContent 객체
            duration: 목표 영상 길이 (초)

        Returns:
            생성된 스크립트
        """
        if not self.model:
            return content.narration or content.meme_text

        prompt_config = self.prompts.get("script_prompt", {})
        system_prompt = prompt_config.get("system", "")
        user_template = prompt_config.get("user_template", "")

        meme_content = f"상단: {content.top_text}\n하단: {content.bottom_text}"
        if content.narration:
            meme_content += f"\n나레이션: {content.narration}"

        user_prompt = user_template.format(
            meme_content=meme_content,
            duration=duration
        )

        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                f"{system_prompt}\n\n{user_prompt}"
            )
            return response.text
        except Exception as e:
            logger.error(f"Error generating script: {e}")
            return content.narration or content.meme_text

    async def generate_meme_text(
        self,
        news_summaries: List[str],
        style: str = "humorous"
    ) -> str:
        """
        뉴스 요약을 기반으로 밈 텍스트를 생성합니다 (레거시 호환).

        Args:
            news_summaries: 뉴스 요약 목록
            style: 스타일

        Returns:
            생성된 밈 텍스트
        """
        if not self.model:
            return ""

        news_text = "\n".join([f"- {summary}" for summary in news_summaries])

        prompt = f"""
다음 뉴스를 기반으로 재미있는 밈 텍스트를 만들어주세요.
모든 문장은 15자 이내로 작성해주세요.

뉴스:
{news_text}

형식:
상단 텍스트: (상황 설명)
하단 텍스트: (반응/펀치라인)
"""

        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )
            return response.text
        except Exception as e:
            logger.error(f"Error generating meme text: {e}")
            return ""

    async def generate_hashtags(
        self,
        content_summary: str,
        platform: str = "youtube",
        max_count: int = 10
    ) -> List[str]:
        """
        해시태그를 생성합니다.

        Args:
            content_summary: 콘텐츠 요약
            platform: 플랫폼
            max_count: 최대 개수

        Returns:
            해시태그 목록
        """
        if not self.model:
            return []

        prompt_config = self.prompts.get("hashtag_prompt", {})
        user_template = prompt_config.get("user_template", "")

        if not user_template:
            user_template = """
콘텐츠 주제: {topic}
플랫폼: {platform}
최대 개수: {max_count}

해시태그를 생성해주세요.
"""

        user_prompt = user_template.format(
            topic=content_summary,
            platform=platform,
            max_count=max_count
        )

        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                user_prompt
            )
            # 응답에서 해시태그 추출
            text = response.text
            hashtags = re.findall(r"#[\w가-힣]+", text)
            return hashtags[:max_count]
        except Exception as e:
            logger.error(f"Error generating hashtags: {e}")
            return []

    def _parse_meme_response(self, response_text: str) -> Dict[str, Any]:
        """
        AI 응답을 파싱하여 밈 정보를 추출합니다.

        Args:
            response_text: AI 응답 텍스트

        Returns:
            파싱된 밈 정보 딕셔너리
        """
        result = self._empty_meme_result()
        result["meme_text"] = response_text

        lines = response_text.strip().split("\n")

        for line in lines:
            line_lower = line.lower()
            line_clean = line.strip()

            # 상단 텍스트 / 텍스트1
            if any(k in line_lower for k in ["상단", "텍스트1", "top"]):
                if ":" in line_clean:
                    result["top_text"] = line_clean.split(":", 1)[1].strip()

            # 하단 텍스트 / 텍스트2
            elif any(k in line_lower for k in ["하단", "텍스트2", "bottom"]):
                if ":" in line_clean:
                    result["bottom_text"] = line_clean.split(":", 1)[1].strip()

            # 나레이션
            elif "나레이션" in line_lower or "narration" in line_lower:
                if ":" in line_clean:
                    result["narration"] = line_clean.split(":", 1)[1].strip()

            # 해시태그
            elif "해시태그" in line_lower or "hashtag" in line_lower:
                if ":" in line_clean:
                    tag_text = line_clean.split(":", 1)[1].strip()
                    hashtags = re.findall(r"#[\w가-힣]+", tag_text)
                    result["hashtags"] = hashtags

        # top_text와 bottom_text가 없으면 첫 두 줄 사용
        if not result["top_text"] and not result["bottom_text"]:
            content_lines = [l.strip() for l in lines if l.strip() and not l.startswith("#")]
            if len(content_lines) >= 2:
                result["top_text"] = content_lines[0][:50]
                result["bottom_text"] = content_lines[1][:50]
            elif content_lines:
                result["top_text"] = content_lines[0][:50]

        return result

    def _empty_meme_result(self) -> Dict[str, Any]:
        """빈 밈 결과를 반환합니다."""
        return {
            "meme_text": "",
            "top_text": "",
            "bottom_text": "",
            "narration": "",
            "hashtags": [],
        }
