"""
Phase 6: GraphRAG Engine - Entity & Relationship Extraction

This module extracts entities (companies, people, policies) and their relationships
from article chunks using LLM-powered Named Entity Recognition and sentiment analysis.
"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
from groq import AsyncGroq
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GraphExtractor:
    """
    Extracts entities and relationships from article text using LLM.
    
    Features:
    - Named Entity Recognition (NER)
    - Relationship extraction
    - Sentiment scoring (-1 to +1)
    - Temporal metadata attachment
    - JSON schema validation
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.3-70b-versatile"):
        """
        Initialize the GraphRAG extractor.
        
        Args:
            api_key: Groq API key (defaults to GROQ_API_KEY env var)
            model: LLM model to use (default: llama-3.3-70b-versatile)
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model
        self.client = None
        
        if not self.api_key:
            logger.warning("No Groq API key provided. Set GROQ_API_KEY environment variable.")
    
    def _ensure_initialized(self):
        """Lazy initialization of Groq client."""
        if self.client is None and self.api_key:
            self.client = AsyncGroq(api_key=self.api_key)
            logger.info("Groq client initialized")
    
    def _build_extraction_prompt(self, article_text: str, article_metadata: Dict[str, Any]) -> str:
        """
        Build the LLM prompt for entity and relationship extraction.
        
        Args:
            article_text: The article chunk text
            article_metadata: Article metadata (title, date, tags)
        
        Returns:
            Formatted prompt string
        """
        prompt = f"""You are an expert financial analyst extracting structured information from Economic Times articles.

TASK: Extract entities and relationships from the following article.

ARTICLE METADATA:
Title: {article_metadata.get('title', 'Unknown')}
Date: {article_metadata.get('date', 'Unknown')}
Tags: {', '.join(article_metadata.get('tags', []))}

ARTICLE TEXT:
{article_text}

OUTPUT FORMAT (strict JSON):
{{
  "entities": [
    {{
      "id": "UNIQUE_ID",
      "type": "ENTITY_TYPE",
      "name": "Display Name",
      "mentions": 1
    }}
  ],
  "relationships": [
    {{
      "source": "SOURCE_ENTITY_ID",
      "target": "TARGET_ENTITY_ID",
      "type": "RELATIONSHIP_TYPE",
      "sentiment": 0.0,
      "evidence": "Exact quote from article..."
    }}
  ]
}}

ENTITY TYPES:
- COMPANY: Tata Motors, Reliance, HDFC Bank
- PERSON: CEOs, analysts, government officials
- POLICY: RBI policies, government schemes, regulations
- EVENT: Mergers, acquisitions, product launches
- METRIC: Stock prices, revenue, market cap

RELATIONSHIP TYPES:
- INVESTED_IN: Entity invested money in target
- ACQUIRED: Entity acquired or merged with target
- CRITICIZED: Entity criticized or opposed target
- BENEFITED_FROM: Entity gained advantage from target
- ANNOUNCED: Entity announced or revealed target
- PARTNERED_WITH: Entity formed partnership with target
- COMPETED_WITH: Entity competed against target
- REGULATED_BY: Entity is regulated or governed by target
- IMPACTED: Entity affected target (general)

SENTIMENT RANGE:
- +0.7 to +1.0: Very positive (bullish, growth, success)
- +0.3 to +0.6: Positive (optimistic, improving)
- -0.2 to +0.2: Neutral (factual, reporting)
- -0.6 to -0.3: Negative (concerns, decline)
- -1.0 to -0.7: Very negative (bearish, crisis, failure)

RULES:
1. Extract ONLY factual relationships mentioned in the text.
2. Do NOT infer or speculate beyond what's written.
3. IMPORTANT: Every 'source' and 'target' in the relationships list MUST correspond exactly to an 'id' defined in the 'entities' list.
4. Use ticker symbols for company IDs when available (from tags).
5. Include exact quotes as evidence for each relationship.
6. Return valid JSON only, no additional text.

