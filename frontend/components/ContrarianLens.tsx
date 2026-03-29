'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, TrendingUp, TrendingDown, Info, ShieldAlert, ChevronRight } from 'lucide-react';

interface ContrarianPair {
  target: string;
  target_name: string;
  source1: string;
  source1_name: string;
  sentiment1: number;
  relationship1: string;
  evidence1: string;
  date1: string;
  source2: string;
  source2_name: string;
  sentiment2: number;
  relationship2: string;
  evidence2: string;
  date2: string;
  conflict_score: number;
}

interface ContrarianLensProps {
  contrarianPairs: ContrarianPair[];
  isEnabled: boolean;
  onToggle: () => void;
  className?: string;
  variant?: 'standard' | 'premium';
}

export default function ContrarianLens({ 
  contrarianPairs, 
  isEnabled, 
  onToggle, 
  className = '',
  variant = 'standard'
}: ContrarianLensProps) {
  const isPremium = variant === 'premium';

  return (
    <div className={`flex flex-col ${className}`}>
      {/* Header / Toggle */}
      <button
        onClick={onToggle}
        className={`w-full p-6 text-left transition-all relative overflow-hidden group ${
          isEnabled 
            ? 'bg-[#ED1C24] text-white' 
            : 'bg-white text-slate-900 border border-slate-200'
        } ${isPremium ? 'rounded-[32px]' : 'rounded-2xl shadow-lg'}`}
      >
        <div className="flex items-center justify-between relative z-10">
          <div className="flex items-center gap-3">
             <div className={`p-2 rounded-xl border ${isEnabled ? 'bg-white/20 border-white/30' : 'bg-red-50 border-red-100'}`}>
               <ShieldAlert className={`w-5 h-5 ${isEnabled ? 'text-white' : 'text-[#ED1C24]'}`} />
             </div>
             <div>
               <h3 className="text-sm font-black uppercase tracking-tight">Contrarian Lens</h3>
               <p className={`text-[10px] font-bold uppercase tracking-widest mt-0.5 ${isEnabled ? 'text-white/70' : 'text-slate-400'}`}>
                 Sentiment Conflict Detection
               </p>
             </div>
          </div>
          <div className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest border ${
            isEnabled ? 'bg-white text-[#ED1C24] border-white' : 'bg-slate-100 text-slate-400 border-slate-200'
          }`}>
            {isEnabled ? 'Activated' : 'Off'}
          </div>
        </div>
        
        {/* Animated Accent */}
        {isEnabled && (
          <motion.div 
            layoutId="active-accent"
            className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000"
          />
        )}
      </button>

      {/* Conflicts List */}
      <AnimatePresence>
        {isEnabled && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden bg-white/50"
          >
            <div className="pt-6 space-y-4">
              {contrarianPairs.length > 0 ? (
                contrarianPairs.map((pair, idx) => (
                  <motion.div
                    key={idx}
                    initial={{ x: -20, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    transition={{ delay: idx * 0.1 }}
                    className="p-5 bg-white border border-slate-200 rounded-3xl shadow-sm hover:shadow-md transition-all group"
                  >
                    <div className="flex items-center justify-between mb-4">
                      <div className="px-3 py-1 bg-red-100 text-[#ED1C24] text-[9px] font-black uppercase rounded-full">
                        Conflict Delta: {pair.conflict_score.toFixed(2)}
                      </div>
                      <span className="text-[9px] font-bold text-slate-400 uppercase">{pair.date1}</span>
                    </div>

                    <h4 className="text-sm font-black text-slate-900 mb-4 tracking-tight uppercase">
                      Analysis: <span className="text-[#ED1C24]">{pair.target_name}</span>
                    </h4>

                    <div className="grid grid-cols-2 gap-4">
                      {/* Bullish Source */}
                      <div className="p-3 bg-red-50/50 rounded-2xl border border-red-50/20">
                        <div className="flex items-center gap-1 text-[9px] font-bold text-red-600 uppercase mb-1">
                          <TrendingUp className="w-3 h-3" /> Positive
                        </div>
                        <p className="text-[10px] font-black text-slate-800 line-clamp-1">{pair.source1_name}</p>
                        <p className="text-[8px] text-slate-400 mt-1 uppercase font-bold">{pair.relationship1}</p>
                        <div className="mt-2 h-1 bg-red-100 rounded-full overflow-hidden">
                           <div className="h-full bg-red-500" style={{ width: `${pair.sentiment1 * 100}%` }} />
                        </div>
                      </div>

                      {/* Bearish Source */}
                      <div className="p-3 bg-slate-100/50 rounded-2xl border border-slate-200">
                        <div className="flex items-center gap-1 text-[9px] font-bold text-slate-500 uppercase mb-1">
                          <TrendingDown className="w-3 h-3" /> Negative
                        </div>
                        <p className="text-[10px] font-black text-slate-800 line-clamp-1">{pair.source2_name}</p>
                        <p className="text-[8px] text-slate-400 mt-1 uppercase font-bold">{pair.relationship2}</p>
                        <div className="mt-2 h-1 bg-slate-200 rounded-full overflow-hidden">
                           <div className="h-full bg-slate-600" style={{ width: `${Math.abs(pair.sentiment2) * 100}%` }} />
                        </div>
                      </div>
                    </div>

                    <div className="mt-4 p-4 bg-slate-50 rounded-2xl text-[10px] font-medium text-slate-600 leading-relaxed italic border-l-4 border-[#ED1C24]">
                      "The target {pair.target_name} is currently experiencing high narrative friction between {pair.source1_name} and {pair.source2_name}."
                    </div>
                  </motion.div>
                ))
              ) : (
                <div className="py-20 flex flex-col items-center justify-center opacity-40">
                  <ShieldAlert className="w-12 h-12 mb-4 text-slate-300" />
                  <p className="text-sm font-black text-slate-400 uppercase">No major conflicts detected</p>
                  <p className="text-xs text-slate-400 uppercase tracking-tighter mt-1">Narrative stability high</p>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
