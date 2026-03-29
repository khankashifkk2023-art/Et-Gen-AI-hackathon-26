"""
ET Nexus — Standalone Retrieval Engine
Performs semantic search with metadata filtering.
Adapted from Data Layer codebase, using existing ETNexusVectorStore.
"""

import logging
import time
from typing import List, Dict, Optional

from models.schemas import SearchResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("retriever")


class RetrievalEngine:
    """
    Standalone retrieval engine wrapping ETNexusVectorStore.search().
    
    Features:
    - Semantic search using dense vectors
    - Metadata filtering (tags, date ranges)
    - Sub-50ms search latency target
    - Hybrid search readiness (BM25 placeholder)
    - Returns results in SearchResult Pydantic format
    """
    
    def __init__(self, vector_store):
        """
        Initialize RetrievalEngine with an ETNexusVectorStore instance.
        
        Args:
            vector_store: An initialized ETNexusVectorStore
        """
        self.vector_store = vector_store
        logger.info("RetrievalEngine initialized")
    
    def search(
        self,
        query: str,
        limit: int = 5,
        ticker_filter: Optional[str] = None,
        filters: Optional[Dict] = None
    ) -> List[SearchResult]:
        """
        Semantic search with optional metadata filtering.
        
        Args:
            query: Natural language search query
            limit: Maximum results to return
            ticker_filter: Filter by stock ticker tag
            filters: Additional filters dict (e.g., {"tags": "TATAMOTORS"})
            
        Returns:
            List of SearchResult Pydantic models
        """
        if not query:
            logger.warning("Empty query provided")
            return []
        
        start_time = time.time()
        
        # Resolve ticker filter from either parameter
        effective_ticker = ticker_filter
        if filters and "tags" in filters:
            effective_ticker = filters["tags"]
        
        # Delegate to vector store
        results = self.vector_store.search(
            query=query,
            limit=limit,
            ticker_filter=effective_ticker
        )
        
        latency_ms = (time.time() - start_time) * 1000
        logger.info(f"🔍 Search completed in {latency_ms:.2f}ms ({len(results)} results)")
        
        if latency_ms > 50:
            logger.warning(f"⚠️ Search latency {latency_ms:.2f}ms exceeds 50ms target")
        
        return results
    
    def hybrid_search(
        self,
        query: str,
        limit: int = 5,
        ticker_filter: Optional[str] = None,
        dense_weight: float = 0.7
    ) -> List[SearchResult]:
        """
        Hybrid search combining dense vectors and BM25 sparse search.
        
        Note: BM25 is a placeholder — falls back to semantic search.
        Qdrant supports hybrid search but requires sparse vector setup.
        
        Args:
            query: Natural language search query
            limit: Maximum results to return
            ticker_filter: Filter by stock ticker tag
            dense_weight: Weight for dense vector score (0-1)
            
        Returns:
            List of SearchResult Pydantic models
        """
        logger.info(f"🔀 Hybrid search requested (dense_weight={dense_weight})")
        logger.info("   Note: Falling back to semantic search (BM25 not yet configured)")
        
        return self.search(query, limit, ticker_filter)
    
    def search_for_context(
        self,
        query: str,
        limit: int = 5,
        ticker_filter: Optional[str] = None
    ) -> List[Dict]:
        """
        Search and return results in the dict format expected by the ContextEngine.
        
        Returns:
            List of dicts: {"document": str, "metadata": dict, "score": float}
        """
        results = self.search(query, limit, ticker_filter)
        
        context_results = []
        for r in results:
            context_results.append({
                "document": r.rag_text,
                "metadata": {
                    "title": r.title,
                    "date": r.date,
                    "tags": r.tags,
                    "image_url": r.image_url or "",
                    "url": r.url,
                },
                "score": r.score or 0.0
            })
        
        return context_results
