"""
ET Nexus — Real-Time Data Collector
Fetches live articles from Economic Times RSS feeds with newspaper3k deep scraping.
Integrated from Data Layer codebase, adapted to use existing Pydantic schemas.
"""

import asyncio
import json
import time
import hashlib
import logging
from typing import List, Dict, Optional
from pathlib import Path

import feedparser

try:
    from newspaper import Article
except ImportError:
    Article = None

from models.schemas import ScrapedArticle

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("data_collector")


# ─── ET RSS Feed URLs ──────────────────────────────────────────
ET_RSS_FEEDS = {
    "Top Stories": "https://economictimes.indiatimes.com/rssfeeds/1221656.cms",
    "Markets": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "Politics": "https://economictimes.indiatimes.com/news/politics/rssfeeds/10527315.cms",
    "Tech": "https://economictimes.indiatimes.com/tech/rssfeeds/13357270.cms",
    "Economy": "https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380680.cms",
    "Startups": "https://economictimes.indiatimes.com/small-biz/startups/rssfeeds/11993050.cms",
    "Wealth": "https://economictimes.indiatimes.com/wealth/rssfeeds/8375554.cms",
    "Industry": "https://economictimes.indiatimes.com/industry/rssfeeds/13352306.cms",
    "Environment": "https://economictimes.indiatimes.com/news/environment/rssfeeds/22753303.cms",
    "International": "https://economictimes.indiatimes.com/news/international/world/rssfeeds/61541381.cms",
    "Opinion": "https://economictimes.indiatimes.com/opinion/rssfeeds/12183310.cms",
    "Mutual Funds": "https://economictimes.indiatimes.com/markets/mutual-funds/rssfeeds/1977021501.cms",
    "Corporate Governance": "https://economictimes.indiatimes.com/news/company/corporate-trends/corporate-governance/rssfeeds/34988716.cms",
}

FALLBACK_DATA_PATH = Path(__file__).parent.parent / "data" / "fallback_articles.json"
MIN_ARTICLE_LENGTH = 200
POLITE_DELAY = 1.0  # seconds between scrape requests


