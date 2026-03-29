"""
Integration Test for AI Video Studio Pipeline.
"""

import os
import asyncio
from dotenv import load_dotenv
from agents.director_agent import DirectorAgent
from agents.voice_engine import VoiceEngine
from agents.visual_engine import VisualEngine

async def test_pipeline():
    print("🚀 Starting AI Video Pipeline Test...")
    load_dotenv()
    
    # 1. Initialize Engines
    director = DirectorAgent()
    voice = VoiceEngine()
    visual = VisualEngine()
    
    title = "India's Tech Sector Booms"
    summary = "Major tech hubs like Bangalore and Hyderabad are seeing record-breaking investments from global giants."
    bull = "Growth is driven by AI innovation and a skilled workforce."
    bear = "Talent shortages and rising costs are potential risks."
    
    # 2. Test Storyboard
    print("\n🎬 Generating storyboard...")
    scenes = director.storyboard(title, summary, bull, bear)
    if not scenes:
        print("❌ Storyboard generation failed!")
        return
    print(f"✅ Generated {len(scenes)} scenes.")
    
    # 3. Test Voice Generation
    print("\n🎙️  Generating narration...")
    all_text = " ".join([s["narration"] for s in scenes])
    audio_path = os.path.join("static", "video", "test_job")
    os.makedirs(os.path.dirname(audio_path), exist_ok=True)
    
    audio_file, vtt_file = await voice.generate_speech(all_text, audio_path)
    if os.path.exists(audio_file) and os.path.exists(vtt_file):
        print(f"✅ Voice and Subtitles generated at: {audio_file}")
    else:
        print("❌ Voice generation failed!")
        
    # 4. Test Visuals (Pexels)
    print("\n🎨 Fetching B-roll visuals...")
    for s in scenes[:2]: # Just test first two
        url = await visual.fetch_broll(s["search_keyword"])
        if url:
            print(f"✅ Found B-roll for '{s['search_keyword']}': {url[:60]}...")
        else:
            print(f"❌ Failed to find B-roll for '{s['search_keyword']}'")

    print("\n🏆 Pipeline Test Complete!")

if __name__ == "__main__":
    asyncio.run(test_pipeline())
