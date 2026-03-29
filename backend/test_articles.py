"""Quick test: live RSS ingestion and article count verification."""
import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')

async def main():
    from ingestion.data_collector import DataCollector
    
    collector = DataCollector()
    print("Testing RSS collection (2 per feed)...")
    
    try:
        articles = await collector.collect_from_rss(limit_per_feed=2)
        print(f"Collected {len(articles)} articles from RSS")
        for a in articles[:5]:
            print(f"  - [{a.date[:20] if a.date else 'N/A'}] {a.title[:60]}")
    except Exception as e:
        print(f"RSS FAILED: {e}")
        import traceback
        traceback.print_exc()
    
    # Now test the ingest pipeline
    print("\nTesting full ingest pipeline...")
    from ingestion.et_nexus_ingestion import get_knowledge_base
    kb = get_knowledge_base()
    
    try:
        result = await kb.ingest_from_sources(limit_per_feed=3, use_fallback=False)
        print(f"Ingest result: {result}")
    except Exception as e:
        print(f"INGEST FAILED: {e}")
        import traceback
        traceback.print_exc()
    
    # Check article count
    from ingestion.vector_store import ETNexusVectorStore
    vs = ETNexusVectorStore()
    articles = vs.get_latest_articles(limit=25)
    print(f"\nTotal unique articles in store: {len(articles)}")

asyncio.run(main())