class DataCollector:
    """
    Collects articles from ET RSS feeds with fallback support.
    
    Features:
    - RSS feed parsing with feedparser
    - Full article deep-scraping with newspaper3k
    - Rate limiting (1 second between requests)
    - Article length filtering (min 200 chars)
    - Automatic fallback to static dataset on failure
    - Returns data as ScrapedArticle Pydantic models
    """
    
    def __init__(self, fallback_path: str = None):
        self.fallback_path = fallback_path or str(FALLBACK_DATA_PATH)
        self.last_request_time = 0
        logger.info("DataCollector initialized")
    
    async def collect_from_rss(
        self, 
        rss_feeds: Dict[str, str] = None, 
        limit_per_feed: int = 5
    ) -> List[ScrapedArticle]:
        """
        Collect articles from RSS feeds with deep scraping.
        Falls back to offline dataset if scraping fails.
        
        Args:
            rss_feeds: Dict mapping category name to RSS feed URL
            limit_per_feed: Maximum articles per feed
            
        Returns:
            List of ScrapedArticle Pydantic models
        """
        if rss_feeds is None:
            rss_feeds = ET_RSS_FEEDS
        
        logger.info(f"📡 Starting collection from {len(rss_feeds)} RSS feeds")
        articles: List[ScrapedArticle] = []
        seen_hashes: set = set()
        
        try:
            for category, feed_url in rss_feeds.items():
                logger.info(f"   Fetching category [{category}]: {feed_url}")
                
                try:
                    feed = feedparser.parse(feed_url)
                    
                    if not feed.entries:
                        logger.warning(f"   No entries found in feed: {category}")
                        continue
                    
                    for entry in feed.entries[:limit_per_feed]:
                        try:
                            article_url = entry.link
                            title = entry.get("title", "Untitled")
                            
                            # Dedup by title hash
                            title_hash = hashlib.md5(title.strip().lower().encode()).hexdigest()
                            if title_hash in seen_hashes:
                                logger.info(f"      🔁 Duplicate skipped: {title[:40]}")
                                continue
                            seen_hashes.add(title_hash)
                            
                            logger.info(f"      → Scraping: {title[:60]}...")
                            
                            # Deep scrape full article
                            body, image_url = await self._scrape_article(article_url)
                            
                            # Fallback to RSS summary if scraping fails
                            if len(body) < MIN_ARTICLE_LENGTH:
                                body = entry.get("summary", "")
                                if len(body) < MIN_ARTICLE_LENGTH:
                                    logger.info(f"      ⏭️  Skipping (too short): {title[:40]}")
                                    continue

                            # If newspaper3k didn't find an image, try RSS-provided media thumbnail.
                            if not isinstance(image_url, str) or not image_url.strip():
                                image_url = self._extract_image_from_entry(entry)

                            # Only keep articles with a non-empty thumbnail image.
                            if not isinstance(image_url, str) or not image_url.strip():
                                logger.info(f"      ⏭️  Skipping (no image thumbnail): {title[:40]}")
                                continue
                            
                            # Extract tags from categories + add primary category tag
                            tags = [category]
                            if hasattr(entry, "tags"):
                                entry_tags = [t.get("term", "") for t in entry.tags if t.get("term")]
                                # Merge and avoid duplicates while preserving order
                                for t in entry_tags:
                                    if t and t not in tags:
                                        tags.append(t)
                            
                            # Extract date
                            date = entry.get("published", entry.get("updated", "Recent"))
                            
                            # Generate article ID
                            article_id = hashlib.sha256(article_url.encode()).hexdigest()[:32]
                            
                            article = ScrapedArticle(
                                article_id=article_id,
                                title=title,
                                date=date,
                                body=body,
                                image_url=image_url,
                                url=article_url,
                                tags=tags,
                                source="Economic Times"
                            )
                            articles.append(article)
                        
                        except Exception as e:
                            logger.error(f"      ⚠️ Error processing entry: {e}")
                            continue
                
                except Exception as e:
                    logger.error(f"   ⚠️ Error fetching feed {feed_url}: {e}")
                    continue
            
            if not articles:
                logger.warning("⚠️ No articles collected from RSS feeds, loading fallback dataset")
                return self._load_fallback()
            
            logger.info(f"✅ Collected {len(articles)} articles from RSS feeds")
            return articles
        
        except Exception as e:
            logger.error(f"❌ Critical error in RSS collection: {e}")
            logger.warning("⚠️ Falling back to static dataset")
            return self._load_fallback()

    def _extract_image_from_entry(self, entry) -> Optional[str]:
        """
        RSS feeds sometimes provide thumbnails via media tags.
        Try common feedparser keys, fallback to None.
        """
        def pick_url(val) -> Optional[str]:
            if not val:
                return None
            if isinstance(val, str):
                return val.strip() or None
            if isinstance(val, dict):
                u = val.get("url") or val.get("href")
                return (u or "").strip() or None
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, str):
                        u = item.strip()
                        if u:
                            return u
                    if isinstance(item, dict):
                        u = item.get("url") or item.get("href")
                        u = (u or "").strip()
                        if u:
                            return u
            return None

        for key in ["media_thumbnail", "media:thumbnail", "media_content", "image", "image_url", "enclosures"]:
            try:
                if hasattr(entry, "get"):
                    url = pick_url(entry.get(key))
                else:
                    url = None
                if url:
                    return url
            except Exception:
                continue
        return None
    
    async def _scrape_article(self, url: str) -> tuple:
        """
        Scrape full article content using newspaper3k.
        Returns (body_text, image_url) tuple.
        """
        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < POLITE_DELAY:
            await asyncio.sleep(POLITE_DELAY - time_since_last)
        self.last_request_time = time.time()
        
        body = ""
        image_url = None
        
        if Article is not None:
            try:
                article = Article(url)
                article.download()
                article.parse()
                body = article.text
                image_url = article.top_image
            except Exception as e:
                logger.warning(f"      ⚠️ newspaper3k failed: {e}")
        
        return body, image_url
    
    def _load_fallback(self) -> List[ScrapedArticle]:
        """Load static fallback dataset from JSON file."""
        try:
            fallback_file = Path(self.fallback_path)
            
            if not fallback_file.exists():
                logger.error(f"❌ Fallback file not found: {self.fallback_path}")
                return []
            
            with open(fallback_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle both flat list and {"articles": [...]} formats
            if isinstance(data, dict) and "articles" in data:
                raw_articles = data["articles"]
            elif isinstance(data, list):
                raw_articles = data
            else:
                raw_articles = []
            
            articles = []
            for item in raw_articles:
                if "source" not in item:
                    item["source"] = "Economic Times"
                articles.append(ScrapedArticle(**item))
            
            logger.info(f"✅ Loaded {len(articles)} articles from fallback dataset")
            return articles
        
        except Exception as e:
            logger.error(f"❌ Error loading fallback dataset: {e}")
            return []
    
    async def collect_by_category(
        self,
        categories: List[str] = None,
        limit_per_feed: int = 5
    ) -> List[ScrapedArticle]:
        """
        Collect articles from specific ET RSS categories.
        
        Args:
            categories: List of category keys from ET_RSS_FEEDS 
                        (e.g., ["Markets", "Tech"])
            limit_per_feed: Max articles per feed
        """
        if categories is None:
            categories = list(ET_RSS_FEEDS.keys())
        
        feed_map = {cat: ET_RSS_FEEDS[cat] for cat in categories if cat in ET_RSS_FEEDS}
        
        if not feed_map:
            logger.warning(f"⚠️ No valid categories: {categories}")
            logger.info(f"   Valid categories: {list(ET_RSS_FEEDS.keys())}")
            return []
        
        return await self.collect_from_rss(feed_map, limit_per_feed)


# ─── Convenience Functions ──────────────────────────────────────

async def fetch_live_articles(
    categories: List[str] = None,
    limit_per_feed: int = 5
) -> List[ScrapedArticle]:
    """Convenience async function for fetching live articles."""
    collector = DataCollector()
    if categories:
        return await collector.collect_by_category(categories, limit_per_feed=limit_per_feed)
    return await collector.collect_from_rss(limit_per_feed=limit_per_feed)


# Standalone test
if __name__ == "__main__":
    async def test():
        collector = DataCollector()
        articles = await collector.collect_from_rss(limit_per_feed=2)
        print(f"\nCollected {len(articles)} articles:")
        for a in articles[:3]:
            print(f"  - {a.title[:60]}... ({len(a.body)} chars)")
    
    asyncio.run(test())
