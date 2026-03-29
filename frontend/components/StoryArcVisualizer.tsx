'use client';

import 'vis-network/styles/vis-network.css';
import React, { useEffect, useRef, useState } from 'react';
import { Network } from 'vis-network/standalone';
import { motion, AnimatePresence } from 'framer-motion';
import { Info, ExternalLink, Calendar, Link2, Maximize2 } from 'lucide-react';

interface GraphNode {
  id: string;
  type: string;
  name: string;
  mentions: number;
  metadata?: any;
}

interface GraphEdge {
  source: string;
  target: string;
  type: string;
  sentiment: number;
  date: string;
  evidence: string;
  edge_id: string;
  article_title?: string;
  article_url?: string;
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

interface StoryArcVisualizerProps {
  graphData: GraphData;
  selectedDate?: string;
  showContrarian?: boolean;
  onNodeClick?: (nodeId: string) => void;
  onEdgeClick?: (edgeId: string) => void;
  className?: string;
  lightMode?: boolean;
}

export default function StoryArcVisualizer({ 
  graphData, 
  selectedDate, 
  showContrarian = false,
  onNodeClick,
  onEdgeClick,
  className = '',
  lightMode = false
}: StoryArcVisualizerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<Network | null>(null);
  const [selectedElement, setSelectedElement] = useState<{ type: 'node' | 'edge', data: any } | null>(null);

  // Theme configuration
  const THEME = {
    background: lightMode ? '#F8FAFC' : '#0B0F19',
    nodeStroke: lightMode ? '#E2E8F0' : '#1E293B',
    textMain: lightMode ? '#0F172A' : '#F8FAFC',
    textMuted: lightMode ? '#64748B' : '#94A3B8',
    brand: '#ED1C24', // ET Red
    edge: lightMode ? '#CBD5E1' : '#334155',
  };

  const getEntityColor = (type: string) => {
    switch(type) {
      case 'COMPANY': return lightMode ? '#ED1C24' : '#EF4444';
      case 'PERSON': return '#0EA5E9';
      case 'POLICY': return '#8B5CF6';
      case 'EVENT': return '#F59E0B';
      default: return '#64748B';
    }
  };

  useEffect(() => {
    if (!containerRef.current || !graphData) return;

    // Always destroy previous instance before re-creating
    if (networkRef.current) {
      try {
        networkRef.current.destroy();
      } catch {
        // ignore
      }
      networkRef.current = null;
    }

    // Filter edges by date (edges without date stay visible — API may omit them)
    let filteredEdges = graphData.edges || [];
    if (selectedDate) {
      filteredEdges = filteredEdges.filter((edge) => {
        if (!edge.date) return true;
        return edge.date <= selectedDate;
      });
    }

    // Bypass filtering: Render all nodes to ensure no entities are lost
    // even if activeNodeIds mismatch
    const filteredNodes = graphData.nodes || [];

    // Prepare vis-network data
    const nodes = filteredNodes.map(node => ({
      id: node.id,
      label: node.name,
      title: `${node.type}: ${node.name}`,
      value: Math.min(12, 4 + Math.min(8, node.mentions || 0)),
      color: {
        background: getEntityColor(node.type),
        border: THEME.nodeStroke,
        highlight: { background: THEME.brand, border: THEME.brand }
      },
      font: { 
        color: THEME.textMain, 
        size: 12, 
        face: 'Inter, system-ui, sans-serif', 
        strokeWidth: lightMode ? 1 : 0, 
        strokeColor: '#FFFFFF' 
      },
      shape: 'dot'
    }));

    // Defensive validation: vis-network crashes completely if an edge points to a non-existent node
    const validNodeIds = new Set(filteredNodes.map(n => n.id));

    const edges = filteredEdges
      .filter(edge => {
        const fromId = typeof edge.source === 'string' ? edge.source : (edge.source as any).id;
        const toId = typeof edge.target === 'string' ? edge.target : (edge.target as any).id;
        return validNodeIds.has(fromId) && validNodeIds.has(toId);
      })
      .map(edge => {
      const fromId = typeof edge.source === 'string' ? edge.source : (edge.source as any).id;
      const toId = typeof edge.target === 'string' ? edge.target : (edge.target as any).id;
      return {
        id: edge.edge_id || `${String(fromId)}-${String(toId)}-${edge.type || 'e'}`,
        from: fromId,
        to: toId,
        color: {
          color: THEME.edge,
          highlight: THEME.brand,
          hover: THEME.brand
        },
        width: 1,
        arrows: { to: { enabled: true, scaleFactor: 0.35 } }
      };
    });

    const options = {
      nodes: {
        borderWidth: 1,
        shadow: false
      },
      edges: {
        width: 1,
        smooth: { enabled: true, type: 'continuous', forceDirection: 'none', roundness: 0.15 },
        hoverWidth: 2,
        selectionWidth: 2
      },
      physics: {
        forceAtlas2Based: {
          gravitationalConstant: -38,
          centralGravity: 0.008,
          springLength: 140,
          springConstant: 0.05,
          damping: 0.55
        },
        solver: 'forceAtlas2Based',
        stabilization: { iterations: 120 }
      },
      interaction: { hover: true, tooltipDelay: 150, hideEdgesOnDrag: true, zoomView: true }
    };

    try {
      // Final fallback for missing IDs that crash the renderer natively
      const safeNodes = nodes.filter(n => n.id !== undefined && n.id !== null);
      const safeEdges = edges.filter(e => e.from !== undefined && e.to !== undefined);

      // Use the ESM-imported constructor. Avoid runtime require() which can fail
      // under Next.js bundling and result in an empty canvas.
      const network = new Network(containerRef.current, { nodes: safeNodes, edges: safeEdges }, options);
      
      // Force stabilization and fit to viewport
      network.once("stabilizationIterationsDone", function () {
        network.fit({ animation: true });
      });

      networkRef.current = network;
    } catch (err) {
      console.error("Failed to initialize vis-network:", err);
      return;
    }

    // network is stored on the ref above; use the ref below to avoid scope issues
    networkRef.current?.on('selectNode', (params: any) => {
      const nodeId = params.nodes[0];
      const nodeData = filteredNodes.find(n => n.id === nodeId);
      if (nodeData) {
        setSelectedElement({ type: 'node', data: nodeData });
        onNodeClick?.(nodeId);
      }
    });

    networkRef.current?.on('selectEdge', (params: any) => {
      const edgeId = params.edges[0];
      const edgeData = filteredEdges.find((e) => {
        const fid = typeof e.source === 'string' ? e.source : (e.source as any).id;
        const tid = typeof e.target === 'string' ? e.target : (e.target as any).id;
        const gen = e.edge_id || `${String(fid)}-${String(tid)}-${e.type || 'e'}`;
        return e.edge_id === edgeId || gen === edgeId;
      });
      if (edgeData) {
        setSelectedElement({ type: 'edge', data: edgeData });
        onEdgeClick?.(edgeId);
      }
    });

    networkRef.current?.on('deselectNode', () => setSelectedElement(null));
    networkRef.current?.on('deselectEdge', () => setSelectedElement(null));

    // Force network to redraw explicitly
    setTimeout(() => {
        if (networkRef.current) networkRef.current.redraw();
    }, 500);

    return () => {
      if (networkRef.current) {
        networkRef.current.destroy();
        networkRef.current = null;
      }
    };
  }, [graphData, selectedDate, showContrarian, lightMode]);

  return (
    <div className={`relative h-full w-full min-h-0 ${className}`}>
      <div 
        ref={containerRef} 
        className="absolute inset-0 w-full h-full cursor-grab active:cursor-grabbing vis-network-override"
        style={{ backgroundColor: THEME.background, width: '100%', height: '100%' }}
      />

      {/* Branded Detail Overlay */}
      <AnimatePresence>
        {selectedElement && (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            className="absolute bottom-6 right-6 w-80 bg-white border border-slate-200 shadow-2xl rounded-2xl overflow-hidden z-20"
          >
            <div className="bg-[#ED1C24] p-4 text-white">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-black uppercase tracking-widest opacity-80">
                  {selectedElement.type === 'node' ? selectedElement.data.type : 'RELATIONSHIP'}
                </span>
                <button onClick={() => setSelectedElement(null)} className="hover:rotate-90 transition-transform">
                  <Maximize2 className="w-4 h-4" />
                </button>
              </div>
              <h3 className="text-lg font-black tracking-tight mt-1 leading-tight">
                {selectedElement.type === 'node' ? selectedElement.data.name : `${selectedElement.data.source} → ${selectedElement.data.target}`}
              </h3>
            </div>

            <div className="p-5 space-y-4">
              {selectedElement.type === 'node' ? (
                <>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 text-center">
                      <p className="text-[10px] text-slate-400 font-bold uppercase mb-1">Mentions</p>
                      <p className="text-xl font-black text-slate-800">{selectedElement.data.mentions}</p>
                    </div>
                    <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 text-center">
                      <p className="text-[10px] text-slate-400 font-bold uppercase mb-1">Influence</p>
                      <p className="text-xl font-black text-[#ED1C24]">{(selectedElement.data.mentions * 0.42).toFixed(1)}</p>
                    </div>
                  </div>
                  {selectedElement.data.metadata && Object.keys(selectedElement.data.metadata).length > 0 && (
                    <div className="p-4 bg-slate-900 rounded-xl text-white">
                      <p className="text-[9px] font-bold text-[#ED1C24] uppercase mb-2">Extended metadata</p>
                      <pre className="text-[10px] opacity-70 overflow-x-auto">
                        {JSON.stringify(selectedElement.data.metadata, null, 2)}
                      </pre>
                    </div>
                  )}
                </>
              ) : (
                <>
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-slate-50 rounded-lg text-slate-400">
                      <Link2 className="w-4 h-4" />
                    </div>
                    <div>
                      <p className="text-[10px] text-slate-400 font-bold uppercase">Relationship Type</p>
                      <p className="text-xs font-black text-slate-800">{selectedElement.data.type}</p>
                    </div>
                  </div>

                  <div className="p-4 bg-slate-50 rounded-xl border border-slate-100 border-l-4 border-l-[#ED1C24]">
                    <p className="text-[10px] text-slate-400 font-bold uppercase mb-2 flex items-center gap-1">
                       <Info className="w-3 h-3" /> Agentic Evidence
                    </p>
                    <p className="text-xs italic text-slate-700 leading-relaxed font-bold">
                      "{selectedElement.data.evidence}"
                    </p>
                  </div>

                  {selectedElement.data.article_title && (
                    <div className="pt-2">
                       <p className="text-[10px] text-slate-400 font-bold uppercase mb-2">Sources</p>
                       <a 
                         href={selectedElement.data.article_url} 
                         target="_blank" 
                         rel="noopener noreferrer"
                         className="flex items-center justify-between p-3 bg-white border border-slate-200 rounded-xl text-xs font-bold text-slate-700 hover:text-[#ED1C24] hover:shadow-md transition-all group"
                       >
                         <span className="truncate pr-4">{selectedElement.data.article_title}</span>
                         <ExternalLink className="w-3.5 h-3.5 flex-shrink-0 opacity-40 group-hover:opacity-100" />
                       </a>
                    </div>
                  )}
                </>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Compact legend — one line */}
      <div className="absolute bottom-3 left-1/2 -translate-x-1/2 max-w-[95%] pointer-events-none z-[5]">
        <div className="px-2 py-1 bg-white/90 backdrop-blur border border-slate-200/80 rounded-md shadow-sm flex flex-wrap items-center justify-center gap-x-3 gap-y-0.5 text-[9px] text-slate-600">
          <span className="text-slate-400 font-medium">Entities</span>
          <span className="inline-flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-[#ED1C24]" /> Company</span>
          <span className="inline-flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-[#0EA5E9]" /> Person</span>
          <span className="inline-flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-[#8B5CF6]" /> Policy</span>
          <span className="inline-flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-[#F59E0B]" /> Event</span>
        </div>
      </div>
    </div>
  );
}
