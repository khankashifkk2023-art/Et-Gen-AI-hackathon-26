"""
ET Nexus — Vector Store (Qdrant + Sentence Transformers)
Handles embedding, storage, and semantic retrieval of article chunks.
Uses BAAI/bge-small-en-v1.5 for embeddings via sentence-transformers.
"""

import os
import uuid
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    OptimizersConfigDiff,
    ScalarQuantization,
    ScalarQuantizationConfig,
    ScalarType,
)

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

from models.schemas import ArticleChunk, SearchResult


# ─── Configuration ──────────────────────────────────────────────

DB_PATH = os.environ.get("QDRANT_DB_PATH", "./et_nexus_db")
COLLECTION_NAME = "et_articles"
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"  # 384-dim, fast for demo
EMBEDDING_DIM = 384


# ─── Vector Store Class ────────────────────────────────────────

class ETNexusVectorStore:
    """
    Manages the Qdrant vector database for ET Nexus.
    Handles embedding via sentence-transformers, storage, and semantic search
    with metadata filtering.
    """

    def __init__(
        self,
        db_path: str = DB_PATH,
        collection_name: str = COLLECTION_NAME,
    ):
        self.collection_name = collection_name
        self.db_path = db_path

        # Initialize Qdrant (local file-based mode)
        print(f"🗄️  Initializing Qdrant at: {db_path}")
        self.client = QdrantClient(path=db_path)

        # Initialize embedding model
        if SentenceTransformer is not None:
            print(f"🧠 Loading embedding model: {EMBEDDING_MODEL}")
            self.embedder = SentenceTransformer(EMBEDDING_MODEL)
        else:
            print("⚠️  sentence-transformers not available. Embedding disabled.")
            self.embedder = None

        # Ensure collection exists
        self._ensure_collection()

    def _ensure_collection(self):
        """Creates the Qdrant collection with HNSW + Scalar Quantization if it doesn't exist."""
        collections = [c.name for c in self.client.get_collections().collections]
        if self.collection_name not in collections:
            print(f"📦 Creating collection: {self.collection_name} (with Scalar Quantization)")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=EMBEDDING_DIM,
                    distance=Distance.COSINE,
                ),
                optimizers_config=OptimizersConfigDiff(
                    indexing_threshold=10000  # Start HNSW indexing after 10k vectors
                ),
                quantization_config=ScalarQuantization(
                    scalar=ScalarQuantizationConfig(
                        type=ScalarType.INT8,
                        always_ram=True  # Keep quantized vectors in RAM for speed
                    )
                ),
            )
            print(f"   ✅ Collection created with HNSW + INT8 Scalar Quantization (4x memory savings)")
        else:
            print(f"✅ Collection '{self.collection_name}' already exists")

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embeds a list of texts using sentence-transformers."""
        if self.embedder is None:
            raise RuntimeError("Embedding model not available")
        embeddings = self.embedder.encode(texts, show_progress_bar=True, normalize_embeddings=True)
        return embeddings.tolist()

    def ingest_chunks(self, chunks: list[ArticleChunk]) -> int:
        """
        Embeds and upserts article chunks into Qdrant.
        Returns the number of chunks stored.
        """
        if not chunks:
            print("⚠️  No chunks to ingest.")
            return 0

        if self.embedder is None:
            print("❌ Cannot ingest — embedding model not available.")
            return 0

        documents = [chunk.text for chunk in chunks]
        metadata_list = [chunk.metadata for chunk in chunks]

        print(f"🚀 Embedding {len(documents)} chunks...")
        embeddings = self._embed_texts(documents)

        # Build Qdrant points
        points = []
        for i, (embedding, metadata) in enumerate(zip(embeddings, metadata_list)):
            # Store the document text in the payload as well
            payload = {**metadata, "document": documents[i]}
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload=payload,
            )
            points.append(point)

        # Upsert in batches of 100
        batch_size = 100
        for start in range(0, len(points), batch_size):
            batch = points[start : start + batch_size]
            self.client.upsert(
                collection_name=self.collection_name,
                points=batch,
            )

        print(f"✅ Ingested {len(documents)} chunks into Qdrant")
        return len(documents)

    def search(
        self,
        query: str,
        limit: int = 3,
        ticker_filter: Optional[str] = None,
    ) -> list[SearchResult]:
        """
        Performs semantic search with optional metadata filtering.
        Returns formatted results for both LLM context and frontend UI.
        """
        if self.embedder is None:
            print("❌ Cannot search — embedding model not available.")
            return []

        # Embed the query
        query_embedding = self._embed_texts([query])[0]

        # Build filter if ticker is specified
        query_filter = None
        if ticker_filter:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="tags",
                        match=MatchValue(value=ticker_filter),
                    )
                ]
            )

        print(f"🔍 Searching for: '{query[:60]}...' (limit={limit})")

        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            limit=limit,
            query_filter=query_filter,
        )

        # Format results
        formatted: list[SearchResult] = []
        for point in results.points:
            payload = point.payload or {}
            formatted.append(
                SearchResult(
                    rag_text=payload.get("document", ""),
                    title=payload.get("title", "Unknown"),
                    date=payload.get("date", ""),
                    image_url=payload.get("image_url", None),
                    url=payload.get("url", ""),
                    tags=payload.get("tags", []),
                    score=point.score if hasattr(point, "score") else None,
                )
            )

        print(f"   ✅ Found {len(formatted)} results")
        return formatted

    def get_collection_info(self) -> dict:
        """Returns info about the current collection (point count, etc.)."""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "collection_name": self.collection_name,
                "points_count": info.points_count,
                "status": str(info.status),
            }
        except Exception as e:
            return {"error": str(e)}

    def get_latest_articles(self, limit: int = 20, tag_filter: Optional[str] = None) -> list[dict]:
        """
        Scrolls the collection and returns unique articles (deduplicated by title), 
        optionally filtered by a specific tag (category).
        """
        print(f"📰 Fetching latest articles (limit={limit}, filter={tag_filter})...")
        
        # Build filter if tag is specified
        query_filter = None
        if tag_filter:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="tags",
                        match=MatchValue(value=tag_filter),
                    )
                ]
            )

        # Use title as the dedup key for the UI
        articles_by_title: dict[str, dict] = {}

        try:
            # Scroll through points
            offset = None
            batch_size = 100
            while True:
                scroll_result = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=batch_size,
                    offset=offset,
                    scroll_filter=query_filter,  # Apply the tag filter
                    with_payload=True,
                    with_vectors=False,
                )
                points, next_offset = scroll_result

                for point in points:
                    payload = point.payload or {}
                    title = payload.get("title", "")
                    if not title:
                        continue

                    raw_img = payload.get("image_url", None)
                    img: Optional[str] = raw_img if isinstance(raw_img, str) else None
                    img = img.strip() if img else None
                    if img is not None and img == "":
                        img = None
                        
                    # Also include the original doc if available
                    full_doc = payload.get("document", "")

                    if title not in articles_by_title:
                        articles_by_title[title] = {
                            "id": payload.get("article_id", str(point.id)), # Use metadata ID if available, fallback to point ID
                            "title": title,
                            "date": payload.get("date", ""),
                            "summary": (
                                (full_doc[:200] + "...")
                                if len(full_doc) > 200
                                else full_doc
                            ),
                            "tags": payload.get("tags", []),
                            "image_url": img or "",
                            "content": full_doc # Add content for RAG
                        }
                    else:
                        existing = articles_by_title[title]
                        # Append content if it's a multi-chunk article (for scrolling logic)
                        if full_doc and full_doc not in existing["content"]:
                             existing["content"] += "\n" + full_doc
                        
                        if (not existing.get("image_url")) and img:
                            existing["image_url"] = img

                # Only stop when Qdrant indicates there are no more points.
                # Relying on `len(points) < batch_size` can cause premature exits.
                if next_offset is None:
                    break
                offset = next_offset

            # Sort by date descending (newest first)
            articles = list(articles_by_title.values())
            articles.sort(key=lambda a: a.get("date", ""), reverse=True)
        except Exception as e:
            print(f"   ❌ Error fetching articles: {e}")
        return articles

    def get_articles_by_ids(self, article_ids: list[str]) -> list[dict]:
        """
        Retrieves full article content (payload) for specific article identifiers.
        Searches the vector store using the 'article_id' metadata field.
        """
        if not article_ids:
            return []

        print(f"🔍 Fetching content for {len(article_ids)} articles from Vector Store...")
        
        # Build filter to match any of the provided IDs
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="article_id",
                    match=MatchValue(value=aid)
                ) for aid in article_ids
            ]
        )
        
        # Actually, Qdrant 'must' is an AND but we want ANY. 'should' is OR.
        query_filter = Filter(
            should=[
                FieldCondition(
                    key="article_id",
                    match=MatchValue(value=aid)
                ) for aid in article_ids
            ]
        )

        try:
            # Scroll to get all chunks for these articles
            points = []
            offset = None
            while True:
                scroll_result = self.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=query_filter,
                    with_payload=True,
                    limit=100,
                    offset=offset
                )
                p, offset = scroll_result
                points.extend(p)
                if not offset:
                    break
            
            # Group by article_id and assemble text
            articles_by_id: dict[str, dict] = {}
            for point in points:
                payload = point.payload or {}
                aid = payload.get("article_id")
                if not aid:
                    continue
                
                chunk_text = payload.get("document", "")
                
                if aid not in articles_by_id:
                    articles_by_id[aid] = {
                        "article_id": aid,
                        "title": payload.get("title", "Unknown"),
                        "date": payload.get("date", "Recent"),
                        "body": chunk_text,
                        "tags": payload.get("tags", []),
                        "url": payload.get("url", ""),
                        "source": payload.get("source", "Economic Times")
                    }
                else:
                    # Append chunk if not already present
                    if chunk_text and chunk_text not in articles_by_id[aid]["body"]:
                        articles_by_id[aid]["body"] += "\n" + chunk_text
            
            result = list(articles_by_id.values())
            print(f"   ✅ Successfully assembled {len(result)} articles from vector store")
            return result
        except Exception as e:
            print(f"   ❌ Error retrieving articles by ID: {e}")
            return []

    def clear_collection(self):
        """Deletes and recreates the collection. Use for reset."""
        print(f"🗑️  Clearing collection: {self.collection_name}")
        try:
            self.client.delete_collection(self.collection_name)
        except Exception:
            pass
        self._ensure_collection()
        print("   ✅ Collection cleared")
