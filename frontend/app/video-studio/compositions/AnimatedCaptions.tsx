// AnimatedCaptions.tsx — YouTube-style line + Roboto; word-timed highlight; props-first data

import React from 'react';
import { useCurrentFrame, interpolate } from 'remotion';
import type { CaptionWord } from '../types';

export interface AnimatedCaptionsProps {
  vttData: string;
  subtitlesText?: string;
  fps: number;
  captionWords?: CaptionWord[];
}

interface TimedWord {
  text: string;
  start_frame: number;
  end_frame: number;
}

interface CaptionSegment {
  start_frame: number;
  end_frame: number;
  words: TimedWord[];
}

const parseVtt = (vtt: string, fps: number): TimedWord[] => {
  const words: TimedWord[] = [];
  const normalized = vtt.replace(/\r\n/g, '\n').replace(/^\ufeff/, '');
  const lines = normalized.split('\n');

  for (let i = 0; i < lines.length; i++) {
    if (lines[i].includes('-->')) {
      const times = lines[i].split(' --> ');
      const startSec = timeToSec(times[0]);
      const endSec = timeToSec(times[1]);

      const text = lines[i + 1]?.trim();
      if (text) {
        const tokenList = text.split(/\s+/).filter(Boolean);
        const n = tokenList.length;
        const span = Math.max(endSec - startSec, 1 / fps);
        const step = span / n;
        for (let j = 0; j < n; j++) {
          const wStart = startSec + j * step;
          const wEnd = j < n - 1 ? startSec + (j + 1) * step : endSec;
          const sf = Math.floor(wStart * fps);
          const ef = Math.max(sf + 1, Math.ceil(wEnd * fps));
          words.push({
            text: tokenList[j],
            start_frame: sf,
            end_frame: ef,
          });
        }
      }
    }
  }
  return closeCaptionGaps(words);
};

function closeCaptionGaps(words: TimedWord[]): TimedWord[] {
  if (words.length <= 1) return words;
  return words.map((w, i) =>
    i < words.length - 1 ? { ...w, end_frame: words[i + 1].start_frame } : w,
  );
}

const timeToSec = (time: string): number => {
  const parts = time.trim().split(':');
  if (parts.length < 2) return 0;
  if (parts.length === 2) {
    const m = parseInt(parts[0], 10) || 0;
    const secParts = parts[1].split(/[.,]/);
    const s = parseInt(secParts[0], 10) || 0;
    const ms = secParts[1] ? parseInt(secParts[1].padEnd(3, '0').slice(0, 3), 10) : 0;
    return m * 60 + s + ms / 1000;
  }
  const [h, m, sRaw] = parts;
  const secParts = sRaw.split(/[.,]/);
  const s = parseInt(secParts[0], 10) || 0;
  const ms = secParts[1] ? parseInt(secParts[1].padEnd(3, '0').slice(0, 3), 10) : 0;
  return (parseInt(h, 10) * 3600 + parseInt(m, 10) * 60 + s) + ms / 1000;
};

/**
 * Build stable caption segments so the visible text doesn't change every frame.
 * This improves readability in the Remotion preview and exported video.
 */
function buildCaptionSegments(
  words: TimedWord[],
  gapFrames = 6,
  maxSegmentFrames = 90,
): CaptionSegment[] {
  if (!words.length) return [];

  const segments: CaptionSegment[] = [];
  let segWords: TimedWord[] = [words[0]];
  let segStart = words[0].start_frame;
  let segEnd = words[0].end_frame;

  for (let i = 1; i < words.length; i++) {
    const w = words[i];
    const fitsGap = w.start_frame - segEnd <= gapFrames;
    const fitsMax = w.end_frame - segStart <= maxSegmentFrames;

    if (fitsGap && fitsMax) {
      segWords.push(w);
      segEnd = w.end_frame;
      continue;
    }

    segments.push({
      start_frame: segStart,
      end_frame: segEnd,
      words: segWords,
    });
    segWords = [w];
    segStart = w.start_frame;
    segEnd = w.end_frame;
  }

  segments.push({
    start_frame: segStart,
    end_frame: segEnd,
    words: segWords,
  });

  return segments;
}

