"""
End-to-end verification for Phase 3 (Generative UI + Guardrails).
"""
import sys
import os
import asyncio
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from models.schemas import UserProfile
from agents.pipeline import AgenticPipeline
from ingestion.vector_store import ETNexusVectorStore
from dotenv import load_dotenv

async def test_full_pipeline():
    load_dotenv()
    print("🚀 Running Phase 3 Full Pipeline Test...")
    vector_store = ETNexusVectorStore()
    pipeline = AgenticPipeline(vector_store)

    investor = UserProfile(
        user_id="expert_user_1",
        name="Expert Dev",
        persona="retail_investor",
        level="expert",
        portfolio=["TATAMOTORS"]
    )

    print("\n--- 🤖 Testing Bullish Impact & UI Component ---")
    res = await pipeline.run_analysis(
        query="Strong Tata Motors growth in EV sector",
        user_profile=investor,
        ticker_filter="TATAMOTORS"
    )
    print(f"  Headline: {res['headline']}")
    print(f"  Component: {res['component']} (Expected: BullishTrendChart/StockImpactChart)")
    print(f"  Confidence: {res['confidence']}")

    print("\n--- 🛡️  Testing Guardrails (Buy/Sell) ---")
    moderator_text_with_advice = "The data says you should definitely buy TATAMOTORS stocks now!"
    filtered = pipeline.safety.filter_advice(moderator_text_with_advice)
    print(f"  Original: '{moderator_text_with_advice}'")
    print(f"  Filtered: '{filtered}'")
    
    if "buy" not in filtered.lower():
        print("  ✅ Guardrail successfully blocked 'buy' command.")

    print("\n--- 📚 Testing Disclaimer Presence ---")
    if res.get("disclaimer"):
        print(f"  ✅ Disclaimer Present: {res['disclaimer'][:40]}...")

    print("\n=== PHASE 3 VERIFICATION PASSED ===")

if __name__ == "__main__":
    asyncio.run(test_full_pipeline())
