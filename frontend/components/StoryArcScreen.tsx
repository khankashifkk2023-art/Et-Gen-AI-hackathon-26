'use client';

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  ArrowLeft, Brain, Search, Loader2, 
  Sparkles, Calendar, Activity, AlertTriangle,
  Layers, Globe, ChevronRight, CheckSquare, Square,
  XCircle, X
} from "lucide-react";
import StoryArcVisualizer from "./StoryArcVisualizer";
import TimeTravelSlider from "./TimeTravelSlider";
import ContrarianLens from "./ContrarianLens";
import ForceGraph3D from "./ForceGraph3D";
import { Article, Persona } from "@/types";
import { Skeleton } from "@/components/ui/Skeleton";

interface GraphData {
  nodes: any[];
  edges: any[];
}

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

interface StoryArcScreenProps {
  persona: Persona;
  articles: Article[];
  onBack: () => void;
}

export function StoryArcScreen({ persona, articles, onBack }: StoryArcScreenProps) {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [contrarianPairs, setContrarianPairs] = useState<ContrarianPair[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // UI state
  const [selectedDate, setSelectedDate] = useState<string | undefined>(undefined);
  const [showContrarian, setShowContrarian] = useState(false);
  const [viewMode, setViewMode] = useState<'2d' | '3d'>('2d');
  const [query, setQuery] = useState('');
  
  // Timeline bounds
  const [startDate, setStartDate] = useState<string>('2026-03-01');
  const [endDate, setEndDate] = useState<string>('2026-03-31');
  
  // Selection state
  const [availableArticles, setAvailableArticles] = useState<Article[]>([]);
  const [selectedArticleIds, setSelectedArticleIds] = useState<string[]>([]);
  const [fetchingArticles, setFetchingArticles] = useState(false);
  const [articlesDialogOpen, setArticlesDialogOpen] = useState(false);

  // BOTTLENECK FIX: Detect API host dynamically to avoid 'localhost' issues on separate networks
  const getApiBase = () => {
    if (typeof window !== 'undefined') {
      const hostname = window.location.hostname;
      if (hostname !== 'localhost' && !hostname.includes('127.0.0.1')) {
        return `http://${hostname}:8000`;
      }
    }
    return 'http://localhost:8000';
  };

  const API_BASE = getApiBase();

  // Fetch graph data
  const fetchStoryArc = async (searchQuery?: string) => {
    setLoading(true);
    setError(null);

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 120000); // 120 second timeout for GraphRAG

      const response = await fetch(`${API_BASE}/api/story-arc/extract`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: searchQuery || undefined,
          article_ids: selectedArticleIds.length > 0 ? selectedArticleIds : undefined,
          limit: selectedArticleIds.length > 0 ? selectedArticleIds.length : 5
        }),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`Knowledge Nexus Offline: ${response.statusText}`);
      }

      const data = await response.json();
      setGraphData(data.graph);
      
      if (data.timeline) {
        setStartDate(data.timeline.start_date || '2026-03-01');
        setEndDate(data.timeline.end_date || '2026-03-31');
        setSelectedDate(data.timeline.end_date || '2026-03-31');
      } else {
        setSelectedDate('2026-03-31');
      }

      const contrarianResponse = await fetch(`${API_BASE}/api/story-arc/contrarian`);
      if (contrarianResponse.ok) {
        const contrarianData = await contrarianResponse.json();
        setContrarianPairs(contrarianData.contrarian_pairs || []);
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Signal Lost: Network instability detected');
      console.error('Error fetching story arc:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStoryArc();
    fetchAvailableArticles();
  }, []);

  const fetchAvailableArticles = async () => {
    setFetchingArticles(true);
    try {
      const response = await fetch(`${API_BASE}/articles`);
      if (response.ok) {
        const data = await response.json();
        setAvailableArticles(data);
      }
    } catch (err) {
      console.error("Error fetching available articles:", err);
    } finally {
      setFetchingArticles(false);
    }
  };

  const toggleArticleSelection = (id: string) => {
    setSelectedArticleIds(prev => {
      if (prev.includes(id)) {
        return prev.filter(i => i !== id);
      }
      if (prev.length >= 10) return prev; // Limit to 10
      return [...prev, id];
    });
  };

  const clearSelection = () => setSelectedArticleIds([]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      fetchStoryArc(query);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[60] bg-[#F8FAFC] text-slate-800 flex flex-col overflow-hidden"
    >
      {/* ── Header ── */}
      <header className="px-6 py-4 bg-white border-b border-slate-200 shadow-sm flex items-center justify-between z-10">
        <div className="flex items-center gap-6">
          <button
            onClick={onBack}
            className="p-2 hover:bg-slate-100 border border-slate-100 rounded-lg transition-colors group"
          >
            <ArrowLeft className="w-5 h-5 text-slate-400 group-hover:text-[#ED1C24]" />
          </button>
          
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-[#ED1C24] rounded-full" />
              <h1 className="text-xl font-black tracking-tighter uppercase font-serif">Story Arc <span className="text-[#ED1C24]">Tracker</span></h1>
            </div>
            <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest flex items-center gap-2">
              <Globe className="w-3 h-3" /> Nexus Intelligence Unit • GraphRAG Service
            </p>
          </div>
        </div>

        <form onSubmit={handleSearch} className="flex-1 max-w-xl mx-8 relative group">
          <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
            <Search className="w-4 h-4 text-slate-400 group-focus-within:text-[#ED1C24] transition-colors" />
          </div>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Query the knowledge graph (e.g. 'Tata Motors EV strategy')"
            className="w-full pl-12 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium focus:outline-none focus:ring-2 focus:ring-[#ED1C24]/20 focus:border-[#ED1C24] focus:bg-white transition-all placeholder-slate-400"
          />
        </form>

        <div className="flex items-center gap-2 flex-wrap justify-end">
           <button
             type="button"
             onClick={() => setArticlesDialogOpen(true)}
             className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-200 bg-white text-[11px] font-semibold text-slate-700 hover:border-[#ED1C24]/40 hover:bg-red-50/50 transition-colors"
           >
             <Layers className="w-3.5 h-3.5 text-[#ED1C24]" />
             Articles
             <span className="text-[10px] font-bold text-slate-400 tabular-nums">
               {selectedArticleIds.length}/10
             </span>
           </button>
           <button
             type="button"
             onClick={() => fetchStoryArc()}
             disabled={loading || selectedArticleIds.length === 0}
             className={`inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-[11px] font-semibold transition-all ${
               selectedArticleIds.length > 0 && !loading
                 ? 'bg-[#ED1C24] text-white shadow-sm hover:bg-[#d41920]'
                 : 'bg-slate-200 text-slate-400 cursor-not-allowed'
             }`}
           >
             {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
             Generate arc
           </button>
           <div className="flex items-center bg-slate-100 p-1 rounded-lg border border-slate-200">
             <button
               type="button"
               onClick={() => setViewMode('2d')}
               className={`px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide rounded-md transition-all ${viewMode === '2d' ? 'bg-white text-[#ED1C24] shadow-sm' : 'text-slate-500 hover:text-slate-800'}`}
             >
               2D
             </button>
             <button
               type="button"
               onClick={() => setViewMode('3d')}
               className={`px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide rounded-md transition-all ${viewMode === '3d' ? 'bg-white text-[#ED1C24] shadow-sm' : 'text-slate-500 hover:text-slate-800'}`}
             >
               3D
             </button>
           </div>
           
           <div className="flex items-center gap-3 pl-3 border-l border-slate-200">
              <div className="text-right hidden sm:block">
                <p className="text-[10px] font-black text-[#ED1C24] uppercase tracking-tighter">{persona.name}</p>
                <p className="text-[8px] font-bold text-slate-400 uppercase tracking-widest">Nexus Profile Active</p>
              </div>
              <div className="w-10 h-10 rounded-xl bg-slate-900 text-white flex items-center justify-center border border-slate-700 shadow-md">
                 <Brain className="w-5 h-5 text-[#ED1C24]" />
              </div>
            </div>
        </div>
      </header>

      <main className="flex-1 flex flex-col relative min-h-0 bg-[#F1F5F9]/30">
        <div className="absolute inset-0 bg-[radial-gradient(#e2e8f0_1px,transparent_1px)] [background-size:24px_24px] opacity-50 pointer-events-none" />

        {/* Loading Overlay - Skeleton Mode */}
        <AnimatePresence>
          {loading && (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 z-50 bg-white/95 backdrop-blur-md flex flex-col"
            >
              <div className="flex-1 flex overflow-hidden">
                <div className="flex-1 p-12 flex flex-col items-center justify-center relative">
                   <div className="absolute inset-0 bg-[radial-gradient(#e2e8f0_1px,transparent_1px)] [background-size:24px_24px] opacity-30" />
                   <div className="relative w-48 h-48">
                      <Skeleton className="absolute inset-0 rounded-full bg-red-50/50 border-4 border-red-100/30 animate-pulse" />
                      <div className="absolute inset-0 flex items-center justify-center">
                        <Loader2 className="w-10 h-10 text-[#ED1C24] animate-spin" />
                      </div>
                   </div>
                   <div className="mt-8 text-center space-y-2">
                     <Skeleton className="h-6 w-56 mx-auto rounded-lg" />
                     <Skeleton className="h-3 w-40 mx-auto rounded-md" />
                   </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Error State */}
        {error && (
          <div className="absolute top-10 left-1/2 -translate-x-1/2 z-40 w-full max-w-lg">
            <div className="bg-white border-2 border-red-500 shadow-2xl p-5 rounded-2xl flex items-center gap-5 text-red-600">
               <div className="w-12 h-12 bg-red-100 rounded-xl flex items-center justify-center flex-shrink-0">
                 <AlertTriangle className="w-7 h-7" />
               </div>
               <div className="flex-1">
                 <p className="text-sm font-black uppercase tracking-tight">System Notification</p>
                 <p className="text-xs font-medium text-slate-500 mt-0.5">{error}</p>
               </div>
               <button 
                 onClick={() => fetchStoryArc()} 
                 className="px-6 py-2 bg-[#ED1C24] text-white text-[10px] font-black uppercase rounded-xl hover:scale-105 transition-transform"
               >
                 Retry
               </button>
            </div>
          </div>
        )}

        {/* Main Interface Layout — graph + insights; articles live in dialog */}
        <div className="flex-1 flex min-h-0 overflow-hidden">
          <section className="flex-1 min-h-0 relative flex flex-col">
            {graphData ? (
              <div className="flex-1 min-h-0 w-full relative">
                {viewMode === '2d' ? (
                  <StoryArcVisualizer
                    graphData={graphData}
                    selectedDate={selectedDate}
                    showContrarian={showContrarian}
                    className="h-full"
                    lightMode={true}
                  />
                ) : (
                  <ForceGraph3D
                    graphData={graphData}
                    selectedDate={selectedDate}
                    showContrarian={showContrarian}
                    className="h-full"
                    lightMode={true}
                  />
                )}
              </div>
            ) : !loading && (
              <div className="h-full flex flex-col items-center justify-center text-slate-200">
                <Globe className="w-32 h-32 mb-6" />
                <p className="text-2xl font-black uppercase tracking-tighter text-slate-400">Initialize Knowledge Exploration</p>
                <button 
                   onClick={() => fetchStoryArc()}
                   className="mt-6 px-10 py-3 bg-white border border-slate-200 text-slate-900 font-black uppercase rounded-2xl shadow-sm hover:shadow-md transition-all"
                >
                   Start Global extraction
                </button>
              </div>
            )}

            {graphData && (
              <div className="absolute top-3 left-3 pointer-events-none z-[5]">
                <div className="px-2.5 py-1.5 bg-white/90 backdrop-blur border border-slate-200/80 rounded-lg shadow-sm flex items-center gap-3 text-[11px] text-slate-700">
                  <span className="text-slate-500">Entities</span>
                  <span className="font-semibold tabular-nums">{graphData.nodes.length}</span>
                  <span className="text-slate-300">|</span>
                  <span className="text-slate-500">Links</span>
                  <span className="font-semibold tabular-nums">{graphData.edges.length}</span>
                </div>
              </div>
            )}
          </section>

          <aside className="w-[400px] shrink-0 min-h-0 bg-white border-l border-slate-200 flex flex-col shadow-2xl z-10 overflow-hidden">
            <div className="flex-1 min-h-0 overflow-y-auto p-8 space-y-8">
              <div className="bg-slate-50 border border-slate-100 rounded-[32px] overflow-hidden">
                <ContrarianLens
                  contrarianPairs={contrarianPairs}
                  isEnabled={showContrarian}
                  onToggle={() => setShowContrarian(!showContrarian)}
                  variant="premium"
                />
              </div>

              <div className="p-8 bg-white rounded-[32px] border border-slate-200 shadow-sm">
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-10 h-10 bg-red-50 rounded-2xl flex items-center justify-center">
                    <Sparkles className="w-5 h-5 text-[#ED1C24]" />
                  </div>
                  <h4 className="text-sm font-black uppercase tracking-tight text-slate-900">Discovery Engine</h4>
                </div>
                
                <p className="text-xs text-slate-500 leading-relaxed mb-6 font-medium">
                  Relational agents have predicted high-impact narrative shifts in these connected sectors:
                </p>

                <div className="space-y-3">
                  {['Regulation Trends', 'Competitor Shifts', 'Global Macro Impacts'].map((chip) => (
                    <button 
                      key={chip}
                      onClick={() => { setQuery(chip); fetchStoryArc(chip); }}
                      className="w-full text-left px-5 py-4 bg-slate-50 hover:bg-white border border-slate-100 hover:border-[#ED1C24]/30 rounded-2xl text-xs font-bold text-slate-700 hover:text-slate-900 transition-all flex items-center justify-between group shadow-sm hover:shadow-md"
                    >
                      {chip}
                      <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-[#ED1C24] transition-colors" />
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="shrink-0 px-8 py-6 border-t border-slate-100 bg-[#F8FAFC] flex items-center justify-between text-[9px] font-bold text-slate-400 tracking-wider">
              <div className="flex items-center gap-3">
                <div className="w-1.5 h-1.5 bg-green-500 rounded-full shadow-[0_0_8px_rgba(34,197,94,0.5)]" />
                <span className="uppercase font-mono">RELATION_ENGINE: ACTIVE</span>
              </div>
              <span className="font-mono">BUILD_032924_6RAG</span>
            </div>
          </aside>
        </div>

        <div className="shrink-0 px-3 py-1.5 border-t border-slate-200/80 bg-white/80 backdrop-blur-sm z-10">
          {startDate && endDate && (
            <TimeTravelSlider
              variant="compact"
              startDate={startDate}
              endDate={endDate}
              onDateChange={setSelectedDate}
              accentColor="#ED1C24"
              className="max-w-3xl mx-auto"
            />
          )}
        </div>
      </main>

      {/* Article selection — dialog so the graph stays full width */}
      <AnimatePresence>
        {articlesDialogOpen && (
          <motion.div
            className="fixed inset-0 z-[80] flex items-center justify-center p-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <button
              type="button"
              className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm"
              aria-label="Close dialog"
              onClick={() => setArticlesDialogOpen(false)}
            />
            <motion.div
              role="dialog"
              aria-modal="true"
              aria-labelledby="articles-dialog-title"
              initial={{ opacity: 0, scale: 0.96, y: 8 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96, y: 8 }}
              className="relative w-full max-w-lg max-h-[min(85vh,560px)] bg-white rounded-xl border border-slate-200 shadow-2xl flex flex-col overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-start justify-between gap-3 px-4 py-3 border-b border-slate-100 bg-slate-50/80">
                <div>
                  <h2 id="articles-dialog-title" className="text-sm font-semibold text-slate-900">
                    Select articles
                  </h2>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    Choose up to 10 sources, then run <span className="font-medium text-slate-700">Generate arc</span> in the header.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setArticlesDialogOpen(false)}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
                  aria-label="Close"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="flex-1 min-h-0 overflow-y-auto p-3 space-y-1 custom-scrollbar">
                {fetchingArticles ? (
                  Array(5).fill(0).map((_, i) => (
                    <div key={i} className="p-3 space-y-2">
                      <Skeleton className="h-3 w-3/4 rounded-full" />
                      <Skeleton className="h-2 w-1/2 rounded-full" />
                    </div>
                  ))
                ) : availableArticles.length > 0 ? (
                  availableArticles.map((article) => {
                    const isSelected = selectedArticleIds.includes(article.id);
                    return (
                      <button
                        key={article.id}
                        type="button"
                        onClick={() => toggleArticleSelection(article.id)}
                        className={`w-full text-left p-2.5 rounded-lg transition-colors border ${
                          isSelected
                            ? 'border-[#ED1C24]/35 bg-red-50/40'
                            : 'border-transparent hover:bg-slate-50'
                        }`}
                      >
                        <div className="flex gap-2.5">
                          <div className={`mt-0.5 shrink-0 ${isSelected ? 'text-[#ED1C24]' : 'text-slate-300'}`}>
                            {isSelected ? <CheckSquare className="w-4 h-4" /> : <Square className="w-4 h-4" />}
                          </div>
                          <div className="min-w-0 space-y-0.5">
                            <p className={`text-[12px] font-medium leading-snug ${isSelected ? 'text-slate-900' : 'text-slate-700'}`}>
                              {article.title}
                            </p>
                            <div className="flex items-center gap-1.5 text-[10px] text-slate-400">
                              <Calendar className="w-3 h-3 shrink-0" /> {article.date}
                            </div>
                          </div>
                        </div>
                      </button>
                    );
                  })
                ) : (
                  <div className="py-10 text-center text-slate-400">
                    <Activity className="w-8 h-8 mx-auto mb-2 opacity-40" />
                    <p className="text-xs">No articles available</p>
                  </div>
                )}
              </div>

              <div className="shrink-0 flex flex-wrap items-center justify-between gap-2 px-4 py-3 border-t border-slate-100 bg-slate-50/80">
                <div className="flex items-center gap-2">
                  <span className="text-[11px] text-slate-500 tabular-nums">{selectedArticleIds.length}/10 selected</span>
                  {selectedArticleIds.length > 0 && (
                    <button
                      type="button"
                      onClick={clearSelection}
                      className="text-[11px] font-medium text-slate-600 hover:text-red-600 inline-flex items-center gap-1"
                    >
                      <XCircle className="w-3.5 h-3.5" /> Clear
                    </button>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setArticlesDialogOpen(false)}
                    className="px-3 py-1.5 text-[11px] font-medium text-slate-600 hover:bg-slate-100 rounded-lg"
                  >
                    Done
                  </button>
                  <button
                    type="button"
                    disabled={loading || selectedArticleIds.length === 0}
                    onClick={() => {
                      fetchStoryArc();
                      setArticlesDialogOpen(false);
                    }}
                    className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-semibold ${
                      selectedArticleIds.length > 0 && !loading
                        ? 'bg-[#ED1C24] text-white hover:bg-[#d41920]'
                        : 'bg-slate-200 text-slate-400 cursor-not-allowed'
                    }`}
                  >
                    {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
                    Generate arc
                  </button>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
