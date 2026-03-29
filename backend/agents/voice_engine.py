"""
ET Nexus — Voice Engine
Converts text to speech using edge-tts with word-level timing.
"""

import os
import re
import asyncio
import edge_tts
from pathlib import Path
from typing import Tuple


def _ms_to_vtt_ts(ms: int) -> str:
    ms = max(0, int(ms))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, fr = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{fr:03d}"


def _synthetic_word_webvtt(text: str, duration_ms: int) -> str:
    """One cue per token, spread evenly across measured audio length (fallback)."""
    tokens = re.findall(r"\S+", text.strip())
    if not tokens:
        return "WEBVTT\n\n"
    n = len(tokens)
    span = max(duration_ms, n * 40)
    lines: list[str] = ["WEBVTT", ""]
    for i, tok in enumerate(tokens):
        t0 = int(i * span / n)
        t1 = int((i + 1) * span / n) if i < n - 1 else span
        lines.append(str(i + 1))
        lines.append(f"{_ms_to_vtt_ts(t0)} --> {_ms_to_vtt_ts(t1)}")
        lines.append(tok)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _mp3_duration_ms(path: str | Path) -> int:
    path = Path(path)
    try:
        from mutagen.mp3 import MP3

        audio = MP3(str(path))
        if audio.info and audio.info.length:
            return int(float(audio.info.length) * 1000)
    except Exception:
        pass
    return 0


class VoiceEngine:
    """
    The 'News Anchor' — converts storyboard narration to audio.
    Generates MP3 audio and WebVTT subtitles for playback.
    """
    
    def __init__(self, voice: str = "en-IN-NeerjaNeural"):
        self.voice = voice

    async def generate_speech(self, text: str, output_path: str) -> Tuple[str, str]:
        """
        Converts text to MP3 and generates word-level subtitles.
        Returns paths to (audio_file, subtitle_file).
        """
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        audio_file = output_path + ".mp3"
        vtt_file = output_path + ".vtt"
        
        # WordBoundary must be requested — default Communicate() uses SentenceBoundary only,
        # which leaves SubMaker empty and produced the useless "(Narration)" placeholder VTT.
        communicate = edge_tts.Communicate(text, self.voice, boundary="WordBoundary")
        submaker = edge_tts.SubMaker()

        with open(audio_file, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    submaker.feed(chunk)

        with open(vtt_file, "w", encoding="utf-8") as f:
            srt_content = submaker.get_srt()
            if not srt_content:
                dur = _mp3_duration_ms(audio_file)
                if dur < 500:
                    dur = max(min(len(text) * 55, 120_000), 5_000)
                vtt_content = _synthetic_word_webvtt(text, dur)
            else:
                vtt_content = "WEBVTT\n\n" + srt_content.replace(",", ".")
            f.write(vtt_content)
            
        print(f"🎙️  Audio generated: {audio_file}")
        return audio_file, vtt_file

    def run_sync(self, text: str, output_path: str):
        """Sync wrapper for async generation."""
        return asyncio.run(self.generate_speech(text, output_path))
