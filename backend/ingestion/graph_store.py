"""
Phase 7: Graph Storage & Management

This module manages the knowledge graph using NetworkX, providing temporal indexing,
delta updates, and efficient querying for the Story Arc Tracker.
"""

import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import networkx as nx
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GraphStore:
    """
    Manages the knowledge graph for Story Arc Tracker.
    
    Features:
    - NetworkX DiGraph for relationship storage
    - Temporal indexing by date
    - Delta updates (append new edges)
    - Query by entity, date range, relationship type
    - JSON serialization for frontend
    - Contrarian detection
    """
    
    def __init__(self, storage_path: str = "data/story_graph.json"):
        """
        Initialize the graph store.
        
        Args:
            storage_path: Path to persist graph as JSON (relative to backend root)
        """
        self.graph = nx.DiGraph()
        # Ensure the path is relative to the backend directory
        self.storage_path = Path(__file__).parent.parent / storage_path
        self.entity_index = {}  # Fast lookup: entity_id -> node data
        self.temporal_index = {}  # Fast lookup: date -> list of edge IDs
        
        # Load existing graph if available
        self._load_from_disk()
    
    def add_entities(self, entities: List[Dict[str, Any]]):
        """
        Add entities as nodes to the graph.
        
        Args:
            entities: List of entity dicts with id, type, name, mentions
        """
        for entity in entities:
            entity_id = entity.get('id')
            if not entity_id:
                continue
            
            # Add or update node
            if entity_id in self.graph.nodes:
                # Update existing node (increment mentions)
                self.graph.nodes[entity_id]['mentions'] += entity.get('mentions', 1)
            else:
                # Add new node
                self.graph.add_node(
                    entity_id,
                    type=entity.get('type', 'UNKNOWN'),
                    name=entity.get('name', entity_id),
                    mentions=entity.get('mentions', 1),
                    metadata=entity.get('metadata', {})
                )
            
            # Update entity index
            self.entity_index[entity_id] = self.graph.nodes[entity_id]
        
        logger.info(f"Added/updated {len(entities)} entities. Total nodes: {self.graph.number_of_nodes()}")
    
    def add_relationships(self, relationships: List[Dict[str, Any]]):
        """
        Add relationships as edges to the graph.
        
        Args:
            relationships: List of relationship dicts with source, target, type, sentiment, date
        """
        added_count = 0
        
        for rel in relationships:
            source = rel.get('source')
            target = rel.get('target')
            
            if not source or not target:
                continue
            
            # Ensure nodes exist
            if source not in self.graph.nodes:
                self.graph.add_node(source, type='UNKNOWN', name=source, mentions=0)
            if target not in self.graph.nodes:
                self.graph.add_node(target, type='UNKNOWN', name=target, mentions=0)
            
            # Generate edge ID
            edge_id = f"{source}_{target}_{rel.get('type', 'UNKNOWN')}_{rel.get('date', 'unknown')}"
            
            # Add edge with metadata
            self.graph.add_edge(
                source,
                target,
                edge_id=edge_id,
                type=rel.get('type', 'UNKNOWN'),
                sentiment=rel.get('sentiment', 0.0),
                date=rel.get('date'),
                evidence=rel.get('evidence', ''),
                article_id=rel.get('article_metadata', {}).get('article_id'),
                article_title=rel.get('article_metadata', {}).get('title'),
                article_url=rel.get('article_metadata', {}).get('url')
            )
            
            # Update temporal index
            date = rel.get('date')
            if date:
                if date not in self.temporal_index:
                    self.temporal_index[date] = []
                self.temporal_index[date].append(edge_id)
            
            added_count += 1
        
        logger.info(f"Added {added_count} relationships. Total edges: {self.graph.number_of_edges()}")
    
    def query_by_entity(
        self,
        entity_id: str,
        max_depth: int = 2,
        include_incoming: bool = True,
        include_outgoing: bool = True
    ) -> Dict[str, Any]:
        """
        Query graph for all relationships involving an entity.
        
        Args:
            entity_id: Entity to query
            max_depth: Maximum relationship depth (1 = direct connections only)
            include_incoming: Include edges pointing to entity
            include_outgoing: Include edges from entity
        
        Returns:
            Subgraph dict with nodes and edges
        """
        if entity_id not in self.graph.nodes:
            logger.warning(f"Entity {entity_id} not found in graph")
            return {'nodes': [], 'edges': []}
        
        # Get connected nodes
        connected_nodes = set([entity_id])
        
        if include_outgoing:
            # Get nodes this entity points to
            for depth in range(max_depth):
                new_nodes = set()
                for node in connected_nodes:
                    if node in self.graph:
                        new_nodes.update(self.graph.successors(node))
                connected_nodes.update(new_nodes)
        
        if include_incoming:
            # Get nodes pointing to this entity
            for depth in range(max_depth):
                new_nodes = set()
                for node in connected_nodes:
                    if node in self.graph:
                        new_nodes.update(self.graph.predecessors(node))
                connected_nodes.update(new_nodes)
        
        # Extract subgraph
        subgraph = self.graph.subgraph(connected_nodes)
        
        return self._serialize_graph(subgraph)
    
    def query_by_date_range(
        self,
        start_date: str,
        end_date: str,
        entity_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Query graph for relationships within a date range.
        
        Args:
            start_date: ISO 8601 start date
            end_date: ISO 8601 end date
            entity_filter: Optional entity ID to filter by
        
        Returns:
            Subgraph dict with nodes and edges in date range
        """
        filtered_edges = []
        entity_ids = set()
        
        for u, v, data in self.graph.edges(data=True):
            edge_date = data.get('date')
            if not edge_date:
                continue
            
            # Check date range
            if start_date <= edge_date <= end_date:
                # Check entity filter
                if entity_filter and entity_filter not in [u, v]:
                    continue
                
                filtered_edges.append((u, v, data))
                entity_ids.add(u)
                entity_ids.add(v)
        
        # Build subgraph
        subgraph = nx.DiGraph()
        
        # Add nodes
        for entity_id in entity_ids:
            subgraph.add_node(entity_id, **self.graph.nodes[entity_id])
        
        # Add edges
        for u, v, data in filtered_edges:
            subgraph.add_edge(u, v, **data)
        
        logger.info(f"Date range query: {len(subgraph.nodes)} nodes, {len(subgraph.edges)} edges")
        
        return self._serialize_graph(subgraph)
    
    def detect_contrarian(self, min_sentiment_diff: float = 1.0) -> List[Dict[str, Any]]:
        """
        Detect contrarian relationships (opposing sentiments on same target).
        
        Args:
            min_sentiment_diff: Minimum sentiment difference to consider contrarian
        
        Returns:
            List of contrarian pairs with conflict metadata
        """
        contrarian_pairs = []
        
        # Group edges by target
        target_edges = {}
        for u, v, data in self.graph.edges(data=True):
            if v not in target_edges:
                target_edges[v] = []
            target_edges[v].append((u, data))
        
        # Find opposing sentiments
        for target, edges in target_edges.items():
            for i in range(len(edges)):
                for j in range(i + 1, len(edges)):
                    source1, data1 = edges[i]
                    source2, data2 = edges[j]
                    
                    sentiment1 = data1.get('sentiment', 0)
                    sentiment2 = data2.get('sentiment', 0)
                    
                    # Check for opposition
                    if sentiment1 * sentiment2 < 0:  # Opposite signs
                        diff = abs(sentiment1 - sentiment2)
                        if diff >= min_sentiment_diff:
                            contrarian_pairs.append({
                                'target': target,
                                'target_name': self.graph.nodes[target].get('name', target),
                                'source1': source1,
                                'source1_name': self.graph.nodes[source1].get('name', source1),
                                'sentiment1': sentiment1,
                                'relationship1': data1.get('type'),
                                'evidence1': data1.get('evidence', ''),
                                'date1': data1.get('date'),
                                'source2': source2,
                                'source2_name': self.graph.nodes[source2].get('name', source2),
                                'sentiment2': sentiment2,
                                'relationship2': data2.get('type'),
                                'evidence2': data2.get('evidence', ''),
                                'date2': data2.get('date'),
                                'conflict_score': diff
                            })
        
        logger.info(f"Detected {len(contrarian_pairs)} contrarian relationships")
        
        return contrarian_pairs
    
    def get_timeline(
        self,
        entity_id: Optional[str] = None,
        granularity: str = "day"
    ) -> List[Dict[str, Any]]:
        """
        Generate timeline of events for visualization.
        
        Args:
            entity_id: Optional entity to filter by
            granularity: "day", "week", or "month"
        
        Returns:
            List of timeline events sorted by date
        """
        timeline = {}
        
        for u, v, data in self.graph.edges(data=True):
            # Filter by entity if specified
            if entity_id and entity_id not in [u, v]:
                continue
            
            date = data.get('date')
            if not date:
                continue
            
            # Group by granularity
            if granularity == "week":
                # Get week start date
                dt = datetime.fromisoformat(date)
                week_start = dt - timedelta(days=dt.weekday())
                date = week_start.strftime('%Y-%m-%d')
            elif granularity == "month":
                # Get month start date
                date = date[:7] + "-01"
            
            if date not in timeline:
                timeline[date] = []
            
            timeline[date].append({
                'source': u,
                'source_name': self.graph.nodes[u].get('name', u),
                'target': v,
                'target_name': self.graph.nodes[v].get('name', v),
                'type': data.get('type'),
                'sentiment': data.get('sentiment', 0),
                'evidence': data.get('evidence', ''),
                'article_title': data.get('article_title', ''),
                'article_url': data.get('article_url', '')
            })
        
        # Convert to sorted list
        timeline_list = [
            {'date': date, 'events': events}
            for date, events in sorted(timeline.items())
        ]
        
        logger.info(f"Generated timeline with {len(timeline_list)} time points")
        
        return timeline_list
    
    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        entity_types = {}
        relationship_types = {}
        sentiment_distribution = {'positive': 0, 'neutral': 0, 'negative': 0}
        
        # Count entity types
        for node, data in self.graph.nodes(data=True):
            entity_type = data.get('type', 'UNKNOWN')
            entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
        
        # Count relationship types and sentiment
        for u, v, data in self.graph.edges(data=True):
            rel_type = data.get('type', 'UNKNOWN')
            relationship_types[rel_type] = relationship_types.get(rel_type, 0) + 1
            
            sentiment = data.get('sentiment', 0)
            if sentiment > 0.2:
                sentiment_distribution['positive'] += 1
            elif sentiment < -0.2:
                sentiment_distribution['negative'] += 1
            else:
                sentiment_distribution['neutral'] += 1
        
        return {
            'total_entities': self.graph.number_of_nodes(),
            'total_relationships': self.graph.number_of_edges(),
            'entity_types': entity_types,
            'relationship_types': relationship_types,
            'sentiment_distribution': sentiment_distribution,
            'contrarian_count': len(self.detect_contrarian())
        }
    
    def _serialize_graph(self, graph: nx.DiGraph = None) -> Dict[str, Any]:
        """
        Serialize graph to JSON format for frontend.
        
        Args:
            graph: NetworkX graph to serialize (defaults to self.graph)
        
        Returns:
            Dict with nodes and edges arrays
        """
        if graph is None:
            graph = self.graph
        
        nodes = []
        for node_id, data in graph.nodes(data=True):
            nodes.append({
                'id': node_id,
                'type': data.get('type', 'UNKNOWN'),
                'name': data.get('name', node_id),
                'mentions': data.get('mentions', 0),
                'metadata': data.get('metadata', {})
            })
        
        edges = []
        for u, v, data in graph.edges(data=True):
            edges.append({
                'source': u,
                'target': v,
                'type': data.get('type', 'UNKNOWN'),
                'sentiment': data.get('sentiment', 0.0),
                'date': data.get('date'),
                'evidence': data.get('evidence', ''),
                'article_id': data.get('article_id'),
                'article_title': data.get('article_title', ''),
                'article_url': data.get('article_url', ''),
                'edge_id': data.get('edge_id', f"{u}_{v}")
            })
        
        return {
            'nodes': nodes,
            'edges': edges
        }
    
    def save_to_disk(self):
        """Persist graph to disk as JSON."""
        try:
            # Ensure directory exists
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Serialize and save
            graph_data = self._serialize_graph()
            graph_data['stats'] = self.get_stats()
            graph_data['temporal_index'] = self.temporal_index
            
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(graph_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Graph saved to {self.storage_path}")
            
        except Exception as e:
            logger.error(f"Error saving graph: {e}")
    
    def _load_from_disk(self):
        """Load graph from disk if exists."""
        try:
            if not self.storage_path.exists():
                logger.info(f"No existing graph found at {self.storage_path}. Starting fresh.")
                return
            
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                graph_data = json.load(f)
            
            # Reconstruct graph
            for node in graph_data.get('nodes', []):
                self.graph.add_node(
                    node['id'],
                    type=node.get('type'),
                    name=node.get('name'),
                    mentions=node.get('mentions', 0),
                    metadata=node.get('metadata', {})
                )
                self.entity_index[node['id']] = self.graph.nodes[node['id']]
            
            for edge in graph_data.get('edges', []):
                self.graph.add_edge(
                    edge['source'],
                    edge['target'],
                    edge_id=edge.get('edge_id'),
                    type=edge.get('type'),
                    sentiment=edge.get('sentiment', 0.0),
                    date=edge.get('date'),
                    evidence=edge.get('evidence', ''),
                    article_id=edge.get('article_id'),
                    article_title=edge.get('article_title', ''),
                    article_url=edge.get('article_url', '')
                )
            
            # Restore temporal index
            self.temporal_index = graph_data.get('temporal_index', {})
            
            logger.info(f"Loaded graph: {self.graph.number_of_nodes()} nodes, "
                       f"{self.graph.number_of_edges()} edges")
            
        except Exception as e:
            logger.error(f"Error loading graph: {e}")
    
    def update_from_extraction(self, extraction: Dict[str, Any]):
        """
        Delta update: Add new entities and relationships from extraction.
        
        Args:
            extraction: Extraction result from GraphExtractor
        """
        self.add_entities(extraction.get('entities', []))
        self.add_relationships(extraction.get('relationships', []))
        self.save_to_disk()
    
    def get_full_graph(self) -> Dict[str, Any]:
        """Get complete graph for frontend."""
        return self._serialize_graph()
    
    def clear(self):
        """Clear all graph data."""
        self.graph.clear()
        self.entity_index.clear()
        self.temporal_index.clear()
        logger.info("Graph cleared")
