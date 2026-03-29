"""
Pydantic models for ET Nexus data structures.
Shared across ingestion, agents, and API layers.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ─── User & Portfolio ───────────────────────────────────────────

class UserProfile(BaseModel):
    """Represents a reader's profile for personalization."""
    user_id: str = Field(..., description="Unique user identifier")
    name: str = Field(default="Demo User")
    persona: str = Field(
        default="retail_investor",
        description="One of: student, retail_investor, fund_manager, startup_founder"
    )
    level: str = Field(
        default="beginner",
        description="Content complexity: beginner, intermediate, expert"
    )
    portfolio: list[str] = Field(
        default_factory=list,
        description="List of stock tickers the user holds, e.g. ['TATAMOTORS', 'HDFCBANK']"
    )
    interests: list[str] = Field(
        default_factory=lambda: ["markets", "technology"],
        description="Topic interests for feed personalization"
    )


# ─── Articles & Chunks ─────────────────────────────────────────

class ScrapedArticle(BaseModel):
    """Raw article fetched from RSS/scraper before processing."""
    article_id: str
    title: str
    date: str = Field(default="Recent")
    body: str = Field(..., min_length=50)
    image_url: Optional[str] = None
    url: str
    tags: list[str] = Field(default_factory=lambda: ["ET News"])
    source: str = Field(default="Economic Times")


class ProcessedArticle(BaseModel):
    """Article after preprocessing (clean text, normalized date)."""
    article_id: str
    title: str
    clean_body: str
    normalized_date: str  # ISO format YYYY-MM-DD
    image_url: Optional[str] = None
    url: str
    tags: list[str] = Field(default_factory=list)
    source: str = Field(default="Economic Times")


class ArticleChunk(BaseModel):
    """A single chunk of an article, ready for embedding."""
    chunk_id: str
    text: str
    metadata: dict = Field(default_factory=dict)


# ─── API Request / Response ────────────────────────────────────

class SearchRequest(BaseModel):
    """Request body for the /search endpoint."""
    query: str = Field(..., description="Natural language search query")
    limit: int = Field(default=3, ge=1, le=10)
    ticker_filter: Optional[str] = Field(
        default=None,
        description="Filter results to a specific stock ticker"
    )


class SearchResult(BaseModel):
    """A single search result from the vector database."""
    rag_text: str = Field(..., description="The text chunk for the LLM context")
    title: str
    date: str
    image_url: Optional[str] = None
    url: str
    tags: list[str] = Field(default_factory=list)
    score: Optional[float] = None


class SearchResponse(BaseModel):
    """Response from the /search endpoint."""
    results: list[SearchResult]
    query: str
    total_results: int


class IngestRequest(BaseModel):
    """Request body for the /ingest endpoint."""
    rss_feeds: list[str] = Field(
        default_factory=lambda: [
            "https://economictimes.indiatimes.com/rssfeeds/1221656.cms",   # Top Stories
            "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",  # Markets
            "https://economictimes.indiatimes.com/tech/rssfeeds/13357270.cms",  # Tech
        ]
    )
    limit_per_feed: int = Field(default=5, ge=1, le=20)


class IngestResponse(BaseModel):
    """Response from the /ingest endpoint."""
    status: str
    articles_scraped: int
    chunks_stored: int
    errors: list[str] = Field(default_factory=list)


class AnalysisRequest(BaseModel):
    """Request body for the /analyze endpoint (Phase 2+)."""
    query: str = Field(..., description="The article topic or user question")
    user_profile: UserProfile = Field(default_factory=UserProfile)
    article_url: Optional[str] = Field(
        default=None,
        description="Specific article URL to analyze"
    )


class AnalysisResponse(BaseModel):
    """Full response from the /analyze endpoint (Phase 2+)."""
    headline: str
    summary: str
    component: str = Field(default="DefaultView")
    impact: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    ui_metadata: dict = Field(default_factory=dict)
    sources: list[SearchResult] = Field(default_factory=list)
    disclaimer: Optional[str] = None


# ─── Video Studio ──────────────────────────────────────────────

class Scene(BaseModel):
    """A single scene in the video storyboard."""
    scene_id: int
    narration: str
    search_keyword: str
    overlay_text: str
    composition: str = Field(default="LOWER_THIRD")
    broll_url: Optional[str] = None
    start_frame: int = Field(default=0)
    end_frame: int = Field(default=0)


class VideoRequest(BaseModel):
    """Request body for the /video/generate endpoint."""
    article_title: str
    summary: str
    bull_view: str
    bear_view: str


class CaptionWord(BaseModel):
    """Single timed caption for Remotion (30fps frame ranges)."""
    text: str
    start_frame: int
    end_frame: int


class VideoResponse(BaseModel):
    """Response from the /video/generate endpoint."""
    job_id: str
    script: list[Scene]
    audio_url: str
    subtitles_url: str
    total_frames: int = Field(default=0)
    status: str = Field(default="ready")
    caption_words: list[CaptionWord] = Field(
        default_factory=list,
        description="Pre-parsed word-level captions synced to audio (no client-side VTT fetch).",
    )
