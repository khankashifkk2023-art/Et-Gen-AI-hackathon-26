from __future__ import annotations

import os
import sys
import uuid
import re
import math
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv(override=True)

# Add backend dir to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from ingestion.data_collector import DataCollector, ET_RSS_FEEDS
from ingestion.et_nexus_ingestion import ETNexusKnowledgeBase, get_knowledge_base
from agents.pipeline import AgenticPipeline
from agents.director_agent import DirectorAgent
from agents.voice_engine import VoiceEngine
from agents.visual_engine import VisualEngine
from ingestion.vector_store import ETNexusVectorStore
from ingestion.chunker import ArticleChunker

# Chatbot Integration
# Add root for 'chatbot' package
sys.path.insert(0, str(Path(__file__).parent.parent))
# Provide chatbot subdirectories to sys.path with unique names to avoid conflicts with backend modules
sys.path.insert(0, str(Path(__file__).parent.parent / "chatbot"))
from chatbot.cb_engine.chat_engine import ChatEngine
from chatbot.cb_api.schemas import ChatRequest, ChatResponse, ChatHistory
from chatbot.cb_ingestion.qa_ingest import QAVectorStore

# Story Arc Tracker
from api.story_arc import router as story_arc_router

from models.schemas import (
    IngestRequest,
    IngestResponse,
    SearchRequest,
    SearchResponse,
    UserProfile,
    AnalysisRequest,
    AnalysisResponse,
    VideoRequest,
    VideoResponse,
    Scene,
    CaptionWord,
)
from video_subtitles import (
    parse_srt_or_vtt,
    mp3_duration_ms,
    map_scenes_to_timeline,
    words_to_caption_frames,
)


# ─── Global State ───────────────────────────────────────────────

# Use the unified ETNexusKnowledgeBase (Phase 6 singleton)
knowledge_base: "ETNexusKnowledgeBase" = None

# Video Studio agents
director_agent: "DirectorAgent" = None
voice_engine: "VoiceEngine" = None
visual_engine: "VisualEngine" = None
chat_engine: "ChatEngine" = None

# Static directory for video assets
VIDEO_ASSETS_DIR = Path(__file__).parent / "static" / "video"
VIDEO_ASSETS_DIR.mkdir(parents=True, exist_ok=True)


# ─── Startup / Shutdown ────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup, cleanup on shutdown."""
    global knowledge_base, director_agent, voice_engine, visual_engine, chat_engine

    print("\n🚀 ET Nexus Backend starting up...")
    
    # Initialize the unified Knowledge Base (initializes VectorStore, Chunker, etc. internally)
    knowledge_base = get_knowledge_base()
    
    # Initialize Video Studio agents
    print(f"📡 API Key Probe: {os.environ.get('GROQ_API_KEY', 'MISSING')[:12]}...")
    director_agent = DirectorAgent(model="llama-3.3-70b-versatile")
    voice_engine = VoiceEngine()
    visual_engine = VisualEngine()
    
    # Initialize Chatbot Engine with shared Qdrant client to avoid locking
    print("🤖 Initializing Chatbot Engine (Shared Mode)...")
    qa_store = QAVectorStore(client=knowledge_base.vector_store.client)
    chat_engine = ChatEngine(vector_store=qa_store)

    # Check if we already have data
    info = knowledge_base.get_collection_info()
    points = info.get("points_count", 0)
    if points > 0:
        print(f"📊 Vector store ready with {points} chunks")
    else:
        print("📭 Vector store is empty. Use POST /ingest to populate.")

    print("✅ ET Nexus Backend ready!\n")
    yield

    # Cleanup
    print("👋 ET Nexus Backend shutting down...")


# ─── FastAPI App ────────────────────────────────────────────────

