"""
ET Nexus — Bull Agent
Provides an optimistic, opportunity-focused analysis of the news.
"""

import os
from groq import Groq
from models.schemas import UserProfile

class BullAgent:
    """
    The 'Optimist' — focuses on growth, upside, and positive catalysts.
    """
    
    def __init__(self, model: str = "llama-3.3-70b-versatile"):
        self.client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        self.model = model

    def analyze(self, context: dict) -> str:
        """
        Generates a bullish perspective based on the context.
        """
        query = context.get("query")
        news = context.get("formatted_news")
        user = context.get("user")
        
        prompt = f"""
ROLE: You are the 'Bull Agent', a senior financial analyst known for identifying growth opportunities and positive catalysts.

USER CONTEXT:
- Persona: {user['persona']}
- Expertise: {user['level']}
- Portfolio: {user['portfolio']}

NEWS DATA:
{news}

TASK:
Analyze the news above regarding '{query}' from a strictly BULLISH (optimistic) perspective.
Highlight:
1. Growth opportunities and positive market sentiment.
2. Why this is good for the economy or specific sectors.
3. If any companies in the user's portfolio are mentioned or impacted positively, emphasize that.
4. Keep the tone professional but encouraging.

LIMIT: 150 words.
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=300
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Bull Agent Analysis Error: {str(e)}"
