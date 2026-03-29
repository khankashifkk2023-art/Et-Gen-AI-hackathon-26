"""
ET Nexus — Article Preprocessor
Cleans raw HTML, normalizes dates, fixes unicode issues, and deduplicates.
"""

import re
import hashlib
from typing import Optional, Set

# ─── Module-level dedup cache ──────────────────────────────────
_seen_hashes: Set[str] = set()

try:
    import trafilatura
except ImportError:
    trafilatura = None

try:
    import ftfy
except ImportError:
    ftfy = None

try:
    import dateparser
except ImportError:
    dateparser = None

from models.schemas import ScrapedArticle, ProcessedArticle


def clean_html(raw_text: str) -> str:
    """
    Strips residual HTML tags, ads, and boilerplate from article text.
    Uses trafilatura if available, otherwise falls back to regex.
    """
    if not raw_text:
        return ""

    cleaned = raw_text

    # Remove HTML tags
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)

    # Remove common boilerplate patterns
    boilerplate_patterns = [
        r"(Also Read|Read More|Subscribe|Sign Up|Download App).*?(?:\n|$)",
        r"(Getty Images|Reuters|AFP|PTI|IANS).*?(?:\n|$)",
        r"(Published|Updated|Last Modified):?\s*\d.*?(?:\n|$)",
        r"\(.*?agency.*?\)",
    ]
    for pattern in boilerplate_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    # Fix unicode if ftfy is available
    if ftfy is not None:
        cleaned = ftfy.fix_text(cleaned)

    # Normalize whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned


def normalize_date(date_str: str) -> str:
    """
    Converts messy date strings into ISO format (YYYY-MM-DD).
    Handles: '2 hours ago', 'Mar 24, 2026', 'Yesterday', etc.
    """
    if not date_str or date_str == "Recent":
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d")

    if dateparser is not None:
        try:
            parsed = dateparser.parse(date_str)
            if parsed:
                return parsed.strftime("%Y-%m-%d")
        except Exception:
            pass

    # Fallback: try to extract any date-like pattern
    date_match = re.search(r"(\d{4})-(\d{2})-(\d{2})", date_str)
    if date_match:
        return date_match.group(0)

    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d")


def extract_clean_text(html_or_url: str) -> str:
    """
    Uses trafilatura for high-quality text extraction from HTML content.
    Falls back to basic regex cleaning.
    """
    if trafilatura is not None:
        try:
            extracted = trafilatura.extract(html_or_url)
            if extracted and len(extracted) > 100:
                return extracted
        except Exception:
            pass

    return clean_html(html_or_url)


def preprocess_article(article: ScrapedArticle) -> ProcessedArticle:
    """
    Full preprocessing pipeline for a single article.
    Cleans text, normalizes dates, fixes encoding.
    """
    # Clean the body text
    clean_body = clean_html(article.body)

    # Ensure minimum quality
    if len(clean_body) < 100:
        clean_body = article.body  # Keep original if cleaning removed too much

    # Normalize the date
    normalized_date = normalize_date(article.date)

    # Clean the title
    clean_title = article.title.strip()
    if ftfy is not None:
        clean_title = ftfy.fix_text(clean_title)

    return ProcessedArticle(
        article_id=article.article_id,
        title=clean_title,
        clean_body=clean_body,
        normalized_date=normalized_date,
        image_url=article.image_url,
        url=article.url,
        tags=article.tags,
        source=article.source,
    )


def _is_duplicate(article: ScrapedArticle) -> bool:
    """Check if article is a duplicate using title+URL hash."""
    hash_input = f"{article.title.strip().lower()}{article.url.strip()}"
    article_hash = hashlib.sha256(hash_input.encode()).hexdigest()
    if article_hash in _seen_hashes:
        return True
    _seen_hashes.add(article_hash)
    return False


def reset_dedup_cache():
    """Clear the deduplication cache (useful between ingestion runs)."""
    global _seen_hashes
    _seen_hashes = set()


def preprocess_batch(articles: list[ScrapedArticle]) -> list[ProcessedArticle]:
    """Preprocesses a batch of scraped articles with deduplication."""
    processed = []
    duplicates = 0
    for article in articles:
        try:
            if _is_duplicate(article):
                duplicates += 1
                print(f"   🔁 Duplicate skipped: {article.title[:40]}")
                continue
            p = preprocess_article(article)
            processed.append(p)
        except Exception as e:
            print(f"⚠️  Preprocessing failed for '{article.title[:40]}': {e}")
    print(f"✅ Preprocessed {len(processed)}/{len(articles)} articles ({duplicates} duplicates skipped)")
    return processed
