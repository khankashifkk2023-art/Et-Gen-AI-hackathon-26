"""
ET Nexus — Visual Engine
Fetches high-quality B-roll from Pexels Video / Photo API.
"""

import os
import httpx
from typing import Optional

class VisualEngine:
    """
    The 'Visual Director' — fetches background assets for scenes.
    Uses Pexels API for stock footage B-roll.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("PEXELS_API_KEY")
        self.base_url = "https://api.pexels.com/videos/search"
        self.headers = {"Authorization": self.api_key}

    async def fetch_broll(self, keyword: str) -> Optional[str]:
        """
        Searches for a 5-10 second video clip on Pexels.
        Returns the CDN URL to the MP4 file.
        """
        if not self.api_key:
            print("⚠️  Pexels API Key not found. Video fetching disabled.")
            return None
            
        params = {
            "query": keyword,
            "per_page": 10, # Get more to allow random selection
            "orientation": "landscape",
            "size": "medium"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.base_url, params=params, headers=self.headers)
                response.raise_for_status()
                
                data = response.json()
                videos = data.get("videos", [])
                
                if videos:
                    # Pick a different video for every scene to avoid the 'stuck' visual
                    import random
                    # Pick from top 5 to maintain relevance, but not just the #1
                    video = random.choice(videos[:5])
                    
                    video_files = video.get("video_files", [])
                    if video_files:
                        # Prefer HD quality if available
                        hd_files = [f for f in video_files if f.get("quality") == "hd"]
                        if hd_files:
                            return hd_files[0]["link"]
                        return video_files[0]["link"]
                        
            print(f"❌  No B-roll found for: '{keyword}'")
            return None
            
        except Exception as e:
            print(f"Visual Engine Error for '{keyword}': {str(e)}")
            return None
