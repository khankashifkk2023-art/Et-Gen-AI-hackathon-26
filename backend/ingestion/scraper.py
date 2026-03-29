"""
ET Nexus — RSS & Article Scraper
Fetches live articles from Economic Times RSS feeds.
Falls back to offline dataset if scraping fails.
"""

import feedparser
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Optional

try:
    from newspaper import Article as NewspaperArticle
except ImportError:
    NewspaperArticle = None

from models.schemas import ScrapedArticle


# ─── Constants ──────────────────────────────────────────────────

DEFAULT_RSS_FEEDS = [
    "https://economictimes.indiatimes.com/rssfeeds/1221656.cms",        # Top Stories
    "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",  # Markets
    "https://economictimes.indiatimes.com/tech/rssfeeds/13357270.cms",  # Tech
]

FALLBACK_DATA_PATH = Path(__file__).parent.parent / "data" / "fallback_articles.json"
MIN_ARTICLE_LENGTH = 200  # Skip articles shorter than this (paywalls, stubs)
POLITE_DELAY = 1.0        # Seconds between scrape requests


# ─── Deduplication ──────────────────────────────────────────────

def _title_hash(title: str) -> str:
    """Generate a hash of the article title for deduplication."""
    normalized = title.strip().lower()
    return hashlib.md5(normalized.encode()).hexdigest()


def _pick_url(val) -> Optional[str]:
    """
    Best-effort extraction of a URL from various feedparser shapes:
    - list[dict] where dict has url/href
    - dict with url/href
    - direct string
    """
    if not val:
        return None
    if isinstance(val, str):
        return val.strip()
    if isinstance(val, dict):
        u = val.get("url") or val.get("href")
        return (u or "").strip() or None
    if isinstance(val, list):
        for item in val:
            if isinstance(item, str):
                u = item.strip()
                if u:
                    return u
            elif isinstance(item, dict):
                u = item.get("url") or item.get("href")
                u = (u or "").strip()
                if u:
                    return u
    return None


def _extract_image_from_entry(entry) -> Optional[str]:
    """
    RSS feeds sometimes provide thumbnails via media tags.
    Try common feedparser keys, fallback to None.
    """
    # Most common shapes from RSS media module
    for key in ["media_thumbnail", "media:thumbnail", "media_content", "image", "image_url", "enclosures"]:
        try:
            if hasattr(entry, "get"):
                url = _pick_url(entry.get(key))
            else:
                url = None
            if url:
                return url
        except Exception:
            continue
    return None


# ─── Live Scraper ───────────────────────────────────────────────

def scrape_rss_feed(rss_url: str, limit: int = 5) -> list[ScrapedArticle]:
    """
    Fetches articles from a single ET RSS feed.
    Uses newspaper3k to extract full text and images.
    """
    print(f"📡 Fetching live feed: {rss_url}")
    articles = []
    errors = []

    try:
        feed = feedparser.parse(rss_url)
        if not feed.entries:
            print(f"⚠️  No entries found in feed: {rss_url}")
            return articles

        for entry in feed.entries[:limit]:
            try:
                article_url = entry.link
                title = entry.get("title", "Untitled")
                print(f"   → Scraping: {title[:60]}...")

                # Extract full text using newspaper3k
                body = ""
                image_url = None

                if NewspaperArticle is not None:
                    try:
                        np_article = NewspaperArticle(article_url)
                        np_article.download()
                        np_article.parse()
                        body = np_article.text
                        image_url = np_article.top_image
                    except Exception as e:
                        print(f"   ⚠️  newspaper3k failed: {e}")

                # Fallback: use RSS summary if full text extraction failed
                if len(body) < MIN_ARTICLE_LENGTH:
                    body = entry.get("summary", "")
                    if len(body) < MIN_ARTICLE_LENGTH:
                        print(f"   ⏭️  Skipping (too short): {title[:40]}")
                        continue

                # If newspaper3k didn't find an image, try RSS-provided media thumbnail.
                if not isinstance(image_url, str) or not image_url.strip():
                    image_url = _extract_image_from_entry(entry)

                # Only keep articles with a non-empty thumbnail image.
                if not isinstance(image_url, str) or not image_url.strip():
                    print(f"   ⏭️  Skipping (no image thumbnail): {title[:40]}")
                    continue

                # Extract tags
                tags = []
                if hasattr(entry, "tags"):
                    tags = [t.get("term", "") for t in entry.tags if t.get("term")]
                if not tags:
                    tags = ["ET News"]

                # Extract date
                date = entry.get("published", entry.get("updated", "Recent"))

                article = ScrapedArticle(
                    article_id=_title_hash(title),
                    title=title,
                    date=date,
                    body=body,
                    image_url=image_url,
                    url=article_url,
                    tags=tags,
                    source="Economic Times"
                )
                articles.append(article)
                time.sleep(POLITE_DELAY)

            except Exception as e:
                err = f"Error scraping {entry.get('link', 'unknown')}: {e}"
                print(f"   ⚠️  {err}")
                errors.append(err)

    except Exception as e:
        print(f"❌ Feed fetch failed: {rss_url} — {e}")

    print(f"   ✅ Scraped {len(articles)} articles from feed")
    return articles


