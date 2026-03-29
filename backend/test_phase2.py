"""
Quick test for Phase 2 Agentic Pipeline.
"""
import sys
import os
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from models.schemas import UserProfile
from agents.pipeline import AgenticPipeline
from ingestion.vector_store import ETNexusVectorStore
from dotenv import load_dotenv

async def test_pipeline():
    load_dotenv()
    if not os.environ.get("GROQ_API_KEY"):
        print("❌ GROQ_API_KEY not found in .env. Skipping test.")
        return

    print("🚀 Initializing Pipeline Test...")
    vector_store = ETNexusVectorStore()
    pipeline = AgenticPipeline(vector_store)

    # 1. Ensure we have data
    info = vector_store.get_collection_info()
    if info.get("points_count", 0) == 0:
        print("⚠️  Vector store empty. Run ingest/fallback first.")
        return

    # 2. Test Persona
    investor = UserProfile(
        user_id="test_investor",
        name="Test Rahul",
        persona="retail_investor",
        level="intermediate",
        portfolio=["TATAMOTORS", "HDFCBANK"],
        interests=["auto", "banking"]
    )

    # 3. Run Analysis
    print("\n--- 🤖 Running Agentic Analysis: 'Tata Motors EV prospects' ---")
    result = await pipeline.run_analysis(
        query="Tata Motors EV prospects and government subsidies",
        user_profile=investor,
        ticker_filter="TATAMOTORS"
    )

    print("\n" + "="*80)
    print("📰 FINAL MODERATOR SYNTHESIS")
    print("="*80)
    print(result["summary"])
    print("\n" + "="*80)
    print(f"🐂 BULL VIEW (Snippet): {result['bull_view'][:150]}...")
    print(f"🐻 BEAR VIEW (Snippet): {result['bear_view'][:150]}...")
    print(f"📚 Sources Found: {len(result['sources'])}")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(test_pipeline())