export const AnimatedCaptions: React.FC<AnimatedCaptionsProps> = ({
  vttData,
  subtitlesText,
  fps,
  captionWords,
}) => {
  const frame = useCurrentFrame();
  const [fetchedWords, setFetchedWords] = React.useState<TimedWord[] | null>(null);

  const fromProps = React.useMemo(() => {
    if (captionWords && captionWords.length > 0) {
      return closeCaptionGaps(
        captionWords.map((w) => ({
          text: w.text,
          start_frame: w.start_frame,
          end_frame: w.end_frame,
        })),
      );
    }
    if (subtitlesText && subtitlesText.trim()) {
      return parseVtt(subtitlesText, fps);
    }
    return null;
  }, [captionWords, subtitlesText, fps]);

  React.useEffect(() => {
    if (fromProps && fromProps.length > 0) return;
    if (!vttData.startsWith('http') && !vttData.startsWith('/')) return;
    let cancelled = false;
    fetch(vttData)
      .then((res) => res.text())
      .then((text) => {
        if (!cancelled) setFetchedWords(parseVtt(text, fps));
      })
      .catch((err) => console.error('Failed to fetch VTT:', err));
    return () => {
      cancelled = true;
    };
  }, [vttData, fps, fromProps]);

  const words: TimedWord[] = fromProps && fromProps.length > 0 ? fromProps : fetchedWords || [];

  if (!words.length) return null;

  const segments = React.useMemo(
    () => buildCaptionSegments(words),
    [words],
  );

  const activeSegment = segments.find(
    (s) => frame >= s.start_frame && frame < s.end_frame,
  );
  if (!activeSegment) return null;

  const activeWord =
    activeSegment.words.find((w) => frame >= w.start_frame && frame < w.end_frame) ??
    activeSegment.words[0];

  const wordPop = interpolate(
    frame,
    [activeWord.start_frame, activeWord.start_frame + Math.max(8, Math.round(fps * 0.25))],
    [0.985, 1.03],
    { extrapolateRight: 'clamp' },
  );

  return (
    <div
      style={{
        position: 'absolute',
        bottom: '10%',
        left: 0,
        width: '100%',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        pointerEvents: 'none',
        zIndex: 100,
        padding: '0 28px',
        boxSizing: 'border-box',
      }}
    >
      <div
        style={{
          transform: `translateY(${interpolate(frame, [activeSegment.start_frame, activeSegment.start_frame + 10], [4, 0], { extrapolateRight: 'clamp' })}px)`,
          maxWidth: '92%',
          backgroundColor: 'rgba(8, 8, 8, 0.78)',
          borderRadius: 4,
          padding: '10px 16px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.45)',
        }}
      >
        <p
          style={{
            margin: 0,
            display: 'flex',
            flexWrap: 'wrap',
            justifyContent: 'center',
            gap: '0.35em',
            alignItems: 'baseline',
            fontFamily: 'var(--font-caption-roboto), "Roboto", system-ui, sans-serif',
            fontSize: 40,
            lineHeight: 1.35,
            letterSpacing: '0.01em',
            textAlign: 'center',
          }}
        >
          {activeSegment.words.map((w, i) => {
            const active = w === activeWord || (w.start_frame === activeWord.start_frame && w.end_frame === activeWord.end_frame && w.text === activeWord.text);
            return (
              <span
                key={`${w.start_frame}-${w.end_frame}-${i}-${w.text}`}
                style={{
                  fontWeight: active ? 700 : 500,
                  color: active ? '#ffffff' : 'rgba(255, 255, 255, 0.78)',
                  textShadow: active
                    ? '0 0 1px rgba(0,0,0,0.9), 0 1px 2px rgba(0,0,0,0.6)'
                    : 'none',
                  transform: active ? `scale(${wordPop})` : 'scale(1)',
                  display: 'inline-block',
                }}
              >
                {w.text}
                {i < activeSegment.words.length - 1 ? ' ' : ''}
              </span>
            );
          })}
        </p>
      </div>
    </div>
  );
};
