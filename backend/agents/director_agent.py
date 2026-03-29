"""
ET Nexus — Director Agent
Transforms financial analysis into a structured JSON screenplay for AI video briefings.
"""

import os
import json
import re
from groq import Groq

class DirectorAgent:
    """
    The 'TV News Director' — storyboarder for the AI Video Studio.
    Converts article context and agentic analysis into a scene-by-scene script.
    """
    
    def __init__(self, model: str = "llama-3.3-70b-versatile"):
        self.client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        self.model = model

    def storyboard(self, title: str, summary: str, bull_view: str, bear_view: str) -> list[dict]:
        """
        Generates a 4-6 scene storyboard JSON.
        """
        
        prompt = f"""
ROLE: You are a professional 'AI News Director' for the ET Nexus Intelligence Unit. 
TASK: Given the following financial analysis, create a 60-second broadcast-ready screenplay.

CONTEXT:
- Headline: {title}
- Summary: {summary}
- Bullish View: {bull_view}
- Bearish View: {bear_view}

OUTPUT REQUIREMENT:
Output ONLY a single JSON object with one key "scenes" whose value is an array of exactly 5 scene objects.
Do not include markdown, preamble, or trailing commentary.

Each scene object MUST have:
1. "scene_id": integer (1-5)
2. "narration": Professional broadcast text.
3. "search_keyword": A detailed and visually unique term for B-roll (e.g., if one scene is "finance", the next should be "busy stock floor", then "modern bank vault").
   IMPORTANT: Every scene MUST have a DIFFERENT visual concept. 
4. "overlay_text": Short text to display on screen (3-5 words).
5. "composition": One of ["LOWER_THIRD", "CENTER_TITLE", "FULL_SCREEN_IMAGE"].

STRICT TIMING RULE (CRITICAL):
The combined narration across ALL 5 scenes MUST be between 140 and 155 words when read aloud.
At roughly 150 words per minute, this yields about 60 seconds of audio. Do not output fewer than 140 words total.

SCENE STRUCTURE:
- Scene 1: Hook & Headline
- Scene 2: The Core Analysis (Summary)
- Scene 3: The Optimist View (Bullish)
- Scene 4: The Risk View (Bearish)
- Scene 5: Closing Outlook
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2500,
                response_format={"type": "json_object"} if "llama-3" in self.model else None
            )
            
            content = response.choices[0].message.content.strip()
            
            # Extract JSON if LLM added markdown wrappers
            if "```json" in content:
                content = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL).group(1)
            elif "```" in content:
                content = re.search(r"```\s*(.*?)\s*```", content, re.DOTALL).group(1)
                
            data = json.loads(content)
            
            # The LLM might return {"scenes": [...]} or just the array
            scenes: list = []
            if isinstance(data, dict) and "scenes" in data:
                scenes = data["scenes"]
            elif isinstance(data, list):
                scenes = data
            else:
                return []

            return self._ensure_min_word_count(scenes)

        except Exception as e:
            print(f"Director Agent Storyboard Error: {str(e)}")
            return []

    def _ensure_min_word_count(self, scenes: list) -> list:
        """Pad narration if the model returned too few words for ~60s audio."""
        if not scenes:
            return scenes
        filler = (
            " This story continues to evolve across markets and policy. "
            "Investors should weigh both opportunity and risk. "
            "Stay informed with ET Nexus for timely context and analysis."
        )
        full = " ".join(str(s.get("narration", "")) for s in scenes)
        n = len(re.findall(r"\w+", full))
        guard = 0
        while n < 140 and guard < 50:
            scenes[-1]["narration"] = str(scenes[-1].get("narration", "")) + filler
            full = " ".join(str(s.get("narration", "")) for s in scenes)
            n = len(re.findall(r"\w+", full))
            guard += 1
        return scenes
