/**
 * Pre-download B-roll and narration so Remotion <Video>/<Audio> don't stall on scene changes.
 * Uses Remotion's prefetch (blob URLs in browser).
 */
import { prefetch } from "remotion";
import type { VideoResponse } from "@/types";

export async function prefetchVideoJobAssets(job: VideoResponse, apiBase: string): Promise<void> {
  const urls: string[] = [];
  const seen = new Set<string>();

  const push = (u: string | undefined) => {
    if (!u || seen.has(u)) return;
    seen.add(u);
    urls.push(u);
  };

  // Ensure apiBase doesn't have trailing slash
  const cleanBase = (apiBase || "").replace(/\/$/, "");

  // Narration
  if (job.audio_url) {
    push(`${cleanBase}${job.audio_url}`);
  }
  
  // Subtitles
  if (job.subtitles_url) {
    push(`${cleanBase}${job.subtitles_url}`);
  }

  // B-roll
  if (job.script) {
    for (const scene of job.script) {
      if (scene.broll_url) {
        push(scene.broll_url);
      }
    }
  }

  const results = await Promise.allSettled(
    urls.map((src) => prefetch(src, { method: "blob-url" }).waitUntilDone()),
  );

  results.forEach((r, i) => {
    if (r.status === "rejected") {
      console.warn(`[prefetch] failed ${urls[i]}`, r.reason);
    }
  });
}
