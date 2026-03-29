'use client';

import React, { useEffect, useRef, useState } from 'react';
import dynamic from 'next/dynamic';
import { motion, AnimatePresence } from 'framer-motion';
import * as THREE from 'three';

// Dynamically import ForceGraph3D to avoid SSR issues
const ForceGraph3DComponent = dynamic(() => import('react-force-graph-3d'), {
  ssr: false,
  loading: () => <div className="flex items-center justify-center h-full text-slate-400">Initializing 3D spatial field...</div>
});

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
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

interface ForceGraph3DProps {
  graphData: GraphData;
  selectedDate?: string;
  showContrarian?: boolean;
  onNodeClick?: (node: GraphNode) => void;
  onEdgeClick?: (edge: GraphEdge) => void;
  className?: string;
  lightMode?: boolean;
}

const ENTITY_COLORS: { [key: string]: string } = {
  COMPANY: '#ED1C24',
  PERSON: '#0EA5E9',
  POLICY: '#8B5CF6',
  EVENT: '#F59E0B',
  METRIC: '#64748B',
  UNKNOWN: '#94A3B8'
};

export default function ForceGraph3D({
  graphData,
  selectedDate,
  showContrarian = false,
  onNodeClick,
  onEdgeClick,
  className = '',
  lightMode = false
}: ForceGraph3DProps) {
  const fgRef = useRef<any>(null);
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);

  // Filter edges by date
  let filteredEdges = graphData?.edges || [];
  if (selectedDate) {
    filteredEdges = filteredEdges.filter((edge) => {
      if (!edge.date) return true;
      return edge.date <= selectedDate;
    });
  }

  // Get active nodes from edges, but fallback to all nodes if no edges exist yet
  const activeNodeIds = new Set<string>();
  filteredEdges.forEach(edge => {
    activeNodeIds.add(typeof edge.source === 'string' ? edge.source : (edge.source as any).id);
    activeNodeIds.add(typeof edge.target === 'string' ? edge.target : (edge.target as any).id);
  });

  const filteredNodes = activeNodeIds.size > 0 
    ? (graphData?.nodes || []).filter(node => activeNodeIds.has(node.id))
    : (graphData?.nodes || []);

  // Transform data for react-force-graph-3d
  const graphData3D = {
    nodes: filteredNodes.map(node => ({
        id: node.id,
        name: node.name,
        type: node.type,
        mentions: node.mentions,
        color: ENTITY_COLORS[node.type] || ENTITY_COLORS.UNKNOWN,
        val: Math.min(14, Math.max(4, 3 + (node.mentions || 0)))
      })),
    links: filteredEdges.map(edge => ({
      source: edge.source,
      target: edge.target,
      type: edge.type,
      sentiment: edge.sentiment,
      date: edge.date,
      edge_id: edge.edge_id,
      color: lightMode ? '#94A3B8' : '#64748B',
      width: 0.6,
      opacity: 0.55
    }))
  };

  useEffect(() => {
    if (fgRef.current) {
        fgRef.current.cameraPosition({ z: 500 }, undefined, 0);
    }
  }, []);

  // Custom Node Rendering with Labels - IMPROVED SAFETY
  const drawNode = (node: any) => {
    const group = new THREE.Group();
    
    // 1. Draw Node Sphere
    const size = Math.sqrt(node.val || 5) * 1.35;
    const geometry = new THREE.SphereGeometry(size, 24, 24);
    const material = new THREE.MeshLambertMaterial({ 
        color: node.color,
        transparent: true,
        opacity: 0.92,
        emissive: node.color,
        emissiveIntensity: 0.12
    });
    const sphere = new THREE.Mesh(geometry, material);
    group.add(sphere);

    // 2. Draw Label Sprite
    if (typeof document !== 'undefined') {
        try {
            const canvas = document.createElement('canvas');
            const context = canvas.getContext('2d');
            if (context) {
                const text = node.name || "Unknown Entity";
                context.font = '600 28px Inter, system-ui, Arial';
                const textWidth = context.measureText(text).width;
                
                canvas.width = Math.max(10, textWidth + 24);
                canvas.height = 44;
                
                // Background
                context.fillStyle = lightMode ? 'rgba(255, 255, 255, 0.85)' : 'rgba(15, 23, 42, 0.85)';
                
                // Check for roundRect support (some environments lack it)
                if (typeof context.roundRect === 'function') {
                   context.beginPath();
                   context.roundRect(0, 0, canvas.width, canvas.height, 12);
                   context.fill();
                } else {
                   // Fallback: draw normal rect
                   context.fillRect(0, 0, canvas.width, canvas.height);
                }
                
                // Text
                context.fillStyle = lightMode ? '#0F172A' : '#F8FAFC';
                context.font = '600 28px Inter, system-ui, Arial';
                context.textAlign = 'center';
                context.textBaseline = 'middle';
                context.fillText(text, canvas.width / 2, canvas.height / 2);
                
                const texture = new THREE.CanvasTexture(canvas);
                const spriteMaterial = new THREE.SpriteMaterial({ map: texture, transparent: true });
                const sprite = new THREE.Sprite(spriteMaterial);
                
                sprite.position.set(0, size + 10, 0);
                sprite.scale.set(canvas.width / 12, canvas.height / 12, 1);
                group.add(sprite);
            }
        } catch (err) {
            console.warn("Label generation failed for node:", node.id, err);
        }
    }

    return group;
  };

  return (
    <div className={`relative ${className} overflow-hidden`} style={{ backgroundColor: lightMode ? '#F8FAFC' : '#0B0F19' }}>
      <ForceGraph3DComponent
        ref={fgRef}
        graphData={graphData3D}
        nodeThreeObject={drawNode}
        nodeThreeObjectExtend={false}
        nodeVal="val"
        linkLabel={() => ''}
        linkColor="color"
        linkWidth="width"
        linkDirectionalArrowLength={2}
        linkDirectionalArrowRelPos={1}
        onNodeClick={(node: any) => {
          const fullNode = graphData.nodes.find(n => n.id === node.id);
          if (fullNode) onNodeClick?.(fullNode);
        }}
        onNodeHover={(node: any) => {
          if (node) {
            const fullNode = graphData.nodes.find(n => n.id === node.id);
            setHoveredNode(fullNode || null);
          } else {
            setHoveredNode(null);
          }
        }}
        backgroundColor={lightMode ? '#F8FAFC' : '#0B0F19'}
        showNavInfo={false}
      />

      <AnimatePresence>
        {hoveredNode && (
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="absolute top-3 left-3 bg-white/95 backdrop-blur border border-slate-200 rounded-lg px-3 py-2 shadow-md z-20 max-w-[240px]"
          >
            <div className="flex items-center gap-2 mb-0.5">
              <div className="w-1.5 h-1.5 rounded-full shrink-0" style={{ backgroundColor: ENTITY_COLORS[hoveredNode.type] || '#000' }} />
              <span className="text-[9px] font-medium text-slate-500">{hoveredNode.type}</span>
            </div>
            <h4 className="text-sm font-semibold text-slate-900 leading-snug">{hoveredNode.name}</h4>
            <p className="text-[10px] text-slate-500 mt-1">Mentions: {hoveredNode.mentions}</p>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="absolute bottom-3 left-1/2 -translate-x-1/2 max-w-[95%] flex flex-col items-center gap-1 pointer-events-none z-10">
        <div className="px-2 py-1 bg-white/90 backdrop-blur border border-slate-200/80 rounded-md shadow-sm flex flex-wrap items-center justify-center gap-x-2 gap-y-0.5 text-[9px] text-slate-600">
          <span className="text-slate-400 font-medium">Entities</span>
          <span className="inline-flex items-center gap-0.5"><span className="w-1.5 h-1.5 rounded-full bg-[#ED1C24]" /> Co.</span>
          <span className="inline-flex items-center gap-0.5"><span className="w-1.5 h-1.5 rounded-full bg-[#0EA5E9]" /> Person</span>
          <span className="inline-flex items-center gap-0.5"><span className="w-1.5 h-1.5 rounded-full bg-[#8B5CF6]" /> Policy</span>
          <span className="inline-flex items-center gap-0.5"><span className="w-1.5 h-1.5 rounded-full bg-[#F59E0B]" /> Event</span>
        </div>
        <div className="px-2 py-0.5 text-[8px] text-slate-400 text-center">
          Drag to rotate · Scroll to zoom · Right-drag to pan
        </div>
      </div>
    </div>
  );
}
