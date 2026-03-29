"""
ET Nexus — Moderator Agent
Synthesizes multiple perspectives into a balanced, personalized summary.
"""

import os
from groq import Groq

class ModeratorAgent:
    """
    The 'Anchor' — balances the debate and creates final consumer-ready output.
    """
    
    def __init__(self, model: str = "llama-3.3-70b-versatile"):
        self.client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        self.model = model

    def synthesize(self, context: dict, bull_view: str, bear_view: str) -> str:
        """
        Synthesizes the debate into a personalized summary.
        """
        query = context.get("query")
        user = context.get("user")
        
        prompt = f"""
ROLE: You are the 'Moderator Agent' for ET Nexus. Your job is to take two conflicting financial perspectives (Bull vs Bear) and synthesize them into a single, balanced, hyper-personalized news briefing.

USER PROFILE:
- Persona: {user['persona']}
- Level: {user['level']} (Adapt your language to this level)
- Portfolio: {user['portfolio']}

DEBATE:
BULL VIEW: {bull_view}
BEAR VIEW: {bear_view}

TASK:
Create a "Balanced Briefing" about '{query}'.
1. Start with a 1-sentence headline-style summary.
2. Provide a 2-para briefing that acknowledges BOTH the opportunities and the risks.
3. Explicitly state the "Actionable Insight" for this specific user based on their portfolio.
4. AVOID generic financial advice (use "consider mapping your risk" instead of "buy stock").
5. Keep it punchy and journalistic.

LIMIT: 200 words.
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6,
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Moderator Agent Synthesis Error: {str(e)}"
