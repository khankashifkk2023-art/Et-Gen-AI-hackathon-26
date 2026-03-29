"""Quick smoke test for the Phase 1 pipeline."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
os.environ["PYTHONIOENCODING"] = "utf-8"

def main():
    print("--- Testing Schemas ---")
    from models.schemas import UserProfile, ScrapedArticle
    user = UserProfile(user_id="test", portfolio=["TATAMOTORS"])
    print(f"  UserProfile OK: {user.persona}")

    print("\n--- Testing Scraper (fallback) ---")
    from ingestion.scraper import fetch_articles
    articles, errors = fetch_articles(use_fallback=True)
    print(f"  Fetched {len(articles)} articles")
    if articles:
        print(f"  First: {articles[0].title[:50]}")

    print("\n--- Testing Preprocessor ---")
    from ingestion.preprocessor import preprocess_batch
    processed = preprocess_batch(articles)
    print(f"  Processed {len(processed)} articles")

    print("\n--- Testing Chunker ---")
    from ingestion.chunker import ArticleChunker
    chunker = ArticleChunker()
    chunks = chunker.chunk_batch(processed)
    print(f"  Created {len(chunks)} chunks")
    if chunks:
        print(f"  Sample chunk metadata keys: {list(chunks[0].metadata.keys())}")

    print("\n--- Testing Vector Store ---")
    from ingestion.vector_store import ETNexusVectorStore
    # Use a temp path for testing
    store = ETNexusVectorStore(db_path="./test_db")
    stored = store.ingest_chunks(chunks)
    print(f"  Stored {stored} chunks")

    print("\n--- Testing Search ---")
    results = store.search("EV subsidies impact on auto sector", limit=2)
    print(f"  Found {len(results)} results")
    for i, r in enumerate(results):
        print(f"  Result {i+1}: {r.title[:50]} (score={r.score})")

    # Cleanup test db
    import shutil
    if os.path.exists("./test_db"):
        store.client.close()
        shutil.rmtree("./test_db", ignore_errors=True)
        print("\n  Cleaned up test_db")

    print("\n=== ALL PHASE 1 TESTS PASSED ===")

if __name__ == "__main__":
    main()
