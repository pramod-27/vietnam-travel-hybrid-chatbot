# services/chat_service.py
"""
Chat Service - OpenRouter with Google Embeddings
100% Clean logging - no emojis, no unicode
"""
import os
import sys
from typing import List, Dict, Optional
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from config import Config
from utils.logger import logger

try:
    from openai import OpenAI
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
except ImportError as e:
    raise ImportError("Missing packages. Run: pip install openai tenacity")


class ChatService:
    """Chat service using OpenRouter"""

    def __init__(self):
        self.client = None
        self.model = None
        self.provider = None
        
        self._init_openrouter()
        
        if not self.provider:
            raise RuntimeError(
                "OpenRouter initialization failed.\n"
                "Check OPENROUTER_API_KEY in .env"
            )

    def _init_openrouter(self):
        """Initialize OpenRouter"""
        if not Config.OPENROUTER_API_KEY:
            logger.error("OPENROUTER_API_KEY not found")
            return
        
        try:
            self.client = OpenAI(
                api_key=Config.OPENROUTER_API_KEY,
                base_url=Config.OPENROUTER_BASE_URL,
                timeout=60.0,
                max_retries=2
            )
            self.model = Config.OPENROUTER_CHAT_MODEL
            self.provider = "openrouter"
            
            # Test connection silently
            test_resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            
            #logger.info(f"ChatService ready - OpenRouter ({self.model})")
            
        except Exception as e:
            logger.error(f"OpenRouter failed: {e}")
            raise

    def _build_system_prompt(self) -> str:
        """System prompt for Vietnam travel"""
        return """You are an expert Vietnam travel consultant with deep knowledge of Vietnamese culture, geography, cuisine, and tourism.

Your expertise:
- Creating detailed, romantic, culturally authentic itineraries
- Providing practical logistics (timing, transport, costs)
- Recommending authentic experiences and hidden gems
- Understanding seasonal patterns and festivals
- Suggesting romantic spots for couples
- Advising on customs, etiquette, and safety

When creating itineraries:
1. Day-by-day structure with morning/afternoon/evening
2. Realistic travel times between locations
3. Specific romantic experiences and photo spots
4. Optimal visiting times and crowd expectations
5. Practical tips: what to bring, dress codes, costs
6. Local food and dining recommendations
7. Balanced pace (no over-scheduling)
8. Cultural insights and customs

Response style:
- Warm, enthusiastic, personal
- Specific details from context
- Actionable recommendations
- Balance romance with practicality

Use retrieved context about places, hotels, activities to craft authentic recommendations."""

    def _build_context_message(self, context: List[Dict]) -> str:
        """Build context from vector + graph results"""
        if not context:
            return "[No context retrieved]"

        parts = []
        
        for i, item in enumerate(context[:8], 1):
            meta = item.get("metadata", {}) or {}
            
            name = meta.get("name", "Unknown")
            typ = meta.get("type", "Place")
            city = meta.get("city", meta.get("region", ""))
            desc = meta.get("description", "")[:500]
            tags = meta.get("tags", [])
            best_time = meta.get("best_time_to_visit", "")
            score = item.get("score", 0)
            
            lines = [
                f"[{i}] {name} ({typ})",
                f"Location: {city}" if city else "",
                f"Relevance: {score:.3f}",
                f"Tags: {', '.join(tags[:6])}" if tags else "",
                f"Best Time: {best_time}" if best_time else "",
                f"\n{desc}" if desc else "",
            ]
            
            # Graph connections
            graph_ctx = item.get("graph_context", {})
            if graph_ctx:
                related = graph_ctx.get("related_nodes", [])[:4]
                if related:
                    nearby = [f"{n.get('name')} ({n.get('type','')})" 
                             for n in related if n.get('name')]
                    if nearby:
                        lines.append(f"Nearby: {', '.join(nearby)}")
            
            parts.append("\n".join([l for l in lines if l]))
        
        return "\n\n" + ("-" * 80) + "\n\n".join(parts)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError))
    )
    def _call_api(self, messages: List[Dict], max_tokens: int, temperature: float) -> str:
        """Call OpenRouter with retry"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response.choices[0].message.content.strip()

    def generate_response(
        self,
        query: str,
        context: List[Dict],
        conversation_history: Optional[List[Dict]] = None,
        max_tokens: int = 1500,
        temperature: float = 0.7
    ) -> str:
        """Generate chat response"""
        
        try:
            messages = [
                {"role": "system", "content": self._build_system_prompt()}
            ]
            
            if conversation_history:
                messages.extend(conversation_history[-6:])
            
            context_text = self._build_context_message(context)
            messages.append({
                "role": "system",
                "content": f"**Database Context:**\n{context_text}\n\nUse this to answer."
            })
            
            messages.append({"role": "user", "content": query})

            #logger.info(f"Generating response (model: {self.model}, context: {len(context)} items)")
            
            answer = self._call_api(messages, max_tokens, temperature)
            
            #logger.info(f"Response complete ({len(answer)} chars)")
            return answer

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise RuntimeError(f"Failed to generate response: {e}")

    def get_provider_info(self) -> Dict[str, str]:
        """Get provider info"""
        return {
            "provider": self.provider,
            "model": self.model,
            "status": "active"
        }