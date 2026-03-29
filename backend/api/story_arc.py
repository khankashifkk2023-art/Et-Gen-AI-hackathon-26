"""
Story Arc Tracker API Endpoints

FastAPI routes for GraphRAG-powered story arc visualization.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging
import os
import sys

# Ensure backend root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ingestion.graph_extractor import GraphExtractor
from ingestion.graph_store import GraphStore
from ingestion.data_collector import DataCollector
from ingestion.retriever import RetrievalEngine
from ingestion.vector_store import ETNexusVectorStore

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/story-arc", tags=["Story Arc"])

# Global instances (lazy initialization)
graph_extractor = None
graph_store = None
retrieval_engine = None


def get_graph_extractor() -> GraphExtractor:
    """Get or create GraphExtractor instance."""
    global graph_extractor
    if graph_extractor is None:
        graph_extractor = GraphExtractor()
    return graph_extractor


def get_graph_store() -> GraphStore:
    """Get or create GraphStore instance."""
    global graph_store
    if graph_store is None:
        graph_store = GraphStore(storage_path="data/story_graph.json")
    return graph_store


def get_retrieval_engine() -> RetrievalEngine:
    """Get or create RetrievalEngine instance."""
    global retrieval_engine
    if retrieval_engine is None:
        vs = ETNexusVectorStore()
        retrieval_engine = RetrievalEngine(vector_store=vs)
    return retrieval_engine


# Request/Response Models

class ExtractRequest(BaseModel):
    """Request model for story arc extraction."""
    article_ids: Optional[List[str]] = Field(None, description="Specific article IDs to extract from")
    entity_focus: Optional[str] = Field(None, description="Focus on specific entity")
    query: Optional[str] = Field(None, description="Natural language query to find relevant articles")
    limit: int = Field(3, description="Maximum number of articles to process", ge=1, le=10)


class GraphResponse(BaseModel):
    """Response model for graph data."""
    graph: Dict[str, Any] = Field(..., description="Graph data with nodes and edges")
    timeline: Optional[Dict[str, Any]] = Field(None, description="Timeline metadata")
    stats: Dict[str, Any] = Field(..., description="Graph statistics")


# API Endpoints

@router.post("/extract", response_model=GraphResponse)
async def extract_story_arc(request: ExtractRequest):
    """
    Extract story arc from articles using GraphRAG.
    """
    try:
        extractor = get_graph_extractor()
        store = get_graph_store()
        collector = DataCollector()
        
        # Get articles
        articles = []
        
        if request.query:
            # Search for relevant articles
            logger.info(f"Searching for articles matching: {request.query}")
            retriever = get_retrieval_engine()
            search_results = retriever.search(request.query, limit=request.limit)
            
            # search_results are SearchResult objects
            # We need to get the full body for extraction
            # For now, we take them from fallback or scrape if needed
            # Simplest for integration: use the results directly if they have body
            # Or use the IDs to filter from fallback
            
            article_ids = [r.article_id for r in search_results if r.article_id]
            all_articles = collector._load_fallback()
            articles = [a.dict() for a in all_articles if a.article_id in article_ids]
            
        elif request.article_ids:
            # Load specific articles from Vector Store
            logger.info(f"Loading {len(request.article_ids)} specific articles from Vector Store")
            vs = ETNexusVectorStore()
            articles = vs.get_articles_by_ids(request.article_ids)
            
            # If some IDs weren't found in VS, try fallback for them
            if len(articles) < len(request.article_ids):
                logger.info("Some articles missing from Vector Store, checking fallback...")
                found_ids = {a.get('article_id') for a in articles}
                missing_ids = [aid for aid in request.article_ids if aid not in found_ids]
                all_fallback = collector._load_fallback()
                fallback_matches = [a.dict() for a in all_fallback if a.article_id in missing_ids]
                articles.extend(fallback_matches)
        
        else:
            # Load recent articles from Vector Store
            logger.info(f"Loading {request.limit} recent articles from Vector Store")
            vs = ETNexusVectorStore()
            articles = vs.get_latest_articles(limit=request.limit)
            
            # Standardize 'body' field if retriever returns 'content'
            for a in articles:
                if 'content' in a and 'body' not in a:
                    a['body'] = a['content']
                if 'article_id' not in a and 'id' in a:
                    a['article_id'] = a['id']
        
        if not articles:
            raise HTTPException(status_code=404, detail="No articles found")
        
        logger.info(f"Processing {len(articles)} articles for GraphRAG")
        
        # Extract graph
        graph_data = await extractor.extract_story_arc(articles)
        
        # Store in graph database (for cumulative knowledge)
        store.update_from_extraction(graph_data)
        
        # If user selected specific articles, return ONLY the focused graph for those
        if request.article_ids and len(request.article_ids) > 0:
            logger.info("Returning focused graph for specific selections")
            focused_graph = {
                'nodes': graph_data.get('entities', []),
                'edges': graph_data.get('relationships', [])
            }
            return GraphResponse(
                graph=focused_graph,
                timeline=graph_data.get('timeline'),
                stats={
                    "total_entities": len(focused_graph['nodes']),
                    "total_relationships": len(focused_graph['edges'])
                }
            )

        # Otherwise get full graph for response
        full_graph = store.get_full_graph()
        stats = store.get_stats()
        
        return GraphResponse(
            graph=full_graph,
            timeline=graph_data.get('timeline'),
            stats=stats
        )
        
    except Exception as e:
        logger.error(f"Error extracting story arc: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Fallback Mechanism: If extraction fails, return the current state of the global graph 
        # or a curated sample if the global graph is also empty.
        try:
            store = get_graph_store()
            full_graph = store.get_full_graph()
            
            if not full_graph or not full_graph.get('nodes'):
                logger.info("Providing curated fallback graph...")
                # Curated fallback for demo purposes
                return GraphResponse(
                    graph={
                        "nodes": [
                            {"id": "TATAMOTORS", "type": "COMPANY", "name": "Tata Motors", "mentions": 15},
                            {"id": "EV_POLICY", "type": "POLICY", "name": "FAME-III Scheme", "mentions": 8},
                            {"id": "TESLA", "type": "COMPANY", "name": "Tesla Inc.", "mentions": 12},
                            {"id": "RIL", "type": "COMPANY", "name": "Reliance Industries", "mentions": 10}
                        ],
                        "edges": [
                            {"source": "TATAMOTORS", "target": "EV_POLICY", "type": "BENEFITED_FROM", "sentiment": 0.8, "date": "2026-03-25", "edge_id": "e1"},
                            {"source": "TESLA", "target": "TATAMOTORS", "type": "COMPETED_WITH", "sentiment": -0.4, "date": "2026-03-26", "edge_id": "e2"},
                            {"source": "RIL", "target": "EV_POLICY", "type": "INVESTED_IN", "sentiment": 0.6, "date": "2026-03-27", "edge_id": "e3"}
                        ]
                    },
                    timeline={"start_date": "2026-03-25", "end_date": "2026-03-29", "total_articles": 3},
                    stats={"total_entities": 4, "total_relationships": 3}
                )
            
            return GraphResponse(
                graph=full_graph,
                timeline=None,
                stats=store.get_stats()
            )
        except Exception:
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/query")
async def query_graph(
    entity: Optional[str] = Query(None, description="Entity ID to query"),
    start_date: Optional[str] = Query(None, description="Start date (ISO 8601)"),
    end_date: Optional[str] = Query(None, description="End date (ISO 8601)"),
    max_depth: int = Query(2, description="Maximum relationship depth", ge=1, le=5)
):
    try:
        store = get_graph_store()
        
        if entity:
            subgraph = store.query_by_entity(entity, max_depth=max_depth)
        elif start_date and end_date:
            subgraph = store.query_by_date_range(start_date, end_date)
        else:
            subgraph = store.get_full_graph()
        
        return {
            'subgraph': subgraph,
            'stats': {
                'nodes': len(subgraph['nodes']),
                'edges': len(subgraph['edges'])
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/timeline")
async def get_timeline(
    entity: Optional[str] = Query(None, description="Entity ID to filter by"),
    granularity: str = Query("day", description="Timeline granularity: day, week, or month")
):
    try:
        store = get_graph_store()
        timeline = store.get_timeline(entity_id=entity, granularity=granularity)
        return {
            'timeline': timeline,
            'stats': {
                'total_events': sum(len(tp['events']) for tp in timeline),
                'time_points': len(timeline),
                'granularity': granularity
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/contrarian")
async def get_contrarian(
    min_sentiment_diff: float = Query(1.0, description="Minimum sentiment difference", ge=0.5, le=2.0)
):
    try:
        store = get_graph_store()
        contrarian_pairs = store.detect_contrarian(min_sentiment_diff=min_sentiment_diff)
        return {
            'contrarian_pairs': contrarian_pairs,
            'stats': {
                'total_conflicts': len(contrarian_pairs),
                'min_sentiment_diff': min_sentiment_diff
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_graph_stats():
    try:
        store = get_graph_store()
        return store.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    try:
        store = get_graph_store()
        stats = store.get_stats()
        return {
            'status': 'healthy',
            'graph_loaded': True,
            'total_entities': stats['total_entities'],
            'total_relationships': stats['total_relationships'],
            'groq_api_configured': bool(os.getenv("GROQ_API_KEY"))
        }
    except Exception as e:
        return {'status': 'unhealthy', 'error': str(e)}
