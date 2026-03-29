"""
ET Nexus — Text Chunker
Splits preprocessed articles into overlapping chunks with metadata.
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter
from models.schemas import ProcessedArticle, ArticleChunk


# ─── Configuration ──────────────────────────────────────────────

CHUNK_SIZE = 750        # Characters per chunk
CHUNK_OVERLAP = 100     # ~13% overlap to preserve context across boundaries
SEPARATORS = ["\n\n", "\n", ". ", " ", ""]  # Paragraph → Sentence → Word


# ─── Chunker ────────────────────────────────────────────────────

class ArticleChunker:
    """Splits articles into overlapping text chunks with full metadata."""

    def __init__(
        self,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP,
    ):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=SEPARATORS,
            length_function=len,
        )

    def chunk_article(self, article: ProcessedArticle) -> list[ArticleChunk]:
        """
        Splits a single article into chunks.
        Injects title + date into text before splitting so every chunk has context.
        """
        # Context injection: prefix body with title & date
        full_text = (
            f"Title: {article.title} | Date: {article.normalized_date}\n\n"
            f"{article.clean_body}"
        )

        # Split into chunks
        text_chunks = self.splitter.split_text(full_text)

        # Build ArticleChunk objects with metadata on every chunk
        chunks = []
        for i, chunk_text in enumerate(text_chunks):
            chunk = ArticleChunk(
                chunk_id=f"{article.article_id}_chunk_{i}",
                text=chunk_text,
                metadata={
                    "article_id": article.article_id,
                    "title": article.title,
                    "date": article.normalized_date,
                    "tags": article.tags,
                    "image_url": article.image_url or "",
                    "url": article.url,
                    "source": article.source,
                    "chunk_index": i,
                    "total_chunks": len(text_chunks),
                },
            )
            chunks.append(chunk)

        return chunks

    def chunk_batch(self, articles: list[ProcessedArticle]) -> list[ArticleChunk]:
        """Chunks a batch of articles, returns flat list of all chunks."""
        all_chunks: list[ArticleChunk] = []
        for article in articles:
            try:
                chunks = self.chunk_article(article)
                all_chunks.extend(chunks)
            except Exception as e:
                print(f"⚠️  Chunking failed for '{article.title[:40]}': {e}")

        print(f"✂️  Created {len(all_chunks)} chunks from {len(articles)} articles")
        return all_chunks
