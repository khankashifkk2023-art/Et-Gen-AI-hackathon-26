import type { AnalysisRequest, AnalysisResponse, Article, Persona, SearchResult, VideoResponse } from "@/types";

/**
 * Dynamic API Host Resolution
 * Detects the correct host (localhost vs network IP) to avoid CORS/connection errors
 * when the ET Nexus app is accessed from different devices on a local network.
 */
const getApiBase = () => {
  if (typeof window !== "undefined") {
    const hostname = window.location.hostname;
    // If accessing via IP (like 172.x.x.x), use that same IP for the backend at port 8000
    if (hostname !== "localhost" && !hostname.includes("127.0.0.1")) {
      return `http://${hostname}:8000`;
    }
  }
  return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
};

export const API_BASE = getApiBase();

export async function fetchPersonas(): Promise<Persona[]> {
  const res = await fetch(`${API_BASE}/personas`);
  if (!res.ok) throw new Error("Failed to fetch personas");
  const data = await res.json();
  return data.personas;
}

export async function fetchArticles(category?: string): Promise<Article[]> {
  const url = category ? `${API_BASE}/articles?category=${encodeURIComponent(category)}` : `${API_BASE}/articles`;
  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to fetch articles");
  return res.json();
}

export async function ingestFallback(): Promise<{ status: string; articles_scraped: number; chunks_stored: number }> {
  const res = await fetch(`${API_BASE}/ingest/fallback`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to ingest");
  return res.json();
}

export async function ingestLive(): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/ingest/live`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to ingest live");
  return res.json();
}

export async function searchArticles(query: string, limit = 5, ticker?: string): Promise<{ results: SearchResult[]; total_results: number }> {
  const res = await fetch(`${API_BASE}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, limit, ticker_filter: ticker }),
  });
  if (!res.ok) throw new Error("Search failed");
  return res.json();
}

export async function analyzeNews(request: AnalysisRequest): Promise<AnalysisResponse> {
  const res = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!res.ok) throw new Error("Analysis failed");
  return res.json();
}

export async function checkHealth(): Promise<{ status: string; vector_store: Record<string, unknown> }> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error("Health check failed");
  return res.json();
}

// Video Studio
export const generateVideo = async (data: {
  article_title: string;
  summary: string;
  bull_view: string;
  bear_view: string;
}): Promise<VideoResponse> => {
  const res = await fetch(`${API_BASE}/video/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    const message = errorBody.detail || "Video Synthesis Failed: The backend agent timed out or encountered an extraction error.";
    throw new Error(message);
  }
  
  const payload: VideoResponse = await res.json();
  
  // Try to pre-fetch subtitles text for the frontend
  let subtitles_text: string | undefined;
  try {
    const subRes = await fetch(`${API_BASE}${payload.subtitles_url}`);
    if (subRes.ok) subtitles_text = await subRes.text();
  } catch (err) {
    console.warn("Subtitle pre-fetch warning:", err);
  }
  
  return { ...payload, subtitles_text };
};
