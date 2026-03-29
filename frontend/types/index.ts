// ET Nexus Frontend Types — mirrors backend Pydantic schemas

export interface UserProfile {
  user_id: string;
  name?: string;
  persona: string;
  level: string;
  portfolio: string[];
  interests: string[];
}

export interface SearchResult {
  rag_text: string;
  title: string;
  date: string;
  image_url?: string;
  url: string;
  tags: string[];
  score?: number;
}

export interface AnalysisRequest {
  query: string;
  user_profile: UserProfile;
  article_url?: string;
}

export interface AnalysisResponse {
  headline: string;
  summary: string;
  component: string;
  impact: string;
  confidence: number;
  ui_metadata: {
    bull: string;
    bear: string;
    disclaimer?: string;
  };
  sources: SearchResult[];
}

export interface Persona {
  user_id: string;
  name: string;
  persona: string;
  level: string;
  portfolio: string[];
  interests: string[];
}

// Article type for the /articles feed
export interface Article {
  id: string;
  title: string;
  date: string;
  summary: string;
  tags: string[];
  image_url?: string;
  content?: string;
}
// Video Studio Types
export interface VideoScene {
  scene_id: number;
  narration: string;
  search_keyword: string;
  overlay_text: string;
  composition: string;
  broll_url?: string;
  start_frame: number;
  end_frame: number;
}

export interface CaptionWord {
  text: string;
  start_frame: number;
  end_frame: number;
}

export interface VideoResponse {
  job_id: string;
  script: VideoScene[];
  audio_url: string;
  subtitles_url: string;
  total_frames: number;
  status: string;
  caption_words?: CaptionWord[];
  /** Set client-side after fetching `subtitles_url` (not returned by the API JSON). */
  subtitles_text?: string;
}
