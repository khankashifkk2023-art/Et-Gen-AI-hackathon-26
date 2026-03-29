"""
ET Nexus — Bear Agent
Provides a cautious, risk-focused analysis of the news.
"""

import os
from groq import Groq

class BearAgent:
    """
    The 'Realist/Skeptic' — focuses on risks, downsides, and cautionary tales.
    """
    
    def __init__(self, model: str = "llama-3.3-70b-versatile"):
        self.client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        self.model = model

    def analyze(self, context: dict) -> str:
        """
        Generates a bearish perspective based on the context.
        """
        query = context.get("query")
        news = context.get("formatted_news")
        user = context.get("user")
        
        prompt = f"""
ROLE: You are the 'Bear Agent', a senior risk manager known for identifying pitfalls, economic headwinds, and market vulnerabilities.

USER CONTEXT:
- Persona: {user['persona']}
- Expertise: {user['level']}
- Portfolio: {user['portfolio']}

NEWS DATA:
{news}

TASK:
Analyze the news above regarding '{query}' from a strictly BEARISH (cautious/skeptical) perspective.
Highlight:
1. Potential risks, negative catalysts, or economic headwinds.
2. Why this could be detrimental to specific sectors or the broader market.
3. If any companies in the user's portfolio are at risk, highlight exactly why.
4. Keep the tone professional, objective, and cautious.

LIMIT: 150 words.
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=300
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Bear Agent Analysis Error: {str(e)}"
