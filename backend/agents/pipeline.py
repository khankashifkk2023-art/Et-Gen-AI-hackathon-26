import asyncio
import time
import random
from typing import Optional
from models.schemas import UserProfile
from agents.context_engine import ContextEngine
from agents.bull_agent import BullAgent
from agents.bear_agent import BearAgent
from agents.moderator_agent import ModeratorAgent
from ingestion.vector_store import ETNexusVectorStore
from ui_engine.ui_logic import UIEngine
from guardrails.safety import SafetyGuardrails

def call_llm_with_retry(func, *args, max_retries=3, **kwargs):
    """Exponential backoff retry wrapper for agent calls."""
    for i in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if i == max_retries - 1:
                raise e
            wait_time = (2 ** i) + random.random()
            print(f"⚠️ Agent call failed, retrying in {wait_time:.2f}s... (Attempt {i+1}/{max_retries})")
            time.sleep(wait_time)
            
class AgenticPipeline:
    def __init__(self, vector_store: ETNexusVectorStore):
        self.context_engine = ContextEngine(vector_store)
        self.bull_agent = BullAgent()
        self.bear_agent = BearAgent()
        self.moderator_agent = ModeratorAgent()
        self.ui_engine = UIEngine()
        self.safety = SafetyGuardrails()

    async def run_analysis(
        self, 
        query: str, 
        user_profile: UserProfile,
        ticker_filter: Optional[str] = None
    ) -> dict:
        context = self.context_engine.build_context(
            query=query, 
            user_profile=user_profile,
            ticker_filter=ticker_filter
        )
        
        # Synchronous execution with retry safety (to_thread used in original but simplified here)
        bull_view = call_llm_with_retry(self.bull_agent.analyze, context)
        bear_view = call_llm_with_retry(self.bear_agent.analyze, context)

        synthesis = call_llm_with_retry(
            self.moderator_agent.synthesize, 
            context, 
            bull_view, 
            bear_view
        )
        
        # --- Logic Handling ---
        
        # 1. Guardrails
        clean_summary, confidence = self.safety.process_output(synthesis)
        
        # 2. Portfolio Impact Scoring
        impact_score = "MEDIUM"
        user_portfolio = user_profile.portfolio if hasattr(user_profile, 'portfolio') else []
        if any(stock.upper() in query.upper() for stock in user_portfolio):
            impact_score = "HIGH"
            
        # 3. Sentiment & UI Component
        sentiment = 0.0
        if "bullish" in bull_view.lower() or "growth" in bull_view.lower():
            sentiment += 0.5
        if "bearish" in bear_view.lower() or "risk" in bear_view.lower():
            sentiment -= 0.5

        component = "DefaultView"
        if "stock" in query.lower() or "price" in query.lower():
            component = "StockImpactChart"
        elif sentiment > 0.4:
            component = "BullishTrendChart"
        elif sentiment < -0.4:
            component = "BearishAlertChart"
            
        return {
            "summary": clean_summary,
            "headline": synthesis.split("\n")[0].strip("# ").strip("**"),
            "bull_view": bull_view,
            "bear_view": bear_view,
            "sources": context.get("raw_results", []),
            "component": component,
            "confidence": confidence,
            "ui_metadata": {
                "bull": bull_view[:250] + "...",
                "bear": bear_view[:250] + "...",
                "impact_score": impact_score,
                "disclaimer": self.safety.DISCLAIMER
            }
        }