def scrape_multiple_feeds(
    rss_feeds: list[str] = None,
    limit_per_feed: int = 5
) -> tuple[list[ScrapedArticle], list[str]]:
    """
    Scrapes multiple RSS feeds with deduplication.
    Returns (articles, errors).
    """
    if rss_feeds is None:
        rss_feeds = DEFAULT_RSS_FEEDS

    all_articles: list[ScrapedArticle] = []
    all_errors: list[str] = []
    seen_hashes: set[str] = set()

    for feed_url in rss_feeds:
        feed_articles = scrape_rss_feed(feed_url, limit=limit_per_feed)
        for article in feed_articles:
            if article.article_id not in seen_hashes:
                seen_hashes.add(article.article_id)
                all_articles.append(article)
            else:
                print(f"   🔁 Duplicate skipped: {article.title[:40]}")

    print(f"\n📊 Total unique articles scraped: {len(all_articles)}")
    return all_articles, all_errors


# ─── Fallback: Offline Dataset ──────────────────────────────────

def load_fallback_articles() -> list[ScrapedArticle]:
    """
    Loads pre-downloaded articles from fallback_articles.json.
    Used when live scraping fails (IP blocked, no internet, etc.)
    """
    if not FALLBACK_DATA_PATH.exists():
        print("⚠️  No fallback dataset found. Creating sample...")
        _create_sample_fallback()

    print(f"📂 Loading fallback articles from: {FALLBACK_DATA_PATH}")
    with open(FALLBACK_DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Handle both flat list and {"articles": [...]} formats
    if isinstance(data, dict) and "articles" in data:
        raw_articles = data["articles"]
    elif isinstance(data, list):
        raw_articles = data
    else:
        print("⚠️  Unexpected fallback JSON format")
        raw_articles = []

    # Ensure 'source' field exists for each article
    articles = []
    for item in raw_articles:
        if "source" not in item:
            item["source"] = "Economic Times"
        articles.append(ScrapedArticle(**item))

    print(f"   ✅ Loaded {len(articles)} fallback articles")
    return articles


def _create_sample_fallback():
    """Creates a sample fallback dataset for demo purposes."""
    sample_articles = [
        {
            "article_id": "fallback_001",
            "title": "RBI Holds Interest Rates Steady at 6.5% Amid Global Uncertainty",
            "date": "2026-03-24",
            "body": (
                "The Reserve Bank of India (RBI) maintained its benchmark repo rate at 6.5% "
                "for the eighth consecutive time, citing persistent global economic uncertainty and "
                "domestic inflation concerns. The Monetary Policy Committee (MPC) voted 4-2 in favor "
                "of maintaining the status quo. RBI Governor Shaktikanta Das highlighted that while "
                "India's GDP growth remains robust at 7.2%, the central bank needs to remain vigilant "
                "about food inflation which spiked to 8.7% in February. The decision has mixed "
                "implications for the banking sector — HDFC Bank and SBI shares rose 1.2% on the "
                "announcement, while NBFCs like Bajaj Finance saw a 0.8% decline. Market analysts "
                "expect the first rate cut in Q3 2026, contingent on monsoon performance and global "
                "commodity prices. The impact on auto loans and home loans remains neutral in the "
                "near term, though Tata Motors reported that sustained high rates are dampening "
                "consumer demand for mid-segment vehicles. The government's fiscal deficit target "
                "of 5.1% of GDP remains achievable, according to the Finance Ministry."
            ),
            "image_url": "https://via.placeholder.com/800x400?text=RBI+Rate+Decision",
            "url": "https://economictimes.indiatimes.com/example/rbi-rates",
            "tags": ["RBI", "Interest Rates", "Banking", "HDFCBANK", "TATAMOTORS", "Markets"],
            "source": "Economic Times"
        },
        {
            "article_id": "fallback_002",
            "title": "Tata Motors EV Sales Surge 45% as New Subsidies Kick In",
            "date": "2026-03-23",
            "body": (
                "Tata Motors reported a 45% year-on-year increase in electric vehicle sales for "
                "March 2026, driven by the government's enhanced EV subsidy scheme announced in the "
                "Union Budget. The company sold 18,500 EVs in the month, with the Nexon EV and "
                "Punch EV leading the charge. The new FAME III policy provides up to ₹1.5 lakh "
                "subsidy per vehicle, making EVs nearly price-competitive with combustion engine "
                "alternatives. Tata Motors' EV market share has risen to 62% in India, maintaining "
                "its dominant position. However, analysts warn that rising lithium prices could "
                "squeeze margins in Q2 FY27. The stock rallied 3.8% on the BSE, touching ₹985 per "
                "share. Competing automakers Mahindra & Mahindra and Hyundai are also ramping up "
                "their EV portfolios, with Mahindra's XUV400 gaining traction in Tier-2 cities. "
                "Industry experts project India's EV penetration will reach 15% by 2028, up from "
                "the current 8%. Infrastructure remains a concern — ChargeZone and Tata Power are "
                "deploying 5,000 new charging stations across highways this fiscal year."
            ),
            "image_url": "https://via.placeholder.com/800x400?text=Tata+EV+Sales",
            "url": "https://economictimes.indiatimes.com/example/tata-ev-sales",
            "tags": ["TATAMOTORS", "EV", "Auto", "Subsidies", "Markets"],
            "source": "Economic Times"
        },
        {
            "article_id": "fallback_003",
            "title": "HDFC Bank Q4 Results: Net Profit Jumps 22% to ₹16,500 Crore",
            "date": "2026-03-22",
            "body": (
                "HDFC Bank reported a stellar Q4 FY26, with net profit surging 22% year-on-year "
                "to ₹16,500 crore, beating analyst estimates of ₹15,800 crore. Net interest income "
                "(NII) grew 18% to ₹31,200 crore, supported by healthy loan growth of 16.5%. "
                "The bank's asset quality improved with gross NPAs declining to 1.24% from 1.36% "
                "in the previous quarter. The merger with HDFC Ltd continues to yield synergies, "
                "with the combined entity's home loan portfolio crossing ₹7 lakh crore. CEO "
                "Sashidhar Jagdishan stated that the focus for FY27 would be on expanding the "
                "rural and semi-urban branch network, targeting 1,000 new branches. Digital "
                "transactions now account for 95% of all customer interactions. The stock closed "
                "at ₹1,685 per share, up 2.1%. Analysts maintain a 'Buy' rating with a 12-month "
                "target of ₹1,900. The banking sector outlook remains positive, though the RBI's "
                "tightening stance on unsecured lending could impact retail credit growth."
            ),
            "image_url": "https://via.placeholder.com/800x400?text=HDFC+Bank+Results",
            "url": "https://economictimes.indiatimes.com/example/hdfc-results",
            "tags": ["HDFCBANK", "Banking", "Quarterly Results", "Markets"],
            "source": "Economic Times"
        },
        {
            "article_id": "fallback_004",
            "title": "India's AI Startup Ecosystem Raises $4.2 Billion in FY26",
            "date": "2026-03-21",
            "body": (
                "India's artificial intelligence startup ecosystem attracted $4.2 billion in "
                "funding during FY26, a 67% increase from the previous fiscal year. The surge was "
                "led by enterprise AI companies focusing on healthcare, fintech, and manufacturing. "
                "Key deals included Krutrim AI's $500 million Series B and Sarvam AI's $200 million "
                "round. The government's IndiaAI Mission, with its ₹10,300 crore allocation, has "
                "catalyzed GPU infrastructure buildout across the country. Bengaluru remains the "
                "AI capital with 45% of startups, followed by Hyderabad (18%) and Mumbai (15%). "
                "However, the talent gap remains critical — India needs 1.5 million AI engineers by "
                "2028, but currently has only 400,000. Large tech companies like Infosys and TCS "
                "are investing heavily in upskilling programs. The regulatory framework remains "
                "under discussion, with the Digital India Act expected to include AI governance "
                "provisions. Global AI majors including OpenAI, Anthropic, and Google DeepMind "
                "have expanded their India operations, drawn by the country's engineering talent "
                "pool and growing enterprise demand."
            ),
            "image_url": "https://via.placeholder.com/800x400?text=India+AI+Startups",
            "url": "https://economictimes.indiatimes.com/example/ai-startups",
            "tags": ["AI", "Startups", "Technology", "Funding", "INFY", "TCS"],
            "source": "Economic Times"
        },
        {
            "article_id": "fallback_005",
            "title": "Union Budget 2026: Key Highlights for Markets and Investors",
            "date": "2026-03-20",
            "body": (
                "Finance Minister Nirmala Sitharaman presented the Union Budget 2026-27 with a "
                "focus on infrastructure, green energy, and digital economy. Capital expenditure "
                "has been raised to ₹12.5 lakh crore, a 15% increase. Key highlights for market "
                "participants include: 1) Long-term capital gains tax on equities reduced from 12.5% "
                "to 10% for holdings above 2 years, 2) Standard deduction for salaried employees "
                "increased to ₹75,000, 3) Production-linked incentives (PLI) extended to AI "
                "hardware and semiconductor manufacturing, 4) Green hydrogen fund of ₹25,000 crore "
                "announced. The Sensex rallied 1,200 points on budget day, with Reliance Industries, "
                "L&T, and Adani Green being the top gainers. However, the increase in securities "
                "transaction tax (STT) on derivatives drew criticism from the trading community. "
                "Foreign institutional investors (FIIs) net purchased ₹3,500 crore worth of Indian "
                "equities on budget day, signaling global confidence. Mutual fund SIP inflows "
                "continued their upward trajectory, crossing ₹22,000 crore per month."
            ),
            "image_url": "https://via.placeholder.com/800x400?text=Union+Budget+2026",
            "url": "https://economictimes.indiatimes.com/example/union-budget",
            "tags": ["Budget", "Markets", "Tax", "Infrastructure", "RELIANCE"],
            "source": "Economic Times"
        },
        {
            "article_id": "fallback_006",
            "title": "Infosys Wins $2 Billion AI Transformation Deal with European Bank",
            "date": "2026-03-19",
            "body": (
                "Infosys announced its largest-ever deal — a $2 billion, seven-year AI transformation "
                "contract with a leading European bank. The engagement involves deploying Infosys' "
                "Topaz AI platform across the bank's retail and corporate banking operations, "
                "automating credit underwriting, fraud detection, and customer service workflows. "
                "CEO Salil Parekh stated this deal 'validates our strategy of leading with AI-first "
                "solutions.' The stock surged 4.5% to ₹1,920 on the BSE. The deal is expected to "
                "add $280 million in annual revenue starting Q2 FY27. Infosys has been aggressively "
                "investing in generative AI capabilities, with over 12,000 employees now certified "
                "in AI technologies. The IT sector is witnessing a pivot from traditional outsourcing "
                "to AI-driven value creation, with deal sizes expanding significantly. Competitors "
                "TCS and Wipro have also reported strong AI deal pipelines. However, margin pressure "
                "remains a concern as AI projects require higher upfront investments. Infosys "
                "maintained its FY27 revenue growth guidance of 13-15% in constant currency terms."
            ),
            "image_url": "https://via.placeholder.com/800x400?text=Infosys+AI+Deal",
            "url": "https://economictimes.indiatimes.com/example/infosys-deal",
            "tags": ["INFY", "IT", "AI", "Banking", "Technology"],
            "source": "Economic Times"
        },
    ]

    os.makedirs(FALLBACK_DATA_PATH.parent, exist_ok=True)
    with open(FALLBACK_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(sample_articles, f, indent=2, ensure_ascii=False)
    print(f"   ✅ Created sample fallback dataset at {FALLBACK_DATA_PATH}")


# ─── Master Scrape Function ────────────────────────────────────

def fetch_articles(
    rss_feeds: list[str] = None,
    limit_per_feed: int = 5,
    use_fallback: bool = False
) -> tuple[list[ScrapedArticle], list[str]]:
    """
    Main entry point for article fetching.
    Tries live scraping first, falls back to offline dataset on failure.
    """
    if use_fallback:
        return load_fallback_articles(), []

    articles, errors = scrape_multiple_feeds(rss_feeds, limit_per_feed)

    # Fallback if no articles were scraped
    if not articles:
        print("\n⚠️  Live scraping returned 0 articles. Falling back to offline dataset...")
        articles = load_fallback_articles()
        errors.append("Live scraping failed — used fallback dataset")

    return articles, errors
