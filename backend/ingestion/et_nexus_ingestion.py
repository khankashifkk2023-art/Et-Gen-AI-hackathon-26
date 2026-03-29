"""
ET Nexus — Knowledge Base Integration Wrapper (Phase 6)
Unified interface connecting: DataCollector → Preprocessor → Chunker → VectorStore → Retriever
This is the single entry point for all data operations.
"""

import asyncio
import logging
from typing import List, Dict, Optional

from models.schemas import ScrapedArticle, SearchResult
from ingestion.data_collector import DataCollector, ET_RSS_FEEDS
from ingestion.scraper import fetch_articles
from ingestion.preprocessor import preprocess_batch, reset_dedup_cache
from ingestion.chunker import ArticleChunker
from ingestion.vector_store import ETNexusVectorStore
from ingestion.retriever import RetrievalEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("knowledge_base")


# ─── Singleton Instance ────────────────────────────────────────
_knowledge_base_instance: Optional["ETNexusKnowledgeBase"] = None


class ETNexusKnowledgeBase:
    """
    Unified integration wrapper for the ET Nexus data pipeline.
    
    Provides a single interface for:
    - Ingesting articles from live RSS feeds or fallback dataset
    - Searching the vector store with semantic + metadata filtering
    - Managing the knowledge base lifecycle
    
    Implements lazy initialization to keep the dev-server startup fast.
    """
    
    def __init__(self):
        """Initialize with lazy-loaded components."""
        self._vector_store: Optional[ETNexusVectorStore] = None
        self._chunker: Optional[ArticleChunker] = None
        self._retriever: Optional[RetrievalEngine] = None
        self._collector: Optional[DataCollector] = None
        self._initialized = False
        logger.info("ETNexusKnowledgeBase configured (lazy initialization)")
    
    def _ensure_initialized(self):
        """Lazy initialization of all components."""
        if self._initialized:
            return
        
        logger.info("🔄 Initializing ETNexusKnowledgeBase...")
        
        self._vector_store = ETNexusVectorStore()
        self._chunker = ArticleChunker()
        self._retriever = RetrievalEngine(self._vector_store)
        self._collector = DataCollector()
        
        self._initialized = True
        logger.info("✅ ETNexusKnowledgeBase initialized")
    
    @property
    def vector_store(self) -> ETNexusVectorStore:
        """Get the vector store instance."""
        self._ensure_initialized()
        return self._vector_store
    
    @property
    def retriever(self) -> RetrievalEngine:
        """Get the retriever instance."""
        self._ensure_initialized()
        return self._retriever
    
    @property
    def chunker(self) -> ArticleChunker:
        """Get the chunker instance."""
        self._ensure_initialized()
        return self._chunker
    
    # ─── Core Operations ────────────────────────────────────────
    
    async def ingest_from_sources(
        self,
        rss_feeds: List[str] = None,
        limit_per_feed: int = 5,
        use_fallback: bool = False
    ) -> Dict:
        """
        Full ingestion pipeline: Collect → Preprocess → Chunk → Embed → Store.
        
        Args:
            rss_feeds: List of RSS feed URLs (defaults to ET feeds)
            limit_per_feed: Max articles per feed
            use_fallback: Force use of offline fallback dataset
            
        Returns:
            Dict with ingestion stats
        """
        self._ensure_initialized()
        reset_dedup_cache()  # Clear dedup for fresh run
        
        import time
        start_time = time.time()
        errors = []
        
        try:
            # Step 1: Collect articles
            if use_fallback:
                articles_list, scrape_errors = fetch_articles(use_fallback=True)
                errors.extend(scrape_errors)
            else:
                articles_list = await self._collector.collect_from_rss(
                    rss_feeds=rss_feeds,
                    limit_per_feed=limit_per_feed
                )
            
            if not articles_list:
                return {
                    "status": "no_data",
                    "articles_collected": 0,
                    "chunks_stored": 0,
                    "errors": ["No articles could be collected"]
                }
            
            # Step 2: Preprocess (with deduplication)
            processed = preprocess_batch(articles_list)
            
            # Step 3: Chunk
            chunks = self._chunker.chunk_batch(processed)
            
            # Step 4: Embed + Store
            stored_count = self._vector_store.ingest_chunks(chunks)
            
            elapsed = time.time() - start_time
            
            return {
                "status": "success",
                "articles_collected": len(articles_list),
                "articles_processed": len(processed),
                "chunks_stored": stored_count,
                "elapsed_seconds": round(elapsed, 2),
                "errors": errors
            }
        
        except Exception as e:
            logger.error(f"❌ Ingestion pipeline failed: {e}")
            return {
                "status": "error",
                "articles_collected": 0,
                "chunks_stored": 0,
                "errors": [str(e)]
            }
    
    def search(
        self,
        query: str,
        limit: int = 5,
        ticker_filter: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Search the knowledge base.
        
        Args:
            query: Natural language search query
            limit: Max results
            ticker_filter: Optional stock ticker filter
            
        Returns:
            List of SearchResult Pydantic models
        """
        self._ensure_initialized()
        return self._retriever.search(query, limit, ticker_filter)
    
    def search_for_context(
        self,
        query: str,
        limit: int = 5,
        ticker_filter: Optional[str] = None
    ) -> List[Dict]:
        """
        Search and return results in ContextEngine dict format.
        
        Returns:
            List of {"document": str, "metadata": dict, "score": float}
        """
        self._ensure_initialized()
        return self._retriever.search_for_context(query, limit, ticker_filter)
    
    def get_collection_info(self) -> Dict:
        """Get vector store collection info."""
        self._ensure_initialized()
        return self._vector_store.get_collection_info()
    
    def reset(self):
        """Clear and recreate the vector store."""
        self._ensure_initialized()
        self._vector_store.clear_collection()
        reset_dedup_cache()
        logger.info("🗑️ Knowledge base reset complete")


def get_knowledge_base() -> ETNexusKnowledgeBase:
    """
    Singleton factory for ETNexusKnowledgeBase.
    Returns the same instance across the application.
    """
    global _knowledge_base_instance
    if _knowledge_base_instance is None:
        _knowledge_base_instance = ETNexusKnowledgeBase()
    return _knowledge_base_instance