OUTPUT:"""
        
        return prompt
    
    async def extract_from_chunk(
        self,
        chunk: Dict[str, Any],
        retry_count: int = 2
    ) -> Optional[Dict[str, Any]]:
        """
        Extract entities and relationships from a single chunk.
        
        Args:
            chunk: Chunk dict with 'text' and 'metadata' fields
            retry_count: Number of retries on failure
        
        Returns:
            Dict with 'entities' and 'relationships' lists, or None on failure
        """
        self._ensure_initialized()
        
        if not self.client:
            logger.error("Groq client not initialized. Check API key.")
            return None
        
        text = chunk.get('text', '')
        metadata = chunk.get('metadata', {})
        
        if not text or len(text) < 50:
            logger.warning("Chunk text too short for extraction")
            return None
        
        prompt = self._build_extraction_prompt(text, metadata)
        
        for attempt in range(retry_count + 1):
            try:
                logger.info(f"Extracting entities from chunk (attempt {attempt + 1}/{retry_count + 1})")
                
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {
                                "role": "system",
                                "content": "You are a financial data extraction expert. Return only valid JSON."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        temperature=0.1,
                        max_tokens=2000
                    ),
                    timeout=45.0  # Avoid hanging on slow extraction
                )
                
                content = response.choices[0].message.content.strip()
                
                # Parse JSON response
                try:
                    extracted = json.loads(content)
                except json.JSONDecodeError:
                    # Try to extract JSON from markdown code blocks
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0].strip()
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0].strip()
                    extracted = json.loads(content)
                
                # Validate schema
                if not isinstance(extracted, dict):
                    raise ValueError("Response is not a dict")
                if 'entities' not in extracted or 'relationships' not in extracted:
                    raise ValueError("Missing required fields: entities or relationships")
                
                # Link Validation: Ensure relationships point to valid entity IDs
                extracted = self._align_relationships(extracted)
                
                # Attach metadata to extraction
                extracted['article_metadata'] = metadata
                extracted['chunk_text'] = text[:200]  # First 200 chars for reference
                
                logger.info(f"Extracted {len(extracted['entities'])} entities, "
                          f"{len(extracted['relationships'])} relationships")
                
                return extracted
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error (attempt {attempt + 1}): {e}")
                if attempt == retry_count:
                    return None
    def _align_relationships(self, extracted: Dict[str, Any]) -> Dict[str, Any]:
        """
        Post-process extraction to ensure relationships point to valid entities.
        Filters out orphaned relationships.
        """
        entities = extracted.get('entities', [])
        relationships = extracted.get('relationships', [])
        
        entity_ids = {e.get('id') for e in entities if e.get('id')}
        
        valid_rels = []
        for rel in relationships:
            source = rel.get('source')
            target = rel.get('target')
            
            if source in entity_ids and target in entity_ids:
                valid_rels.append(rel)
            else:
                logger.warning(f"Dropping orphaned relationship: {source} -> {target}")
                
        extracted['relationships'] = valid_rels
        return extracted

    async def extract_from_batch(
        self,
        chunks: List[Dict[str, Any]],
        max_concurrent: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Extract entities and relationships from multiple chunks in parallel.
        
        Args:
            chunks: List of chunk dicts
            max_concurrent: Maximum concurrent LLM calls
        
        Returns:
            List of extraction results (excludes None values)
        """
        logger.info(f"Starting batch extraction for {len(chunks)} chunks")
        
        # Process in batches to avoid rate limits
        results = []
        for i in range(0, len(chunks), max_concurrent):
            batch = chunks[i:i + max_concurrent]
            batch_results = await asyncio.gather(
                *[self.extract_from_chunk(chunk) for chunk in batch],
                return_exceptions=True
            )
            
            # Filter out None and exceptions
            for result in batch_results:
                if result and not isinstance(result, Exception):
                    results.append(result)
            
            logger.info(f"Processed batch {i // max_concurrent + 1}, "
                       f"total results: {len(results)}")
            
            # Brief pause to stay under RPM limits
            if i + max_concurrent < len(chunks):
                await asyncio.sleep(1.0)
        
        logger.info(f"Batch extraction complete: {len(results)} successful extractions")
        return results
    
    def merge_extractions(self, extractions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge multiple extraction results into a single graph structure.
        
        Args:
            extractions: List of extraction dicts
        
        Returns:
            Merged graph with deduplicated entities and aggregated relationships
        """
        merged_entities = {}
        merged_relationships = []
        
        for extraction in extractions:
            # Merge entities (deduplicate by ID)
            for entity in extraction.get('entities', []):
                entity_id = entity.get('id')
                if entity_id:
                    if entity_id in merged_entities:
                        # Increment mention count
                        merged_entities[entity_id]['mentions'] += entity.get('mentions', 1)
                    else:
                        merged_entities[entity_id] = entity
            
            # Collect all relationships
            for rel in extraction.get('relationships', []):
                # Attach article metadata for temporal context
                rel['article_metadata'] = extraction.get('article_metadata', {})
                merged_relationships.append(rel)
        
        logger.info(f"Merged {len(merged_entities)} unique entities, "
                   f"{len(merged_relationships)} relationships")
        
        return {
            'entities': list(merged_entities.values()),
            'relationships': merged_relationships
        }
    
    async def extract_story_arc(
        self,
        articles: List[Dict[str, Any]],
        chunker = None
    ) -> Dict[str, Any]:
        """
        Extract complete story arc from multiple articles.
        
        Args:
            articles: List of processed articles
            chunker: TextChunker instance (optional, creates new if None)
        
        Returns:
            Complete graph structure with entities and relationships
        """
        logger.info(f"Extracting story arc from {len(articles)} articles")
        
        # Chunker initialization for long articles
        from ingestion.chunker import ArticleChunker
        default_chunker = ArticleChunker()
        
        chunks = []
        for article in articles:
            body = article.get('body', '') or article.get('content', '')
            if len(body) > 1000: # Re-chunk long articles
                from models.schemas import ProcessedArticle
                processed = ProcessedArticle(
                    article_id=article.get('article_id', 'unknown'),
                    title=article.get('title', 'Unknown'),
                    clean_body=body,
                    normalized_date=article.get('date', 'Recent'),
                    image_url=article.get('image_url'),
                    url=article.get('url', ''),
                    tags=article.get('tags', [])
                )
                article_chunks = default_chunker.chunk_article(processed)
                for c in article_chunks:
                    chunks.append({'text': c.text, 'metadata': c.metadata})
            else:
                chunks.append({
                    'text': body,
                    'metadata': {
                        'title': article.get('title', ''),
                        'date': article.get('date', 'Recent'),
                        'tags': article.get('tags', []),
                        'article_id': article.get('article_id', 'unknown'),
                        'url': article.get('url', ''),
                        'image_url': article.get('image_url', '')
                    }
                })
        
        logger.info(f"Processing {len(chunks)} chunks")
        
        # Extract from all chunks
        extractions = await self.extract_from_batch(chunks)
        
        # Merge into single graph
        graph = self.merge_extractions(extractions)
        
        # Add timeline metadata
        dates = [
            extraction.get('article_metadata', {}).get('date')
            for extraction in extractions
            if extraction.get('article_metadata', {}).get('date')
        ]
        
        if dates:
            graph['timeline'] = {
                'start_date': min(dates),
                'end_date': max(dates),
                'total_articles': len(articles)
            }
        
        return graph


async def test_extraction():
    """Test the graph extraction with sample articles."""
    logger.info("=" * 80)
    logger.info("PHASE 6 TEST: GraphRAG Entity & Relationship Extraction")
    logger.info("=" * 80)
    
    # Check for API key
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.error("❌ GROQ_API_KEY not set. Please set environment variable.")
        logger.info("Example: export GROQ_API_KEY='your-api-key-here'")
        return
    
    # Initialize extractor
    extractor = GraphExtractor()
    
    # Test with sample article
    sample_chunk = {
        'text': """Tata Motors has announced a strategic partnership with Tesla to develop 
        next-generation electric vehicle batteries. The collaboration, valued at $500 million, 
        will focus on solid-state battery technology. CEO Shailesh Chandra expressed optimism 
        about the partnership, stating it will accelerate India's EV adoption. However, 
        industry analyst Rajesh Kumar from ICICI Securities criticized the move, calling it 
        "too risky" given Tesla's recent production challenges. The announcement caused Tata 
        Motors stock to surge 8% while competitor Mahindra & Mahindra dropped 3%.""",
        'metadata': {
            'title': 'Tata Motors Partners with Tesla for EV Battery Development',
            'date': '2026-03-25',
            'tags': ['TATAMOTORS', 'TESLA', 'EV', 'AUTO'],
            'article_id': 'test123',
            'url': 'https://economictimes.indiatimes.com/test',
            'image_url': 'https://img.etimg.com/test.jpg'
        }
    }
    
    # Test 1: Single chunk extraction
    logger.info("\\n" + "=" * 80)
    logger.info("TEST 1: Single Chunk Extraction")
    logger.info("=" * 80)
    
    result = await extractor.extract_from_chunk(sample_chunk)
    
    if result:
        logger.info(f"✅ Extraction successful")
        logger.info(f"Entities extracted: {len(result['entities'])}")
        logger.info(f"Relationships extracted: {len(result['relationships'])}")
        
        logger.info("\\nEntities:")
        for entity in result['entities']:
            logger.info(f"  - {entity['name']} ({entity['type']}) [ID: {entity['id']}]")
        
        logger.info("\\nRelationships:")
        for rel in result['relationships']:
            logger.info(f"  - {rel['source']} --[{rel['type']}]--> {rel['target']}")
            logger.info(f"    Sentiment: {rel['sentiment']:.2f}")
            logger.info(f"    Evidence: {rel['evidence'][:100]}...")
    else:
        logger.error("❌ Extraction failed")
    
    # Test 2: Batch extraction with fallback articles
    logger.info("\\n" + "=" * 80)
    logger.info("TEST 2: Batch Extraction with Fallback Articles")
    logger.info("=" * 80)
    
    try:
        from ingestion.data_collector import DataCollector
        
        collector = DataCollector()
        articles = collector.load_fallback_data()[:3]  # Test with first 3 articles
        
        logger.info(f"Loaded {len(articles)} articles for testing")
        
        # Extract story arc
        graph = await extractor.extract_story_arc(articles)
        
        logger.info(f"✅ Story arc extraction complete")
        logger.info(f"Total unique entities: {len(graph['entities'])}")
        logger.info(f"Total relationships: {len(graph['relationships'])}")
        
        if 'timeline' in graph:
            logger.info(f"Timeline: {graph['timeline']['start_date']} to {graph['timeline']['end_date']}")
        
        # Show sample entities
        logger.info("\\nSample Entities:")
        for entity in graph['entities'][:5]:
            logger.info(f"  - {entity['name']} ({entity['type']}) - {entity['mentions']} mentions")
        
        # Show sample relationships
        logger.info("\\nSample Relationships:")
        for rel in graph['relationships'][:5]:
            logger.info(f"  - {rel['source']} --[{rel['type']}]--> {rel['target']}")
            logger.info(f"    Sentiment: {rel.get('sentiment', 0):.2f}")
        
    except ImportError:
        logger.warning("⚠️ Could not import DataCollector. Skipping batch test.")
    except Exception as e:
        logger.error(f"❌ Batch extraction error: {e}")
    
    logger.info("\\n" + "=" * 80)
    logger.info("PHASE 6 TEST COMPLETE")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_extraction())
