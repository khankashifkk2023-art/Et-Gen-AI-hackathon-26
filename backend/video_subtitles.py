"""
Parse edge-tts SRT/VTT output and map words to scenes for audio-first video sync.
"""
from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any


def _time_to_ms(ts: str) -> int:
    """Parse 00:00:00,000 or 00:00:00.000 or 00:01:02,500 to milliseconds."""
    ts = ts.strip().replace(",", ".")
    parts = ts.split(":")
    if len(parts) == 3:
        h, m, s = parts
    elif len(parts) == 2:
        h = "0"
        m, s = parts
    else:
        raise ValueError(f"Bad timestamp: {ts}")
    sec_parts = s.split(".")
    sec = int(sec_parts[0])
    ms = int(sec_parts[1].ljust(3, "0")[:3]) if len(sec_parts) > 1 else 0
    return int(h) * 3600000 + int(m) * 60000 + sec * 1000 + ms


def parse_srt_or_vtt(path: str | Path) -> list[dict[str, Any]]:
    """
    Parse WEBVTT or SRT file from edge-tts SubMaker.
    Returns ordered list of {word, start_ms, end_ms} (one entry per token).
    """
    path = Path(path)
    raw = path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
    if raw.startswith("\ufeff"):
        raw = raw[1:]
    if raw.startswith("WEBVTT"):
        raw = raw.split("\n", 1)[-1].strip()

    words: list[dict[str, Any]] = []
    blocks = re.split(r"\n\s*\n", raw.strip())
    for block in blocks:
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        i = 0
        if re.match(r"^\d+$", lines[0]):
            i = 1
        if i >= len(lines) or "-->" not in lines[i]:
            continue
        time_line = lines[i]
        start_s, end_s = time_line.split("-->", 1)
        try:
            start_ms = _time_to_ms(start_s)
            end_ms = _time_to_ms(end_s)
        except Exception:
            continue
        text = " ".join(lines[i + 1 :]).strip()
        if not text:
            continue
        token_list = re.findall(r"\S+", text)
        if not token_list:
            continue
        n = len(token_list)
        span = max(end_ms - start_ms, 1)
        step = span / n
        for j, tok in enumerate(token_list):
            w_start = int(start_ms + j * step)
            w_end = int(start_ms + (j + 1) * step) if j < n - 1 else end_ms
            words.append({"word": tok, "start_ms": w_start, "end_ms": w_end})
    return words


def mp3_duration_ms(path: str | Path) -> int:
    """Return MP3 duration in milliseconds (audio-first source of truth)."""
    path = Path(path)
    try:
        from mutagen.mp3 import MP3

        audio = MP3(str(path))
        if audio.info and audio.info.length:
            return int(float(audio.info.length) * 1000)
    except Exception:
        pass
    return 0


def count_words(text: str) -> int:
    return len(re.findall(r"\w+", text))


def _largest_remainder_alloc(wlen: int, weights: list[int]) -> list[int]:
    """Integer counts that sum to wlen, proportional to weights (Hamilton)."""
    n = len(weights)
    total_w = sum(weights)
    if n == 0 or wlen <= 0:
        return [0] * n
    if total_w <= 0:
        q, r = divmod(wlen, n)
        return [q + (1 if i < r else 0) for i in range(n)]
    quotas = [w * wlen / total_w for w in weights]
    floors = [int(q) for q in quotas]
    remainder = wlen - sum(floors)
    frac_order = sorted(range(n), key=lambda i: quotas[i] - floors[i], reverse=True)
    for k in range(remainder):
        floors[frac_order[k % n]] += 1
    # Steal from richest if any bucket is 0 but we have words (wlen >= n)
    for _ in range(n * 2):
        if all(c > 0 for c in floors) or wlen < n:
            break
        poor = next(i for i in range(n) if floors[i] == 0)
        rich = max(range(n), key=lambda i: floors[i])
        if floors[rich] <= 1:
            break
        floors[rich] -= 1
        floors[poor] += 1
    return floors


def map_scenes_to_timeline(
    scenes: list[dict],
    word_timeline: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Assign each scene start/end ms by splitting the word timeline across scenes
    proportionally to each scene's narration word count (audio-first).
    """
    if not word_timeline or not scenes:
        return []

    wlen = len(word_timeline)
    n = len(scenes)
    if wlen < n:
        return []

    raw_counts = [max(1, count_words(s.get("narration", ""))) for s in scenes]
    alloc = _largest_remainder_alloc(wlen, raw_counts)

    assigned: list[list[dict[str, Any]]] = []
    idx = 0
    for take in alloc:
        take = min(max(0, take), wlen - idx)
        chunk = word_timeline[idx : idx + take] if take > 0 else []
        assigned.append(chunk)
        idx += take
    if idx < wlen and assigned:
        assigned[-1].extend(word_timeline[idx:])

    out = []
    for scene, wds in zip(scenes, assigned):
        if not wds:
            out.append({"scene": scene, "start_ms": 0, "end_ms": 0})
            continue
        out.append(
            {
                "scene": scene,
                "start_ms": wds[0]["start_ms"],
                "end_ms": wds[-1]["end_ms"],
            }
        )
    return out


def words_to_caption_frames(
    word_timeline: list[dict[str, Any]], fps: int = 30
) -> list[dict[str, Any]]:
    """Build caption entries with frame ranges for Remotion."""
    caps = []
    for w in word_timeline:
        sf = int(math.floor(w["start_ms"] / 1000 * fps))
        ef = max(sf + 1, int(math.ceil(w["end_ms"] / 1000 * fps)))
        caps.append(
            {
                "text": w["word"],
                "start_frame": sf,
                "end_frame": ef,
            }
        )
    return caps
