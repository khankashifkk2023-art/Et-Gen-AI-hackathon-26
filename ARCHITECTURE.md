# 🏗️ ET Nexus — Technical Architecture & Stack

The ET Nexus platform is built on a high-performance, container-ready architecture designed to handle thousands of unstructured financial news articles in real-time, converting them into structured knowledge universes.

---

## 🧠 Core AI & Knowledge Engine (Backend)

The backend is a unified Python system leveraging **Agentic RAG (Retrieval-Augmented Generation)** to transform raw text into actionable insights.

- **FastAPI**: Our high-concurrency gateway for all AI inference and data extraction calls.
- **Groq & LLaMA-3.3-70B**: Ultra-fast inference layer powering our Multi-Agent personas (Bull, Bear, Neutral, Contrarian).
- **Qdrant Vector Database**: Localized vector storage for semantic indexing and high-precision news retrieval.
- **NetworkX**: In-memory graph architecture for topographical mapping of entity relationships.
- **Newspaper3k & Feedparser**: Deep-scraping pipeline for fetching live ET articles from distributed RSS feeds.
- **LangChain**: Orchestrates the orchestration of our knowledge-extraction prompts and document loaders.

---

## 🎨 Immersive Experience Layer (Frontend)

The frontend is a futuristic, dark-themed dashboard focused on spatial data visualization.

- **Next.js 15 (App Router)**: Utilizing React 18 and Turbopack for lightning-fast hydration and state management.
- **React Force Graph (3D)**: A WebGL-powered 3D universe that maps relationships in a spatial coordinate system (powered by **Three.js**).
- **Vis-Network (2D Atlas)**: A high-fidelity physics-based matrix for 2D relationship mapping.
- **Framer Motion**: Orchestrates all interface transitions, micro-interactions, and visual state morphing.
- **Tailwind CSS**: Custom design system built for high-performance responsive layout management.
- **Lucide Icons**: Unified iconography system across the Nexus dashboard.

---

## 🎞️ AI Video Studio & Media Pipeline

- **Edge-TTS**: State-of-the-art text-to-speech engine for real-time news narration.
- **Pexels API**: Dynamic B-roll director that fetches HD video assets based on story keywords.
- **Mutagen & VTT Parsing**: Precise word-level synchronization between narrated audio and visual captions.

---

## 🛠️ DevSecOps & Infrastructure

- **Git & GitHub**: Version control with rigorous **Push Protection** for environment security.
- **TypeScript**: Strict-type safety across the entire visualization engine to prevent runtime rendering crashes.
- **Pydantic**: Robust data validation layer between the AI extraction engine and the UI components.
