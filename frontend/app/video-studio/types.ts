// AI Video Studio — Types for Remotion Compositions

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

export interface NewsVideoProps {
  script: VideoScene[];
  audio_url: string;
  subtitles_url: string;
  subtitles_text?: string;
  article_title: string;
  total_frames?: number;
  /** Server-parsed word timings — preferred over fetching VTT in the player. */
  caption_words?: CaptionWord[];
}
