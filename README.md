<div align="center">
  <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/The_Economic_Times_logo.svg/1200px-The_Economic_Times_logo.svg.png" alt="ET Logo" width="120" />
  <h1>ET Nexus</h1>
  <p><b>Intelligent Knowledge Graphs & Multi-Agent Narrative Engine</b></p>
</div>

---

## 🚀 Overview

**ET Nexus** transforms unstructured financial and market news from RSS feeds into fully coherent, interactive 2D and 3D knowledge universes. Powered by an advanced GraphRAG framework and Multi-Agent Persona systems, the platform moves beyond simple keyword searching—extracting, mapping, and connecting deep narrative contexts between entities, companies, people, and policies in real-time.

---

## ✨ Key Features

1. **AI Multi-Agent Ecosystem**
   Every article is evaluated by specialized LLaMA-3 personas—the **Bull**, the **Bear**, the **Neutral**, and the **Contrarian**. They independently grade sentiment, detect subtle biases, and derive an overall market consensus metric stored natively within the Graph.
2. **Graph Retrieval-Augmented Generation (GraphRAG)**
   Financial jargon is parsed through adaptive semantic chunking mechanisms over a localized Qdrant Vector Store, allowing our extraction engine to mathematically map entity dependencies and relationships.
3. **Immersive Temporal Visualizations**
   Toggle effortlessly between the **2D Atlas Matrix** and the WebGL-powered **3D Spatial Canvas**. Watch structures morph as you use the Timeline Scrubber to navigate historical data structures chronologically.
4. **Focused Article Triage**
   Select highly specific articles from the sidebar interface to dynamically render isolated, pristine knowledge arcs that bypass global market noise.

---

## 🛠️ Technology Stack

**Backend (Engine & Agent Layer)**
- **Framework**: `FastAPI` (Python 3.10+) 
- **Database**: Localized `Qdrant` DB (Vector Indexing) & Native NetworkX routing
- **AI/LLM**: `LangChain`, `Groq Inference API` (`llama-3.3-70b-versatile`)
- **Extraction**: Pydantic structured schema alignment

**Frontend (Interface & Canvas)**
- **Framework**: `Next.js 14` (React 18), `TypeScript`, `Turbopack`
- **Visualization Engines**: `vis-network` (2D), `react-force-graph-3d` (3D webGL binding)
- **Styling & Motion**: `Tailwind CSS`, `Framer Motion`, `Lucide Icons`

---

## ⚙️ Quick Start Installation

Because the repository is optimized for GitHub/Submission size, you must install the runtime dependencies first.

### 1. Backend Engine
Ensure you have Python 3.10 installed on your device.
```bash
cd backend
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Mac/Linux: 
source venv/bin/activate

pip install -r requirements.txt
```
**Environment Credentials:**
In the `/backend` folder, copy `.env.example` to `.env` and configure your keys:
```env
# --- Core AI (Llama-3 via Groq) ---
GROQ_API_KEY=gsk_your_api_key_here

# --- Visual Director (B-Roll Assets) ---
PEXELS_API_KEY=your_pexels_api_key_here (Optional: Disables Video Generation if missing)

# --- Market Data & Search ---
NEWS_API_KEY=your_newsapi_key_here
SERPER_API_KEY=your_serper_api_key_here

# --- Voice Engine (Optional) ---
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
```
**Launch Server:**
```bash
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
> The API will be available at `http://localhost:8000`.

### 2. Frontend Interface
In a separate terminal, install the Next.js dependancy tree:
```bash
cd frontend
npm install
```
**Launch Application:**
```bash
npm run dev
```
> The ET Nexus UI will launch at `http://localhost:3000`. Select "Start Global Extraction" on the platform to begin!

---

*Built with ❤️ for the Hackathon Submission. To explore specific multi-agent capabilities, view the `/backend/agents` directory.*
