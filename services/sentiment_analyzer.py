import os
import aiohttp
import asyncio
import logging
from typing import Optional, List, Dict, Any
import json

logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    """
    Sentiment analysis service using OpenRouter API for Reddit posts and comments.
    
    Provides sentiment analysis capabilities with scores ranging from -1 (negative) 
    to +1 (positive), with 0 being neutral.
    """
    
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1"
        self.model = "anthropic/claude-3-haiku:beta"  # Fast, cost-effective model
        self.session = None
        
        if not self.api_key:
            logger.warning("OpenRouter API key not found. Sentiment analysis will be disabled.")
    
    async def __aenter__(self):
        """Async context manager entry"""
        if self.api_key:
            self.session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def is_available(self) -> bool:
        """Check if sentiment analysis is available (API key configured)"""
        return self.api_key is not None
    
    async def analyze_text(self, text: str) -> Optional[float]:
        """
        Analyze sentiment of a single text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Sentiment score from -1 (negative) to +1 (positive), or None if unavailable
        """
        if not self.is_available() or not self.session or not text.strip():
            return None
        
        # Clean and truncate text for analysis
        cleaned_text = self._clean_text(text)
        if len(cleaned_text) < 10:  # Skip very short texts
            return 0.0
        
        prompt = f"""Analyze the sentiment of this Reddit text and respond with only a decimal number between -1 and 1:
- -1 = very negative
- -0.5 = moderately negative  
- 0 = neutral
- 0.5 = moderately positive
- 1 = very positive

Text: "{cleaned_text}"

Response (number only):"""

        try:
            async with self.session.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 10,
                    "temperature": 0.1
                }
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                    
                    # Parse the sentiment score
                    try:
                        score = float(content)
                        # Clamp to valid range
                        return max(-1.0, min(1.0, score))
                    except ValueError:
                        logger.warning(f"Invalid sentiment score format: {content}")
                        return None
                else:
                    logger.error(f"OpenRouter API error: {response.status} - {await response.text()}")
                    return None
                    
        except asyncio.TimeoutError:
            logger.warning("Sentiment analysis timeout")
            return None
        except Exception as e:
            logger.error(f"Sentiment analysis error: {e}")
            return None
    
    async def analyze_batch(self, texts: List[str], batch_size: int = 5) -> List[Optional[float]]:
        """
        Analyze sentiment of multiple texts in batches to avoid rate limits.
        
        Args:
            texts: List of texts to analyze
            batch_size: Number of texts to process simultaneously
            
        Returns:
            List of sentiment scores corresponding to input texts
        """
        if not self.is_available():
            return [None] * len(texts)
        
        results = []
        
        # Process in batches to respect rate limits
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # Process batch concurrently
            batch_tasks = [self.analyze_text(text) for text in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Handle any exceptions in the batch
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch sentiment analysis error: {result}")
                    results.append(None)
                else:
                    results.append(result)
            
            # Small delay between batches to be respectful to the API
            if i + batch_size < len(texts):
                await asyncio.sleep(0.5)
        
        return results
    
    def _clean_text(self, text: str) -> str:
        """
        Clean text for sentiment analysis by removing markdown, URLs, etc.
        
        Args:
            text: Raw text to clean
            
        Returns:
            Cleaned text suitable for sentiment analysis
        """
        if not text:
            return ""
        
        # Remove markdown formatting
        import re
        
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove Reddit formatting
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # [text](url) -> text
        text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)  # **bold** -> bold
        text = re.sub(r'\*([^\*]+)\*', r'\1', text)  # *italic* -> italic
        text = re.sub(r'`([^`]+)`', r'\1', text)  # `code` -> code
        text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)  # ## headers
        text = re.sub(r'^&gt;\s*', '', text, flags=re.MULTILINE)  # > quotes
        
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)  # Multiple newlines
        text = re.sub(r'\s+', ' ', text)  # Multiple spaces
        
        # Truncate if too long (OpenRouter has token limits)
        if len(text) > 2000:
            text = text[:2000] + "..."
        
        return text.strip()
    
    def get_sentiment_label(self, score: Optional[float]) -> str:
        """
        Convert sentiment score to human-readable label.
        
        Args:
            score: Sentiment score from -1 to 1
            
        Returns:
            Human-readable sentiment label
        """
        if score is None:
            return "unknown"
        elif score <= -0.6:
            return "very negative"
        elif score <= -0.2:
            return "negative"
        elif score < 0.2:
            return "neutral"
        elif score < 0.6:
            return "positive"
        else:
            return "very positive"
    
    def get_sentiment_stats(self, scores: List[Optional[float]]) -> Dict[str, Any]:
        """
        Calculate sentiment statistics for a collection of scores.
        
        Args:
            scores: List of sentiment scores
            
        Returns:
            Dictionary with sentiment statistics
        """
        valid_scores = [s for s in scores if s is not None]
        
        if not valid_scores:
            return {
                "total_analyzed": 0,
                "average_sentiment": None,
                "sentiment_distribution": {
                    "very negative": 0,
                    "negative": 0,
                    "neutral": 0,
                    "positive": 0,
                    "very positive": 0
                }
            }
        
        # Calculate distribution
        distribution = {
            "very negative": 0,
            "negative": 0,
            "neutral": 0,
            "positive": 0,
            "very positive": 0
        }
        
        for score in valid_scores:
            label = self.get_sentiment_label(score)
            distribution[label] += 1
        
        return {
            "total_analyzed": len(valid_scores),
            "average_sentiment": sum(valid_scores) / len(valid_scores),
            "sentiment_distribution": distribution,
            "positive_ratio": len([s for s in valid_scores if s > 0.2]) / len(valid_scores),
            "negative_ratio": len([s for s in valid_scores if s < -0.2]) / len(valid_scores),
            "neutral_ratio": len([s for s in valid_scores if -0.2 <= s <= 0.2]) / len(valid_scores)
        }

# Global instance for easy access
sentiment_analyzer = SentimentAnalyzer()