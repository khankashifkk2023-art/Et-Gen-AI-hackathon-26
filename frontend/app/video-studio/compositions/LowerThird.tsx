// LowerThird.tsx — Branded News Overlay

import React from 'react';
import { interpolate, useCurrentFrame, useVideoConfig } from 'remotion';

export interface LowerThirdProps {
  text: string;
  sentiment?: string; // e.g. 'bullish', 'bearish'
}

export const LowerThird: React.FC<LowerThirdProps> = ({ text, sentiment }) => {
  const frame = useCurrentFrame();
  const { width, durationInFrames } = useVideoConfig();
  
  // Animation: slide in from left over first 15 frames
  const slideIn = interpolate(frame, [0, 15], [-400, 40], {
    extrapolateRight: 'clamp',
  });
  
  // Fade out during the last 15 frames of the specific scene/sequence
  const opacity = interpolate(
    frame, 
    [durationInFrames - 15, durationInFrames - 5], 
    [1, 0], 
    { extrapolateLeft: 'clamp' }
  );

  return (
    <div 
      style={{ 
        position: 'absolute', 
        bottom: 80, 
        left: slideIn, 
        opacity,
        display: 'flex',
        flexDirection: 'column',
        gap: 0,
        filter: 'drop-shadow(0 10px 20px rgba(0,0,0,0.3))'
      }}
    >
      {/* Top Label */}
      <div style={{
        background: '#ED1C24',
        color: 'white',
        padding: '6px 16px',
        fontSize: 18,
        fontWeight: 900,
        textTransform: 'uppercase',
        letterSpacing: '0.15em',
        width: 'fit-content',
        borderTopRightRadius: 4,
        fontFamily: 'Outfit, sans-serif'
      }}>
        ET DEMO • {sentiment?.toUpperCase() || "INTELLIGENCE"}
      </div>
      
      {/* Main Bar */}
      <div style={{
        background: 'rgba(16, 23, 35, 0.95)',
        backdropFilter: 'blur(10px)',
        color: 'white',
        padding: '12px 30px',
        fontSize: 40,
        fontWeight: 700,
        borderLeft: '8px solid #ED1C24',
        minWidth: 500,
        fontFamily: 'Playfair Display, serif',
        boxShadow: '0 4px 15px rgba(0,0,0,0.2)'
      }}>
        {text}
      </div>
    </div>
  );
};
