'use client';

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Calendar, Play, Pause, ChevronLeft, ChevronRight, Clock } from 'lucide-react';

interface TimeTravelSliderProps {
  startDate: string;
  endDate: string;
  onDateChange: (date: string) => void;
  accentColor?: string;
  className?: string;
  /** Single slim row — minimal vertical space */
  variant?: 'default' | 'compact';
}

export default function TimeTravelSlider({
  startDate,
  endDate,
  onDateChange,
  accentColor = '#ED1C24',
  className = '',
  variant = 'default'
}: TimeTravelSliderProps) {
  const [currentDate, setCurrentDate] = useState(endDate);
  const [isPlaying, setIsPlaying] = useState(false);
  const [dates, setDates] = useState<string[]>([]);

  // Generate date array
  useEffect(() => {
    const start = new Date(startDate);
    const end = new Date(endDate);
    const tempDates: string[] = [];
    
    let current = new Date(start);
    while (current <= end) {
      tempDates.push(current.toISOString().split('T')[0]);
      current.setDate(current.getDate() + 1);
    }
    setDates(tempDates);
    setCurrentDate(endDate);
  }, [startDate, endDate]);

  // Handle auto-play
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isPlaying) {
      interval = setInterval(() => {
        const currentIndex = dates.indexOf(currentDate);
        if (currentIndex < dates.length - 1) {
          const nextDate = dates[currentIndex + 1];
          setCurrentDate(nextDate);
          onDateChange(nextDate);
        } else {
          setIsPlaying(false);
        }
      }, 1500);
    }
    return () => clearInterval(interval);
  }, [isPlaying, currentDate, dates, onDateChange]);

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const date = dates[parseInt(e.target.value)];
    setCurrentDate(date);
    onDateChange(date);
  };

  const currentIndex = dates.indexOf(currentDate);

  if (variant === 'compact') {
    const maxIdx = Math.max(0, dates.length - 1);
    const safeIndex = currentIndex >= 0 ? Math.min(currentIndex, maxIdx) : 0;
    return (
      <div
        className={`flex items-center gap-2 px-2 py-1 bg-white/90 backdrop-blur border border-slate-200/70 shadow-sm rounded-md ${className}`}
        title={`${startDate} → ${endDate}`}
      >
        <Calendar className="w-3 h-3 shrink-0 text-[#ED1C24]" aria-hidden />
        <span className="text-[10px] font-medium text-slate-800 tabular-nums shrink-0 min-w-[5.5rem]">
          {currentDate}
        </span>
        <input
          type="range"
          min="0"
          max={maxIdx}
          value={safeIndex}
          onChange={handleSliderChange}
          className="flex-1 min-w-[80px] max-w-md h-1 bg-slate-100 rounded-full appearance-none cursor-pointer accent-[#ED1C24] focus:outline-none"
          aria-label={`Timeline from ${startDate} to ${endDate}`}
        />
        <button
          type="button"
          onClick={() => setIsPlaying(!isPlaying)}
          className={`shrink-0 w-6 h-6 flex items-center justify-center rounded border border-slate-200 transition-colors ${
            isPlaying ? 'bg-[#ED1C24] text-white border-[#ED1C24]' : 'bg-white text-slate-500 hover:text-[#ED1C24]'
          }`}
          aria-label={isPlaying ? 'Pause timeline' : 'Play timeline'}
        >
          {isPlaying ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3 ml-px" />}
        </button>
      </div>
    );
  }

  return (
    <div className={`flex flex-col gap-5 px-10 py-8 bg-white/95 backdrop-blur-xl border border-slate-200 shadow-2xl rounded-[32px] ${className}`}>
      {/* Date Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
           <div className={`p-3 rounded-2xl border border-slate-100 bg-red-50`}>
             <Calendar className={`w-5 h-5 text-[#ED1C24]`} />
           </div>
           <div>
             <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Temporal Index</h4>
             <p className="text-xl font-black text-slate-900 tracking-tighter">
               {currentDate}
             </p>
           </div>
        </div>

        {/* Playback Controls */}
        <div className="flex items-center gap-3 bg-slate-50 p-2 rounded-2xl border border-slate-100">
          <button 
            onClick={() => setIsPlaying(!isPlaying)}
            className={`w-10 h-10 flex items-center justify-center rounded-xl transition-all ${
              isPlaying ? 'bg-[#ED1C24] text-white shadow-lg' : 'hover:bg-white text-slate-400 hover:text-[#ED1C24]'
            }`}
          >
            {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 ml-0.5" />}
          </button>
          <div className="w-px h-6 bg-slate-200 mx-1" />
          <div className="flex items-center gap-1 pr-2">
            <span className={`text-[10px] font-black uppercase tracking-widest px-3 py-1 rounded-lg ${isPlaying ? 'bg-red-100 text-[#ED1C24]' : 'text-slate-300'}`}>
              Story evolution {isPlaying ? 'Active' : 'Paused'}
            </span>
          </div>
        </div>
      </div>

      {/* Slider Core */}
      <div className="relative group pt-2">
        <input
          type="range"
          min="0"
          max={dates.length - 1}
          value={currentIndex}
          onChange={handleSliderChange}
          className="w-full h-1.5 bg-slate-100 rounded-full appearance-none cursor-pointer accent-[#ED1C24] transition-all hover:h-2 focus:outline-none"
        />
        
        {/* Progress Bar (Visual Overlay) */}
        <div 
          className="absolute h-1.5 top-2.5 left-0 pointer-events-none rounded-full bg-gradient-to-r from-[#ED1C24] to-[#FF4D4D] shadow-[0_0_12px_rgba(237,28,36,0.3)] transition-all"
          style={{ width: `${(currentIndex / (dates.length - 1)) * 100}%` }}
        />

        {/* Legend / Range labels */}
        <div className="flex items-center justify-between mt-5">
           <div className="flex flex-col items-start">
             <span className="text-[8px] font-black text-slate-300 uppercase tracking-widest mb-1">STORY_START</span>
             <span className="text-[10px] font-bold text-slate-400 bg-slate-50 px-3 py-1 rounded-lg border border-slate-100">{startDate}</span>
           </div>

           <div className="flex gap-4 items-center">
             <div className="w-2 h-2 rounded-full bg-slate-200 animate-pulse" />
             <div className="w-2 h-2 rounded-full bg-slate-200 animate-pulse [animation-delay:200ms]" />
             <div className="w-2 h-2 rounded-full bg-slate-200 animate-pulse [animation-delay:400ms]" />
           </div>

           <div className="flex flex-col items-end">
             <span className="text-[8px] font-black text-slate-300 uppercase tracking-widest mb-1">STORY_NOW</span>
             <span className="text-[10px] font-bold text-[#ED1C24] bg-red-50/50 px-3 py-1 rounded-lg border border-red-100">{endDate}</span>
           </div>
        </div>
      </div>
    </div>
  );
}