app = FastAPI(
    title="ET Nexus API",
    description="AI-Native News Experience Engine — Personalized, Agentic, Generative UI",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS (allow frontend dev server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=False, # Must be False if using ["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Story Arc Tracker Router
app.include_router(story_arc_router)

# Mount static files for video assets (audio, subtitles)
app.mount("/static/video", StaticFiles(directory=str(VIDEO_ASSETS_DIR)), name="video")


# ─── Endpoints ──────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    info = knowledge_base.get_collection_info() if knowledge_base else {}
    return {
        "status": "healthy",
        "service": "ET Nexus API",
        "version": "0.1.0",
        "vector_store": info,
        "chatbot": "operational" if chat_engine else "initializing"
    }


@app.post("/ingest", response_model=IngestResponse)
async def ingest_articles(request: IngestRequest = None):
    """
    Triggers the full ingestion pipeline:
    Scrape → Preprocess → Chunk → Embed → Store in Qdrant.
    """
    if request is None:
        request = IngestRequest()

    start_time = time.time()
    errors: list[str] = []

    try:
        # Step 1: Fetch articles
        print("\n" + "=" * 60)
        print("📡 PHASE 1: Fetching articles...")
        print("=" * 60)
        articles, scrape_errors = fetch_articles(
            rss_feeds=request.rss_feeds,
            limit_per_feed=request.limit_per_feed,
        )
        errors.extend(scrape_errors)

        if not articles:
            return IngestResponse(
                status="no_data",
                articles_scraped=0,
                chunks_stored=0,
                errors=["No articles could be fetched"],
            )

        # Step 2: Preprocess
        print("\n" + "=" * 60)
        print("🛠️  PHASE 2: Preprocessing articles...")
        print("=" * 60)
        processed = preprocess_batch(articles)

        # Step 3: Chunk
        print("\n" + "=" * 60)
        print("✂️  PHASE 3: Chunking articles...")
        print("=" * 60)
        chunks = knowledge_base.chunker.chunk_batch(processed)

        # Step 4: Embed + Store
        print("\n" + "=" * 60)
        print("🚀 PHASE 4: Embedding and storing...")
        print("=" * 60)
        stored_count = knowledge_base.vector_store.ingest_chunks(chunks)

        elapsed = time.time() - start_time
        print(f"\n🎉 Ingestion complete in {elapsed:.1f}s")
        print(f"   Articles: {len(articles)} → Chunks: {stored_count}")

        return IngestResponse(
            status="success",
            articles_scraped=len(articles),
            chunks_stored=stored_count,
            errors=errors,
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@app.post("/ingest/fallback", response_model=IngestResponse)
async def ingest_fallback():
    """
    Ingest from the offline fallback dataset.
    Useful for demo/hackathon when live scraping isn't reliable.
    """
    start_time = time.time()

    try:
        articles, errors = fetch_articles(use_fallback=True)
        processed = preprocess_batch(articles)
        chunks = knowledge_base.chunker.chunk_batch(processed)
        stored_count = knowledge_base.vector_store.ingest_chunks(chunks)

        elapsed = time.time() - start_time
        return IngestResponse(
            status="success (fallback)",
            articles_scraped=len(articles),
            chunks_stored=stored_count,
            errors=errors,
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Fallback ingestion failed: {str(e)}")


@app.post("/search", response_model=SearchResponse)
async def search_articles(request: SearchRequest):
    """
    Semantic search across ingested articles.
    Supports optional ticker filtering for portfolio personalization.
    """
    try:
        results = knowledge_base.vector_store.search(
            query=request.query,
            limit=request.limit,
            ticker_filter=request.ticker_filter,
        )

        return SearchResponse(
            results=results,
            query=request.query,
            total_results=len(results),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_news(request: AnalysisRequest):
    """
    Full Agentic Pipeline (Phase 3):
    Retrieval → Context → Bull/Bear Parallel Analysis → Moderator Synthesis → 
    Guardrails → Generative UI.
    """
    try:
        # Run the pipeline
        # Re-initialize pipeline here if needed, or better yet, use a managed instance
        pipeline_runner = AgenticPipeline(knowledge_base.vector_store)
        result = await pipeline_runner.run_analysis(
            query=request.query,
            user_profile=request.user_profile,
            ticker_filter=None # Derived inside pipeline mapping
        )

        return AnalysisResponse(
            headline=result["headline"] or "ET Nexus Analysis",
            summary=result["summary"],
            component=result["component"], # Generative UI
            impact="Neutral",              # Placeholder
            confidence=result["confidence"],
            ui_metadata={
                "bull": result["bull_view"],
                "bear": result["bear_view"],
                "disclaimer": result.get("disclaimer", "")
            },
            sources=result["sources"]
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis pipeline failed: {str(e)}")


@app.post("/reset")
async def reset_database():
    """Clears and recreates the vector database. Use with caution."""
    try:
        knowledge_base.reset()
        # Also clear preprocessing dedup cache so subsequent ingestion re-processes
        # (otherwise we may scrape identical titles and skip everything).
        reset_dedup_cache()
        return {"status": "reset_complete", "message": "Vector database has been cleared."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")


# ─── Demo Personas (for frontend) ──────────────────────────────

@app.get("/personas")
async def get_demo_personas():
    """Returns pre-configured demo user personas for the frontend."""
    return {
        "personas": [
            UserProfile(
                user_id="demo_student",
                name="Priya (Student)",
                persona="student",
                level="beginner",
                portfolio=[],
                interests=["technology", "startups", "AI"],
            ).model_dump(),
            UserProfile(
                user_id="demo_investor",
                name="Rahul (Retail Investor)",
                persona="retail_investor",
                level="intermediate",
                portfolio=["TATAMOTORS", "HDFCBANK", "INFY"],
                interests=["markets", "banking", "auto"],
            ).model_dump(),
            UserProfile(
                user_id="demo_manager",
                name="Arun (Fund Manager)",
                persona="fund_manager",
                level="expert",
                portfolio=["TATAMOTORS", "HDFCBANK", "RELIANCE", "INFY", "TCS"],
                interests=["markets", "macro", "global"],
            ).model_dump(),
            UserProfile(
                user_id="demo_founder",
                name="Sneha (Startup Founder)",
                persona="startup_founder",
                level="intermediate",
                portfolio=["INFY", "TCS"],
                interests=["technology", "AI", "funding", "startups"],
            ).model_dump(),
        ]
    }


# ─── Run ────────────────────────────────────────────────────────────

@app.post("/ingest/live")
async def ingest_live_articles():
    """
    Ingest articles from live ET RSS feeds using the DataCollector.
    Uses the server's existing vector_store to avoid Qdrant lock conflicts.
    """
    try:
        collector = DataCollector()
        # Fetching 20 articles per category as requested for a 'normal view' robust feed.
        articles_list = await collector.collect_from_rss(limit_per_feed=20)
        
        if not articles_list:
            return {"status": "no_data", "articles_collected": 0, "chunks_stored": 0}
        
        # Preprocess
        processed = preprocess_batch(articles_list)
        
        # Chunk
        chunks = knowledge_base.chunker.chunk_batch(processed)
        
        # Store using the existing vector_store (no new Qdrant connection)
        stored_count = knowledge_base.vector_store.ingest_chunks(chunks)
        
        return {
            "status": "success",
            "articles_collected": len(articles_list),
            "articles_processed": len(processed),
            "chunks_stored": stored_count,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Live ingestion failed: {str(e)}")


@app.get("/articles")
def read_articles(category: str = None):
    """
    Returns unique articles (deduplicated by title, sorted by date descending).
    Supports optional category filtering. Falls back to demo feed if store is empty.
    """
    # Try to get real articles from vector store
    if knowledge_base:
        try:
            # Use tag_filter to support live category clicks from frontend
            articles = knowledge_base.vector_store.get_latest_articles(limit=40, tag_filter=category)
            if articles:
                return articles
        except Exception as e:
            print(f"Error fetching articles: {e}")
    
    # Fallback: static demo feed
    return [
        {
            "id": "1",
            "title": "Impact of EV subsidies on Tata Motors",
            "date": "2026-03-23",
            "summary": "Analyzing the 45% surge in EV sales following the new subsidy scheme.",
            "tags": ["Automotive", "Subsidies", "EV"]
        },
        {
            "id": "2",
            "title": "HDFC Bank Q4 Results: Market Expectations",
            "date": "2026-03-24",
            "summary": "Experts weigh in on HDFC Bank's upcoming quarterly performance.",
            "tags": ["Banking", "Earnings", "Markets"]
        },
        {
            "id": "3",
            "title": "Reliance Industries Green Hydrogen Roadmap",
            "date": "2026-03-22",
            "summary": "RIL's strategic pivot to clean energy enters the next phase.",
            "tags": ["Energy", "Green Hydrogen", "Reliance"]
        }
    ]


@app.get("/rss-feeds")
def get_rss_feeds():
    """Returns available ET RSS feed categories."""
    return {"feeds": ET_RSS_FEEDS}


# ─── Chatbot Endpoints ──────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint for the integrated Nexus Assistant.
    Supports article-specific context and general platform info.
    """
    if not chat_engine:
        raise HTTPException(status_code=503, detail="Chat engine not initialized")
    
    try:
        response = chat_engine.chat(
            user_message=request.user_message,
            session_id=request.session_id,
            user_profile=request.user_profile,
            article_text=request.article_text
        )
        return response
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@app.get("/chat/history/{session_id}", response_model=ChatHistory)
async def get_chat_history(session_id: str, limit: int = 10):
    """Returns the conversation history for a specific session."""
    if not chat_engine:
        raise HTTPException(status_code=503, detail="Chat engine not initialized")
    
    try:
        messages = chat_engine.memory.get_history(session_id, limit=limit)
        session = chat_engine.memory.sessions.get(session_id)
        
        return ChatHistory(
            session_id=session_id,
            messages=messages,
            created_at=session.created_at if session else datetime.now(),
            last_updated=session.last_updated if session else datetime.now()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"History retrieval failed: {str(e)}")


@app.delete("/chat/session/{session_id}")
async def clear_session(session_id: str):
    """Clears the chat history for a specific session."""
    if not chat_engine:
        raise HTTPException(status_code=503, detail="Chat engine not initialized")
    
    chat_engine.clear_session(session_id)
    return {"status": "success", "message": f"Session {session_id} cleared"}


# ─── Video Studio Endpoints ────────────────────────────────────

@app.post("/video/generate", response_model=VideoResponse)
async def generate_video_briefing(request: VideoRequest):
    """
    Generates an AI news video briefing storyboard and audio.
    Audio-first: duration follows MP3 + VTT; scenes use word-level mapping for sync.
    """
    job_id = f"job_{uuid.uuid4().hex[:8]}"
    print(f"🎬 Starting video generation job: {job_id}")
    fps = 30

    try:
        # 1. Storyboard Generation
        scenes_data = director_agent.storyboard(
            title=request.article_title,
            summary=request.summary,
            bull_view=request.bull_view,
            bear_view=request.bear_view
        )

        if not scenes_data:
            raise HTTPException(status_code=500, detail="Failed to generate video storyboard")

        # 2. Voice Generation (single narration — matches director output)
        full_narration = " ".join([s["narration"] for s in scenes_data])
        audio_path = VIDEO_ASSETS_DIR / f"{job_id}_audio"

        await voice_engine.generate_speech(full_narration, str(audio_path))

        mp3_path = f"{audio_path}.mp3"
        vtt_path = f"{audio_path}.vtt"

        # 3. Parse subtitles + audio duration (audio-first timeline)
        word_timeline = parse_srt_or_vtt(vtt_path)
        audio_duration_ms = mp3_duration_ms(mp3_path)
        last_word_end_ms = word_timeline[-1]["end_ms"] if word_timeline else 0
        total_duration_ms = max(audio_duration_ms, last_word_end_ms)
        if total_duration_ms < 500:
            total_duration_ms = max(60_000, len(scenes_data) * 10_000)

        total_frames = max(1, int(math.ceil((total_duration_ms / 1000.0) * fps)))

        # 4. Map scenes to time ranges from word timeline (visual sync to audio)
        mapped = map_scenes_to_timeline(scenes_data, word_timeline)
        if not mapped and scenes_data:
            n = len(scenes_data)
            chunk = total_duration_ms // n if n else total_duration_ms
            mapped = []
            for i, s in enumerate(scenes_data):
                sm = i * chunk
                em = total_duration_ms if i == n - 1 else min(total_duration_ms, (i + 1) * chunk)
                mapped.append({"scene": s, "start_ms": sm, "end_ms": max(em, sm + 1)})

        final_scenes: list[Scene] = []
        for i, row in enumerate(mapped):
            s = row["scene"]
            start_ms = row["start_ms"]
            end_ms = row["end_ms"]
            if i == len(mapped) - 1:
                end_ms = max(end_ms, total_duration_ms)

            start_frame = int((start_ms / 1000.0) * fps)
            end_frame = int(math.ceil((end_ms / 1000.0) * fps))
            end_frame = max(end_frame, start_frame + 1)
            if i == len(mapped) - 1:
                end_frame = max(end_frame, total_frames)

            broll_url = await visual_engine.fetch_broll(s["search_keyword"])

            final_scenes.append(
                Scene(
                    # Stable 1..N so frontend list keys never collapse duplicate LLM scene_id values
                    scene_id=i + 1,
                    narration=s["narration"],
                    search_keyword=s["search_keyword"],
                    overlay_text=s["overlay_text"],
                    composition=s.get("composition", "LOWER_THIRD"),
                    broll_url=broll_url,
                    start_frame=start_frame,
                    end_frame=min(end_frame, total_frames),
                )
            )

        # Last scene must run to the end frame for Remotion
        if final_scenes:
            last = final_scenes[-1]
            final_scenes[-1] = last.model_copy(update={"end_frame": total_frames})

        caption_frames = words_to_caption_frames(word_timeline, fps)
        caption_words = []
        for c in caption_frames:
            sf = max(0, min(int(c["start_frame"]), max(0, total_frames - 1)))
            ef = max(sf + 1, min(int(c["end_frame"]), total_frames))
            caption_words.append(CaptionWord(text=c["text"], start_frame=sf, end_frame=ef))

        return VideoResponse(
            job_id=job_id,
            script=final_scenes,
            audio_url=f"/static/video/{job_id}_audio.mp3",
            subtitles_url=f"/static/video/{job_id}_audio.vtt",
            total_frames=total_frames,
            caption_words=caption_words,
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Video generation failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
