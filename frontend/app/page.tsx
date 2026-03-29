"use client";

import { useMemo, useRef, useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Zap,
  TrendingUp,
  TrendingDown,
  Shield,
  User,
  Loader2,
  ArrowLeft,
  ChevronRight,
  Sparkles,
  BookOpen,
  Brain,
  RefreshCw,
  Calendar,
  Video,
  Play,
  PlayCircle,
  FileVideo,
} from "lucide-react";

import type { AnalysisResponse, Article, Persona, UserProfile, VideoResponse } from "@/types";
import { Skeleton, ArticleSkeleton, AnalysisSkeleton, StoryboardSkeleton } from "@/components/ui/Skeleton";
import { analyzeNews, fetchArticles, ingestFallback, generateVideo, API_BASE } from "@/lib/api";
import { prefetchVideoJobAssets } from "@/lib/videoPrefetch";
import { Player } from "@remotion/player";
import { ChatWidget } from "../components/ChatWidget";
import { NewsVideo } from "./video-studio/compositions/NewsVideo";
import { StoryArcScreen } from "@/components/StoryArcScreen";

function escapeXml(s: string) {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

function stringToHsl(input: string) {
  // Deterministically turn a string into a pleasant HSL color.
  let hash = 0;
  for (let i = 0; i < input.length; i++) hash = input.charCodeAt(i) + ((hash << 5) - hash);
  const hue = Math.abs(hash) % 360;
  return { h: hue, s: 78, l: 46 };
}

function getFallbackThumbnailDataUrl(article: Article) {
  const title = article.title ?? "";
  const tag = article.tags?.[0] ?? "News";
  const { h } = stringToHsl(title + "|" + tag);

  const bg1 = `hsl(${h} 78% 48%)`;
  const bg2 = `hsl(${(h + 35) % 360} 78% 42%)`;

  // Shorten text to fit the thumbnail while keeping it readable.
  const label = (tag || "News").slice(0, 18);
  const headline = (title || "ET Nexus").replace(/\s+/g, " ").slice(0, 44).trim();

  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="800" height="400" viewBox="0 0 800 400">
      <defs>
        <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stop-color="${bg1}" />
          <stop offset="1" stop-color="${bg2}" />
        </linearGradient>
        <filter id="noise">
          <feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="2" stitchTiles="stitch" />
          <feColorMatrix type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 .18 0"/>
        </filter>
      </defs>
      <rect width="800" height="400" fill="url(#g)" />
      <rect width="800" height="400" filter="url(#noise)" opacity="0.35" />
      <rect x="30" y="30" width="740" height="340" rx="22" fill="rgba(255,255,255,0.14)" stroke="rgba(255,255,255,0.22)" />

      <text x="56" y="106" font-family="ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial"
            font-size="18" font-weight="800" fill="rgba(255,255,255,0.92)">
        ${escapeXml(label.toUpperCase())}
      </text>
      <text x="56" y="170" font-family="ui-serif, Georgia, Cambria, Times New Roman, Times, serif"
            font-size="32" font-weight="800" fill="rgba(255,255,255,0.96)">
        ${escapeXml(headline)}
      </text>

      <text x="56" y="344" font-family="ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial"
            font-size="14" font-weight="700" fill="rgba(255,255,255,0.85)">
        ET Nexus • Economic Times
      </text>
    </svg>
  `;

  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

// ─── Demo Personas ─────────────────────────────────────────────

const DEMO_PERSONAS: Persona[] = [
  {
    user_id: "student_01",
    name: "Student",
    persona: "curious_student",
    level: "beginner",
    portfolio: [],
    interests: ["technology", "startups", "AI"],
  },
  {
    user_id: "investor_01",
    name: "Retail Investor",
    persona: "retail_investor",
    level: "intermediate",
    portfolio: ["TATAMOTORS", "HDFCBANK", "INFY"],
    interests: ["auto", "banking", "IT"],
  },
  {
    user_id: "fund_mgr_01",
    name: "Fund Manager",
    persona: "fund_manager",
    level: "expert",
    portfolio: ["RELIANCE", "TCS", "HDFCBANK", "TATAMOTORS", "ICICIBANK"],
    interests: ["markets", "macro", "policy"],
  },
  {
    user_id: "founder_01",
    name: "Startup Founder",
    persona: "startup_founder",
    level: "intermediate",
    portfolio: ["INFY", "WIPRO"],
    interests: ["AI", "SaaS", "funding"],
  },
];

const PERSONA_META: Record<string, { role: string; icon: string; desc: string }> = {
  curious_student: { role: "Student", icon: "🎓", desc: "Simplified explanations with learning context" },
  retail_investor: { role: "Retail Investor", icon: "📈", desc: "Portfolio impact analysis with actionable insights" },
  fund_manager: { role: "Fund Manager", icon: "🏦", desc: "Deep macro analysis with risk quantification" },
  startup_founder: { role: "Startup Founder", icon: "🚀", desc: "Tech trends and funding ecosystem perspective" },
};

type Screen = "welcome" | "persona" | "home" | "article" | "video_studio" | "story_arc";

// ─── Main Page ─────────────────────────────────────────────────

export default function Home() {
  const [screen, setScreen] = useState<Screen>("welcome");
  const [selectedPersona, setSelectedPersona] = useState<Persona | null>(null);
  const [articles, setArticles] = useState<Article[]>([]);
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [isLoadingArticles, setIsLoadingArticles] = useState(false);
  const [isLoadingAnalysis, setIsLoadingAnalysis] = useState(false);
  const [isIngesting, setIsIngesting] = useState(false);
  const [ingested, setIngested] = useState(false);
  const [videoJob, setVideoJob] = useState<VideoResponse | null>(null);
  const [isGeneratingVideo, setIsGeneratingVideo] = useState(false);
  const [videoError, setVideoError] = useState<string | null>(null);

  // Load articles when reaching home screen
  useEffect(() => {
    if (screen === "home") {
      loadArticles();
    }
  }, [screen]);

  const loadArticles = async (category?: string) => {
    setIsLoadingArticles(true);
    try {
      const catParam = category === "All" ? undefined : category;
      const data = await fetchArticles(catParam);
      setArticles(data);
    } catch {
      setArticles([]);
    } finally {
      setIsLoadingArticles(false);
    }
  };

  const handleIngest = async () => {
    setIsIngesting(true);
    try {
      await ingestFallback();
      setIngested(true);
      await loadArticles();
    } catch {
      // silent fail
    } finally {
      setIsIngesting(false);
    }
  };

  const handleSelectPersona = (p: Persona) => {
    setSelectedPersona(p);
    setScreen("home");
  };

  const handleSelectArticle = async (article: Article) => {
    setSelectedArticle(article);
    setAnalysis(null);
    setScreen("article");

    // Auto-run analysis
    if (!selectedPersona) return;
    setIsLoadingAnalysis(true);
    try {
      const userProfile: UserProfile = {
        user_id: selectedPersona.user_id,
        name: selectedPersona.name,
        persona: selectedPersona.persona,
        level: selectedPersona.level,
        portfolio: selectedPersona.portfolio,
        interests: selectedPersona.interests,
      };
      const result = await analyzeNews({ query: article.title, user_profile: userProfile });
      setAnalysis(result);
    } catch {
      setAnalysis(null);
    } finally {
      setIsLoadingAnalysis(false);
    }
  };

  const handleGenerateVideo = async (article: Article, analysisData: AnalysisResponse) => {
    setIsGeneratingVideo(true);
    setVideoError(null);
    setVideoJob(null);
    setScreen("video_studio");

    try {
      const data = await generateVideo({
        article_title: article.title,
        summary: analysisData.summary,
        bull_view: analysisData.ui_metadata.bull,
        bear_view: analysisData.ui_metadata.bear,
      });
      await prefetchVideoJobAssets(data, API_BASE);
      setVideoJob(data);
    } catch (err: any) {
      setVideoError(err.message || "Failed to generate video briefing");
    } finally {
      setIsGeneratingVideo(false);
    }
  };

  const handleBack = () => {
    if (screen === "article") {
      setScreen("home");
      setSelectedArticle(null);
      setAnalysis(null);
    } else if (screen === "home") {
      setScreen("persona");
    }
  };

  return (
    <div className="min-h-screen bg-white text-[#1A1A1A]">
      <AnimatePresence mode="wait">
        {screen === "welcome" && (
          <WelcomeScreen key="welcome" onStart={() => setScreen("persona")} />
        )}
        {screen === "persona" && (
          <PersonaScreen key="persona" onSelect={handleSelectPersona} />
        )}
        {screen === "home" && selectedPersona && (
          <HomeScreen
            key="home"
            persona={selectedPersona}
            articles={articles}
            isLoading={isLoadingArticles}
            isIngesting={isIngesting}
            ingested={ingested}
            onSelectArticle={handleSelectArticle}
            onIngest={handleIngest}
            onRefresh={loadArticles}
            onChangePersona={() => setScreen("persona")}
            onOpenVideoStudio={() => setScreen("video_studio")}
            onOpenStoryArc={() => setScreen("story_arc")}
          />
        )}
        {screen === "article" && selectedArticle && selectedPersona && (
          <ArticleScreen
            key="article"
            article={selectedArticle}
            persona={selectedPersona}
            analysis={analysis}
            isLoading={isLoadingAnalysis}
            onBack={handleBack}
            onGenerateVideo={handleGenerateVideo}
            onViewStoryArc={(article) => {
              setSelectedArticle(article);
              setScreen("story_arc");
            }}
          />
        )}
        {screen === "video_studio" && selectedPersona && (
          <VideoStudioScreen
            key="video_studio"
            persona={selectedPersona}
            articles={articles}
            videoJob={videoJob}
            isGenerating={isGeneratingVideo}
            error={videoError}
            onGenerate={handleGenerateVideo}
            onClearVideo={() => setVideoJob(null)}
            onBack={() => setScreen("home")}
          />
        )}
        {screen === "story_arc" && selectedPersona && (
          <StoryArcScreen
            key="story_arc"
            persona={selectedPersona}
            articles={articles}
            onBack={() => setScreen("home")}
          />
        )}
      </AnimatePresence>
      <ChatWidget 
        userName={selectedPersona?.name} 
        articleText={screen === "article" && selectedArticle ? (selectedArticle.content || `${selectedArticle.title}\n\n${analysis?.summary || ""}`) : undefined}
      />
    </div>
  );
}

// ─── Shared Components ────────────────────────────────────────

function Logo({ className = "", light = false }: { className?: string; light?: boolean }) {
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <div className="flex flex-col items-start -space-y-0.5">
        <span className={`text-[8px] font-black tracking-[0.2em] uppercase leading-none ${light ? 'text-white/80' : 'text-[#101723]/60'}`}>The</span>
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 bg-[#ED1C24] flex items-center justify-center rounded-sm shadow-sm rotate-[-2deg]">
             <span className="text-white font-serif font-black text-lg">E</span>
          </div>
          <div className="flex flex-col -space-y-1">
            <h1 className={`text-xl font-serif font-black tracking-tight leading-none ${light ? 'text-white' : 'text-[#101723]'}`}>
              ECONOMIC <span className="text-[#ED1C24]">TIMES</span>
            </h1>
            <span className={`text-[9px] font-bold tracking-[0.15em] ${light ? 'text-white/40' : 'text-gray-300'}`}>INTELLIGENCE UNIT</span>
          </div>
        </div>
      </div>
      <div className={`h-8 w-px ${light ? 'bg-white/20' : 'bg-gray-100'} mx-1`} />
      <span className={`text-lg font-sans font-extrabold tracking-tighter ${light ? 'text-white/90' : 'text-[#ED1C24]'}`}>NEXUS</span>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// SCREEN 1: WELCOME
// ═══════════════════════════════════════════════════════════════

function WelcomeScreen({ onStart }: { onStart: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="min-h-screen flex flex-col items-center justify-center relative overflow-hidden bg-white"
    >
      {/* Background accent */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_bottom_left,_var(--et-beige)_0%,_transparent_40%)]" />
      <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-[#ED1C24]/3 rounded-full blur-[100px] -translate-y-1/2 translate-x-1/2" />

      <motion.div
        initial={{ y: 30, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.2, duration: 0.6 }}
        className="relative z-10 text-center max-w-2xl px-6"
      >
        <Logo className="mb-12 justify-center scale-125 origin-center" />

        <h2 className="text-4xl md:text-5xl font-serif font-black tracking-tight mb-6 leading-tight text-[#101723]">
          Next-Gen News <br/> 
          <span className="italic text-[#ED1C24]">Reimagined.</span>
        </h2>

        <p className="text-lg text-gray-500 font-medium mb-10 max-w-md mx-auto leading-relaxed">
          The precision of Economic Times meets the power of Agentic AI. Hyper-personalized intelligence for the modern visionary.
        </p>

        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={onStart}
          className="px-10 py-4 bg-[#101723] text-white font-bold text-xs uppercase tracking-[0.2em] rounded-full hover:bg-black transition-all shadow-2xl shadow-black/20 flex items-center gap-3 mx-auto"
        >
          Begin Discovery
          <ChevronRight className="w-4 h-4" />
        </motion.button>

        <div className="mt-16 pt-8 border-t border-gray-100">
           <p className="text-[10px] text-gray-400 uppercase tracking-[0.3em] font-black">
            Powered by Multi-Agent RAG • GenAI Hackathon 2026
          </p>
        </div>
      </motion.div>
    </motion.div>
  );
}

// ═══════════════════════════════════════════════════════════════
// SCREEN 2: PERSONA SELECTION
// ═══════════════════════════════════════════════════════════════

function PersonaScreen({ onSelect }: { onSelect: (p: Persona) => void }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="min-h-screen flex flex-col items-center justify-center px-6 py-12"
    >
      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.1 }}
        className="text-center mb-12"
      >
        <div className="w-10 h-10 bg-[#FDE9E4] rounded-lg flex items-center justify-center mx-auto mb-4">
          <User className="w-5 h-5 text-[#ED1C24]" />
        </div>
        <h2 className="text-3xl md:text-4xl font-serif font-black mb-3">Choose Your Persona</h2>
        <p className="text-gray-500 text-sm max-w-md mx-auto">
          ET Nexus tailors every insight to your experience level and portfolio.
        </p>
      </motion.div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 w-full max-w-3xl">
        {DEMO_PERSONAS.map((p, i) => {
          const meta = PERSONA_META[p.persona] || { role: p.persona, icon: "👤", desc: "" };
          return (
            <motion.button
              key={p.user_id}
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.15 + i * 0.08 }}
              onClick={() => onSelect(p)}
              className="group p-6 text-left bg-white border-2 border-gray-100 rounded-xl hover:border-[#ED1C24] hover:shadow-xl hover:shadow-[#ED1C24]/5 transition-all duration-300"
            >
              <div className="flex items-start gap-4">
                <div className="text-3xl">{meta.icon}</div>
                <div className="flex-1">
                  <h3 className="text-lg font-bold mb-0.5 text-[#ED1C24] uppercase tracking-tighter">{meta.role}</h3>
                  <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Profile Active</p>
                  <p className="text-xs text-gray-500 leading-relaxed mb-3">{meta.desc}</p>
                  {p.portfolio.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {p.portfolio.map(tk => (
                        <span key={tk} className="text-[10px] font-bold px-2 py-0.5 bg-gray-50 border border-gray-100 rounded text-gray-600">
                          {tk}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <ChevronRight className="w-5 h-5 text-gray-300 group-hover:text-[#ED1C24] transition-colors mt-1" />
              </div>
            </motion.button>
          );
        })}
      </div>
    </motion.div>
  );
}

// ═══════════════════════════════════════════════════════════════
// SCREEN 3: HOME — ARTICLE GRID
// ═══════════════════════════════════════════════════════════════

interface HomeScreenProps {
  persona: Persona;
  articles: Article[];
  isLoading: boolean;
  isIngesting: boolean;
  ingested: boolean;
  onSelectArticle: (a: Article) => void;
  onIngest: () => void;
  onRefresh: (category?: string) => void;
  onChangePersona: () => void;
  onOpenVideoStudio: () => void;
  onOpenStoryArc: () => void;
}

function HomeScreen({
  persona,
  articles,
  isLoading,
  isIngesting,
  ingested,
  onSelectArticle,
  onIngest,
  onRefresh,
  onChangePersona,
  onOpenVideoStudio,
  onOpenStoryArc,
}: HomeScreenProps) {
  const [activeCategory, setActiveCategory] = useState<string>("All");

  const categories = [
    "All", "Markets", "Politics", "Tech", "Economy", "Startups", 
    "Wealth", "Industry", "Environment", "International", "Opinion", "Mutual Funds"
  ];

  // Refetch when category changes for 'Live' experience
  useEffect(() => {
    onRefresh(activeCategory);
  }, [activeCategory]);

  const filteredArticles = useMemo(() => {
    if (activeCategory === "All") return articles;
    return articles.filter(a => (a.tags ?? []).includes(activeCategory));
  }, [articles, activeCategory]);



  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="min-h-screen bg-[#FAFAFA]"
    >
      {/* ── Header ── */}
      <header className="bg-white/80 backdrop-blur-md border-b border-gray-100 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
          <Logo />

          <div className="flex items-center gap-3">
            <button
              onClick={onOpenVideoStudio}
              className="flex items-center gap-2 px-4 py-2 text-[11px] font-bold uppercase tracking-wider bg-[#101723] text-white rounded-lg hover:bg-black transition-colors shadow-lg shadow-navy-900/10"
            >
              <Video className="w-4 h-4" />
              <span>Video Studio</span>
            </button>
            <button
               onClick={() => onOpenStoryArc()}
               className="flex items-center gap-2 px-4 py-2 text-[11px] font-bold uppercase tracking-wider bg-white border border-[#ED1C24]/20 text-[#ED1C24] rounded-lg hover:bg-[#FDE9E4] transition-colors shadow-sm"
             >
               <Brain className="w-4 h-4" />
               <span>Story Arc</span>
             </button>
            <button
              onClick={() => onRefresh(activeCategory)}
              className="p-2 text-gray-400 hover:text-[#ED1C24] transition-colors rounded-lg hover:bg-gray-50"
              title="Refresh articles"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button
              onClick={onIngest}
              disabled={isIngesting}
              className="px-4 py-2 text-[11px] font-bold uppercase tracking-wider border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
            >
              {isIngesting ? "Loading..." : ingested ? "✓ Data Ready" : "Load Data"}
            </button>
            <button
              onClick={onChangePersona}
              className="flex items-center gap-2 px-3 py-2 bg-[#FDE9E4] border border-[#ED1C24]/10 rounded-lg hover:border-[#ED1C24]/30 transition-colors"
            >
              <span className="text-base">{PERSONA_META[persona.persona]?.icon || "👤"}</span>
              <span className="text-xs font-black text-[#ED1C24] uppercase tracking-tighter">{persona.name}</span>
            </button>
          </div>
        </div>
      </header>

      {/* ── Content ── */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-2xl font-serif font-black">Latest News</h2>
            <p className="text-sm text-gray-500 mt-1">
              Choose a category, then tap any story for AI-powered analysis tailored to your profile
            </p>
          </div>
          <div className="text-right">
            <span className="text-xs font-bold text-gray-400 uppercase tracking-wider block">
              {filteredArticles.length} shown
            </span>
            <span className="text-[11px] text-gray-400">
              Category: <span className="font-bold text-gray-600">{activeCategory}</span>
            </span>
          </div>
        </div>

        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8 pt-2">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <ArticleSkeleton key={i} />
            ))}
          </div>
        ) : articles.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 border-2 border-dashed border-gray-200 rounded-xl">
            <BookOpen className="w-10 h-10 text-gray-300 mb-4" />
            <p className="text-gray-500 font-medium mb-2">No articles yet</p>
            <p className="text-sm text-gray-400 mb-6">Load the fallback dataset to get started</p>
            <button
              onClick={onIngest}
              disabled={isIngesting}
              className="px-6 py-2 bg-[#ED1C24] text-white text-sm font-bold rounded-lg hover:bg-[#d4171e] transition-colors disabled:opacity-50"
            >
              {isIngesting ? "Loading..." : "Load Articles"}
            </button>
          </div>
        ) : (
          <div className="space-y-5">
            {/* Category chips */}
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[11px] font-bold text-gray-400 uppercase tracking-wider mr-1">
                Browse by topic
              </span>
              {categories.map(cat => {
                const selected = cat === activeCategory;
                return (
                  <button
                    key={cat}
                    type="button"
                    onClick={() => setActiveCategory(cat)}
                    className={
                      "px-3 py-1.5 rounded-full text-[11px] font-bold border transition-colors " +
                      (selected
                        ? "bg-[#ED1C24] text-white border-[#ED1C24]"
                        : "bg-white text-gray-600 border-gray-200 hover:border-[#ED1C24]/40 hover:text-[#ED1C24]")
                    }
                    aria-pressed={selected}
                    title={cat === "All" ? "Show all news" : `Show ${cat} news`}
                  >
                    {cat === "All" ? "All News" : cat}
                  </button>
                );
              })}
            </div>

            {/* Feed header */}
            <div className="flex items-center justify-between border-b border-gray-100 pb-4">
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-6 bg-[#ED1C24] rounded-full" />
                <span className="text-lg font-black font-serif text-[#101723]">
                  {activeCategory === "All" ? "Top Intelligence Briefs" : `${activeCategory} Special Reports`}
                </span>
                <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest ml-2 px-2 py-0.5 bg-gray-50 rounded">
                  Personalized for {persona.name}
                </span>
              </div>
            </div>

            {/* Articles Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8 pt-2">
              {filteredArticles.map((article, i) => (
                <ArticleCard
                  key={article.id + i}
                  article={article}
                  index={i}
                  onClick={() => onSelectArticle(article)}
                />
              ))}
              {filteredArticles.length === 0 && (
                <div className="w-full border-2 border-dashed border-gray-200 rounded-xl p-10 text-center bg-white">
                  <p className="text-gray-500 font-medium mb-1">No stories in this category yet</p>
                  <p className="text-sm text-gray-400">Try a different topic or load fresh data.</p>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </motion.div>
  );
}

// ─── Article Card Component ─────────────────────────────────────

function ArticleCard({ article, index, onClick }: { article: Article; index: number; onClick: () => void }) {
  const thumbnailUrl =
    article.image_url && article.image_url.trim().length > 0 && !article.image_url.includes("placeholder")
      ? article.image_url
      : getFallbackThumbnailDataUrl(article);

  return (
    <motion.div
      initial={{ y: 20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ delay: index * 0.05 }}
      onClick={onClick}
      className="group bg-white rounded-xl border border-gray-100 overflow-hidden cursor-pointer hover:shadow-lg hover:shadow-black/5 hover:border-[#ED1C24]/20 transition-all duration-300"
    >
      {/* Thumbnail */}
      <div className="h-48 bg-gradient-to-br from-gray-100 to-gray-50 relative overflow-hidden">
        <img
          src={thumbnailUrl}
          alt={article.title}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
          loading="lazy"
        />
        {/* Tag overlay */}
        {article.tags?.[0] && (
          <div className="absolute top-3 left-3">
            <span className="px-2 py-1 bg-[#ED1C24] text-white text-[10px] font-bold uppercase tracking-wider rounded">
              {article.tags[0]}
            </span>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-6">
        <h3 className="font-serif font-bold text-lg leading-tight mb-3 group-hover:text-[#ED1C24] transition-colors line-clamp-2">
          {article.title}
        </h3>
        <p className="text-[13px] text-gray-500 font-medium leading-relaxed mb-5 line-clamp-3">
          {article.summary}
        </p>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-[11px] text-gray-400">
            <Calendar className="w-3 h-3" />
            <span>{article.date}</span>
          </div>
          <div className="flex gap-1.5">
            {article.tags?.slice(1, 3).map(tag => (
              <span key={tag} className="text-[9px] font-bold px-1.5 py-0.5 bg-gray-50 text-gray-500 rounded">
                {tag}
              </span>
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

// ═══════════════════════════════════════════════════════════════
// SCREEN 4: ARTICLE DETAIL + AI AGENTS
// ═══════════════════════════════════════════════════════════════

interface ArticleScreenProps {
  article: Article;
  persona: Persona;
  analysis: AnalysisResponse | null;
  isLoading: boolean;
  onBack: () => void;
  onGenerateVideo: (article: Article, analysis: AnalysisResponse) => void;
  onViewStoryArc: (article: Article) => void;
}

function ArticleScreen({ article, persona, analysis, isLoading, onBack, onGenerateVideo, onViewStoryArc }: ArticleScreenProps) {
  const meta = PERSONA_META[persona.persona] || { role: persona.persona, icon: "👤" };
  const hasImage = article.image_url && !article.image_url.includes("placeholder");

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="min-h-screen bg-white"
    >
      <header className="bg-white/90 backdrop-blur-md border-b border-gray-100 sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-2 flex items-center justify-between">
          <button
            onClick={onBack}
            className="group flex items-center gap-2 text-[#ED1C24] font-extrabold text-[10px] uppercase tracking-wider hover:text-black transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5 group-hover:-translate-x-1 transition-transform" /> Back
          </button>
          <Logo className="scale-75 origin-center" />
          <div className="flex items-center gap-2 px-3 py-1 bg-gray-50 rounded-full border border-gray-100">
            <span className="text-sm">{meta.icon}</span>
            <span className="text-[10px] font-black text-[#ED1C24] uppercase tracking-tighter">{persona.name}</span>
          </div>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
        {/* ── Article Header ── */}
        <div className="mb-10">
          {/* Tags */}
          <div className="flex gap-2 mb-4">
            {article.tags?.map(tag => (
              <span key={tag} className="px-2.5 py-1 bg-[#FDE9E4] text-[#ED1C24] text-[10px] font-bold uppercase tracking-wider rounded">
                {tag}
              </span>
            ))}
          </div>

          {/* Title */}
          <h1 className="text-3xl md:text-4xl font-serif font-black leading-tight mb-4">
            {article.title}
          </h1>

          {/* Meta */}
          <div className="flex items-center gap-4 text-sm text-gray-500 mb-6">
            <div className="flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5" />
              <span>{article.date}</span>
            </div>
            <span>•</span>
            <span className="text-[#ED1C24] font-medium">Economic Times</span>
          </div>

          {/* Banner Image */}
          {hasImage && (
            <div className="w-full h-64 md:h-80 rounded-xl overflow-hidden mb-6 bg-gray-100">
              <img
                src={article.image_url!}
                alt={article.title}
                className="w-full h-full object-cover"
                onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
              />
            </div>
          )}

          {/* Article Summary */}
          <div className="prose max-w-none">
            <p className="text-lg md:text-xl leading-relaxed text-gray-700 font-medium 
                        first-letter:text-6xl first-letter:font-serif first-letter:font-black 
                        first-letter:float-left first-letter:mr-3 first-letter:text-[#101723] 
                        first-letter:leading-[0.8] first-letter:mt-1
                        drop-shadow-sm">
              {article.summary}
            </p>
          </div>
        </div>

        {/* ── Divider ── */}
        <div className="border-t-2 border-[#ED1C24] pt-8 mb-8">
          <div className="flex items-center gap-2 mb-2">
            <Brain className="w-5 h-5 text-[#ED1C24]" />
            <h2 className="text-xl font-serif font-black">AI Agent Analysis</h2>
          </div>
          <p className="text-sm text-gray-500">
            Multi-agent synthesis personalized for <strong className="text-[#ED1C24]">{persona.name}</strong>
          </p>
        </div>

        {/* ── AI Analysis Section ── */}
        {isLoading ? (
          <div className="py-10">
            <AnalysisSkeleton />
          </div>
        ) : analysis ? (
          <div className="space-y-6">
            {/* 🎬 Video Briefing CTA */}
            <div className="bg-gradient-to-r from-[#101723] to-[#1A2639] rounded-2xl p-6 mb-8 flex flex-col md:flex-row items-center justify-between gap-6 border border-white/10 shadow-2xl">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-[#ED1C24] rounded-2xl flex items-center justify-center shadow-lg shadow-red-500/20">
                  <PlayCircle className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="text-white font-serif font-black text-xl">Generate AI News Briefing</h3>
                  <p className="text-gray-400 text-sm">Transform this analysis into a 60-second broadcast video</p>
                </div>
              </div>
              <button
                onClick={() => onGenerateVideo(article, analysis)}
                className="w-full md:w-auto px-8 py-4 bg-[#ED1C24] text-white rounded-xl font-black uppercase tracking-widest hover:bg-[#C4121B] transition-all transform hover:scale-105 active:scale-95 shadow-xl shadow-red-500/20 flex items-center justify-center gap-3"
              >
                <Sparkles className="w-5 h-5" />
                Create Briefing
              </button>
              <button
                onClick={() => onViewStoryArc(article)}
                className="w-full md:w-auto px-8 py-4 bg-white border-2 border-[#ED1C24] text-[#ED1C24] rounded-xl font-black uppercase tracking-widest hover:bg-[#FDE9E4] transition-all transform hover:scale-105 active:scale-95 shadow-lg flex items-center justify-center gap-3"
              >
                <Brain className="w-5 h-5" />
                View Story Arc
              </button>
            </div>

            {/* Agent 1: AI Summarizer */}
            <div className="bg-white rounded-2xl p-8 border border-gray-100 shadow-xl shadow-black/5 relative overflow-hidden group">
              <div className="absolute top-0 right-0 w-32 h-32 bg-[#ED1C24]/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2 group-hover:bg-[#ED1C24]/10 transition-colors" />
              <div className="flex items-center gap-3 mb-6">
                <div className="w-10 h-10 bg-[#101723] rounded-xl flex items-center justify-center shadow-lg">
                  <Sparkles className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="text-xs font-black uppercase tracking-[0.2em] text-[#101723]">Executive Briefing</h3>
                  <p className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">AI Synthesis Engine • Confidence: {Math.round(analysis.confidence * 100)}%</p>
                </div>
              </div>
              <h4 className="font-serif font-black text-2xl mb-4 leading-tight text-[#101723]">{analysis.headline}</h4>
              <p className="text-[15px] leading-relaxed text-gray-600 whitespace-pre-line font-medium">{analysis.summary}</p>
            </div>

            {/* Agent 2 & 3: Bull / Bear side by side */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {/* Bull Agent */}
              <div className="bg-emerald-50/50 rounded-xl p-6 border border-emerald-100">
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-8 h-8 bg-emerald-600 rounded-lg flex items-center justify-center">
                    <TrendingUp className="w-4 h-4 text-white" />
                  </div>
                  <div>
                    <h3 className="text-sm font-black uppercase tracking-wide text-emerald-800">Bull Agent</h3>
                    <p className="text-[10px] text-emerald-500">Bullish perspective</p>
                  </div>
                </div>
                <p className="text-sm leading-relaxed text-gray-700">{analysis.ui_metadata.bull}</p>
              </div>

              {/* Bear Agent */}
              <div className="bg-red-50/50 rounded-xl p-6 border border-red-100">
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-8 h-8 bg-[#ED1C24] rounded-lg flex items-center justify-center">
                    <TrendingDown className="w-4 h-4 text-white" />
                  </div>
                  <div>
                    <h3 className="text-sm font-black uppercase tracking-wide text-[#ED1C24]">Bear Agent</h3>
                    <p className="text-[10px] text-red-400">Bearish perspective</p>
                  </div>
                </div>
                <p className="text-sm leading-relaxed text-gray-700">{analysis.ui_metadata.bear}</p>
              </div>
            </div>

            {/* Agent 4: Context Engine — Sources */}
            <div className="bg-white rounded-xl p-6 border-2 border-gray-100">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 bg-[#FDE9E4] rounded-lg flex items-center justify-center">
                  <Shield className="w-4 h-4 text-[#ED1C24]" />
                </div>
                <div>
                  <h3 className="text-sm font-black uppercase tracking-wide">Context Engine</h3>
                  <p className="text-[10px] text-gray-400">Source-grounded facts — {analysis.sources.length} relevant chunks</p>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {analysis.sources.slice(0, 3).map((s, i) => (
                  <div key={i} className="p-4 bg-gray-50 rounded-lg border border-gray-100 hover:border-[#ED1C24]/30 transition-colors">
                    <p className="text-xs font-bold leading-snug mb-2">{s.title}</p>
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-gray-400">{s.date}</span>
                      <span className="text-[9px] font-bold px-1.5 py-0.5 bg-[#FDE9E4] text-[#ED1C24] rounded">{s.tags?.[0]}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Safety Disclaimer */}
            {analysis.ui_metadata.disclaimer && (
              <div className="p-4 bg-gray-50 border-l-4 border-gray-300 rounded-r-lg">
                <p className="text-[10px] font-bold uppercase text-gray-500 mb-1">Disclaimer</p>
                <p className="text-xs text-gray-500 italic">{analysis.ui_metadata.disclaimer}</p>
              </div>
            )}
          </div>
        ) : (
          <div className="py-12 text-center border-2 border-dashed border-gray-200 rounded-xl">
            <p className="text-gray-400 italic">Analysis could not be generated. Please ensure the backend is running with a valid GROQ_API_KEY.</p>
          </div>
        )}
      </div>

      {/* ── Footer ── */}
      <footer className="mt-16 border-t border-gray-200 py-8 bg-[#FAFAFA]">
        <div className="max-w-5xl mx-auto px-6 text-center">
          <p className="text-[11px] text-gray-400 uppercase tracking-widest font-medium">
            ET Nexus • Multi-Agent RAG Intelligence • © {new Date().getFullYear()} Times Internet
          </p>
        </div>
      </footer>
    </motion.div>
  );
}

// ═══════════════════════════════════════════════════════════════
// SCREEN 5: VIDEO STUDIO
// ═══════════════════════════════════════════════════════════════

interface VideoStudioScreenProps {
  persona: Persona;
  articles: Article[];
  videoJob: VideoResponse | null;
  isGenerating: boolean;
  error: string | null;
  onGenerate: (article: Article, analysis: AnalysisResponse) => void;
  onClearVideo: () => void;
  onBack: () => void;
}

function VideoStudioScreen({
  persona,
  articles,
  videoJob,
  isGenerating,
  error,
  onGenerate,
  onClearVideo,
  onBack,
}: VideoStudioScreenProps) {
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(articles[0] || null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const handleStartGeneration = async () => {
    if (!selectedArticle) return;
    setIsAnalyzing(true);
    try {
      // First generate analysis if needed
      const res = await analyzeNews({
        query: selectedArticle.title,
        user_profile: {
          user_id: persona.user_id,
          persona: persona.persona,
          level: persona.level,
          portfolio: persona.portfolio,
          interests: persona.interests,
        },
      });
      onGenerate(selectedArticle, res);
    } catch (err) {
      console.error(err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="min-h-screen bg-[#F5F5F7]"
    >
      <header className="bg-white/80 backdrop-blur-md border-b border-gray-100 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={onBack}
              className="p-2 hover:bg-gray-100 rounded-full transition-colors"
            >
              <ArrowLeft className="w-5 h-5 text-gray-500" />
            </button>
            <h1 className="text-xl font-serif font-black tracking-tight">AI Video Studio</h1>
          </div>
          <Logo className="h-6" />
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Left: Video Preview & Status */}
          <div className="lg:col-span-8">
            <div className="aspect-video bg-black rounded-3xl shadow-2xl overflow-hidden relative">
              {isGenerating || isAnalyzing ? (
                <div className="absolute inset-0 flex flex-col bg-white overflow-hidden z-20">
                  <div className="p-8 border-b border-slate-100 flex items-center justify-between">
                    <div>
                      <Skeleton className="h-6 w-48 mb-2" />
                      <Skeleton className="h-4 w-32" />
                    </div>
                    <div className="flex gap-2">
                       <Skeleton className="h-8 w-20 rounded-lg" />
                       <Skeleton className="h-8 w-20 rounded-lg" />
                    </div>
                  </div>
                  <div className="flex-1 overflow-hidden">
                    <StoryboardSkeleton />
                  </div>
                  <div className="p-8 bg-slate-50 border-t border-slate-100 flex items-center justify-center gap-6">
                    <div className="flex flex-col items-center gap-3">
                      <div className="w-12 h-12 bg-[#ED1C24]/10 rounded-2xl flex items-center justify-center">
                        <Loader2 className="w-6 h-6 text-[#ED1C24] animate-spin" />
                      </div>
                      <p className="text-xs font-black text-slate-900 uppercase tracking-widest">
                        {isAnalyzing ? "Analyzing Intelligence..." : "Synthesizing Video Briefing..."}
                      </p>
                    </div>
                  </div>
                </div>
              ) : videoJob ? (
                <Player
                  component={NewsVideo}
                  inputProps={{
                    script: videoJob.script,
                    audio_url: `${API_BASE}${videoJob.audio_url}`,
                    subtitles_url: `${API_BASE}${videoJob.subtitles_url}`,
                    subtitles_text: videoJob.subtitles_text,
                    article_title: selectedArticle?.title || "AI Briefing",
                    caption_words: videoJob.caption_words ?? [],
                  }}
                  durationInFrames={videoJob.total_frames ?? 1800}
                  fps={30}
                  compositionWidth={1280}
                  compositionHeight={720}
                  style={{
                    width: '100%',
                    height: '100%',
                  }}
                  controls
                />
              ) : (
                <div className="absolute inset-0 flex flex-col items-center justify-center text-center p-12">
                  <PlayCircle className="w-20 h-20 text-white/10 mb-6" />
                  <h3 className="text-white font-serif text-2xl mb-4">Studio Ready</h3>
                  <p className="text-gray-400 max-w-sm mx-auto">
                    Select an article from the news desk and click 'Produce Briefing' to create sounds and visuals.
                  </p>
                </div>
              )}
            </div>

            {error && (
              <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-xl flex items-center gap-3 text-red-600">
                <Zap className="w-5 h-5" />
                <span className="text-sm font-bold">{error}</span>
              </div>
            )}
          </div>

          {/* Right: Controls & Selection */}
          <div className="lg:col-span-4 space-y-6">
            <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-sm">
              <h3 className="text-sm font-black uppercase tracking-widest text-gray-400 mb-6 flex items-center gap-2">
                <Play className="w-4 h-4" />
                Article Desk
              </h3>
              <div className="space-y-3 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
                {articles.slice(0, 10).map((article) => (
                  <button
                    key={article.id}
                    onClick={() => { setSelectedArticle(article); onClearVideo(); }}
                    className={`w-full text-left p-4 rounded-xl transition-all border ${
                      selectedArticle?.id === article.id
                        ? "bg-[#101723] border-[#101723] text-white shadow-xl"
                        : "bg-gray-50 border-transparent hover:border-gray-200 text-gray-700"
                    }`}
                  >
                    <p className="text-[10px] font-bold uppercase opacity-60 mb-1">{article.date}</p>
                    <p className="font-serif font-bold text-sm leading-snug line-clamp-2">{article.title}</p>
                  </button>
                ))}
              </div>
            </div>

            <button
              onClick={handleStartGeneration}
              disabled={!selectedArticle || isGenerating || isAnalyzing}
              className="w-full py-6 bg-[#ED1C24] text-white rounded-2xl font-black uppercase tracking-[0.2em] shadow-2xl shadow-red-500/20 hover:bg-[#C4121B] transition-all transform active:scale-95 flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isGenerating || isAnalyzing ? (
                <Loader2 className="w-6 h-6 animate-spin" />
              ) : (
                <>
                  <Sparkles className="w-6 h-6" />
                  Produce Briefing
                </>
              )}
            </button>

            <div className="p-6 bg-blue-50 rounded-2xl border border-blue-100">
              <div className="flex items-center gap-2 mb-2">
                <Shield className="w-4 h-4 text-blue-600" />
                <h4 className="text-[10px] font-black uppercase tracking-widest text-blue-800">Studio Guarantee</h4>
              </div>
              <p className="text-[11px] text-blue-600 leading-relaxed font-medium">
                Our AI Director automatically selects HD stock footage and synthesizes professional narration using the ET Nexus Intelligence voice bank.
              </p>
            </div>
          </div>
        </div>
      </main>
    </motion.div>
  );
}
