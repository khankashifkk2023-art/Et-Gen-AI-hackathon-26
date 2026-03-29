"""
ET Nexus — Generative UI Logic
Map analysis sentiment and context to specific React components.
"""

from typing import Optional
from models.schemas import AnalysisResponse, SearchResult

class UIEngine:
    """
    Decides what UI components should be rendered on the frontend.
    """
    
    ALLOWED_COMPONENTS = {
        "BearishAlertChart",
        "BullishTrendChart",
        "StockImpactChart",
        "TimelineView",
        "DefaultView"
    }

    def determine_component(
        self, 
        summary: str, 
        sentiment_score: float, 
        ticker: Optional[str],
        user_portfolio: list[str],
        sources: list[SearchResult]
    ) -> str:
        """
        Logic for selecting the visual component.
        """
        # 1. Portfolio specific impact
        if ticker and ticker in user_portfolio:
            if sentiment_score < -0.3:
                return "BearishAlertChart"
            return "StockImpactChart"
            
        # 2. Strong sentiment triggers
        if sentiment_score > 0.6:
            return "BullishTrendChart"
        if sentiment_score < -0.6:
            return "BearishAlertChart"
            
        # 3. Complex story over time
        if len(sources) >= 3:
            return "TimelineView"
            
        # 4. Fallback
        return "DefaultView"

    def validate_component(self, component: str) -> str:
        """Ensures the component is in the whitelist."""
        if component in self.ALLOWED_COMPONENTS:
            return component
        return "DefaultView"
