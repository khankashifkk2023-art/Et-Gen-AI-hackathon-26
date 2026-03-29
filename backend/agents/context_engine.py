"""
ET Nexus — Context Engine
Builds the structured context for the agentic pipeline.
Handles RAG retrieval, user profile integration, and context compression.
"""

from typing import Optional
from models.schemas import UserProfile, SearchResult
from ingestion.vector_store import ETNexusVectorStore

class ContextEngine:
    """
    Synthesizes information from multiple sources to create an agent context.
    """
    
    def __init__(self, vector_store: ETNexusVectorStore):
        self.vector_store = vector_store

    def build_context(
        self, 
        query: str, 
        user_profile: UserProfile,
        ticker_filter: Optional[str] = None
    ) -> dict:
        """
        Retrieves relevant news and merges it with user context.
        """
        print(f"🧠 Building context for query: '{query}'")
        
        # 1. Fetch relevant articles via RAG
        # If no specific ticker filter is provided, try to use the user's portfolio
        search_results = self.vector_store.search(
            query=query, 
            limit=5, 
            ticker_filter=ticker_filter
        )
        
        # 2. If no results found with specific filter, search broadly
        if not search_results and ticker_filter:
            print(f"   ⚠️ No results for ticker {ticker_filter}, searching broadly...")
            search_results = self.vector_store.search(query=query, limit=5)

        # 3. Structure the context for the LLM
        context = {
            "query": query,
            "user": {
                "persona": user_profile.persona,
                "level": user_profile.level,
                "portfolio": user_profile.portfolio,
                "interests": user_profile.interests
            },
            "news_chunks": [
                {
                    "text": res.rag_text,
                    "title": res.title,
                    "date": res.date,
                    "source": "Economic Times"
                } for res in search_results
            ]
        }
        
        # 4. Add a summary of the news for quick agent reference
        news_summary = "\n\n".join([
            f"ARTICLE: {res.title}\nDATE: {res.date}\nCONTENT: {res.rag_text}" 
            for res in search_results
        ])
        
        context["formatted_news"] = news_summary
        context["raw_results"] = search_results # Keep for the final response
        
        print(f"   ✅ Context built with {len(search_results)} news chunks")
        return context
