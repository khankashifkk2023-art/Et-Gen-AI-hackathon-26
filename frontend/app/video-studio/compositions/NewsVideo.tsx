// NewsVideo.tsx — Main Composition

import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Video,
  Sequence,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import { NewsVideoProps } from '../types';
import { LowerThird } from './LowerThird';
import { AnimatedCaptions } from './AnimatedCaptions';

const VideoSceneRenderer: React.FC<{
  url: string;
  duration: number;
}> = ({ url, duration }) => {
  const frame = useCurrentFrame();
  // Sequence-local frame: Ken Burns over this scene only
  const scale = interpolate(
    frame,
    [0, Math.max(1, duration)],
    [1, 1.15],
    { extrapolateRight: 'clamp' }
  );

  // Fade in for first 15 frames
  const opacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ transform: `scale(${scale})`, opacity }}>
      <Video
        src={url}
        muted
        loop
        volume={0}
        acceptableTimeShiftInSeconds={0.75}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
        }}
      />
    </AbsoluteFill>
  );
};

export const NewsVideo: React.FC<NewsVideoProps> = ({
  script,
  audio_url,
  subtitles_url,
  subtitles_text,
  article_title,
  caption_words,
}) => {
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill style={{ backgroundColor: 'black' }}>
      {/* 1. Main Scenes (B-roll background with sync) */}
      {script.map((scene, idx) => {
        const sceneDuration = scene.end_frame - scene.start_frame;

        return (
          <Sequence
            key={`scene-${idx}-${scene.start_frame}-${scene.end_frame}`}
            from={scene.start_frame}
            durationInFrames={sceneDuration}
            layout="absolute-fill"
            premountFor={Math.min(120, Math.max(45, Math.round(fps * 2)))}
          >
            <AbsoluteFill>
              {scene.broll_url ? (
                <VideoSceneRenderer
                  key={`clip-${idx}-${scene.start_frame}-${scene.broll_url}`}
                  url={scene.broll_url}
                  duration={sceneDuration}
                />
              ) : (
                <div style={{
                  width: '100%',
                  height: '100%',
                  background: 'linear-gradient(45deg, #101723, #1A2639)',
                  display: 'flex',
                  justifyContent: 'center',
                  alignItems: 'center',
                  color: 'white',
                  fontSize: 40,
                  fontFamily: 'Playfair Display, serif'
                }}>
                  {article_title}
                </div>
              )}
              
              {/* Branded Overlay (Lower Third) */}
              <LowerThird 
                text={scene.overlay_text} 
                sentiment={scene.search_keyword.includes('bull') ? 'bullish' : 
                           scene.search_keyword.includes('bear') ? 'bearish' : 'intelligence'}
              />
            </AbsoluteFill>
          </Sequence>
        );
      })}

      {/* 2. Global Overlays */}
      
      {/* Animated Captions */}
      <AnimatedCaptions
        vttData={subtitles_url}
        subtitlesText={subtitles_text}
        fps={fps}
        captionWords={caption_words}
      />

      {/* Corporate Branding Watermark */}
      <div style={{
        position: 'absolute',
        top: 40,
        right: 40,
        background: 'rgba(237, 28, 36, 0.9)',
        color: 'white',
        fontWeight: 900,
        padding: '5px 15px',
        fontSize: 20,
        fontFamily: 'Outfit, sans-serif',
        borderRadius: 4,
        letterSpacing: '0.1em'
      }}>
        ET DEMO
      </div>

      {/* 3. Audio Narration */}
      <Audio src={audio_url} />
    </AbsoluteFill>
  );
};
