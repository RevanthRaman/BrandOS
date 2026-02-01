import requests
from urllib.parse import urlparse
import re
from utils.ai_engine import calculate_readability

def fetch_robots_txt(url):
    """Fetches the robots.txt content for a given URL."""
    try:
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        robots_url = f"{base_url}/robots.txt"
        
        response = requests.get(robots_url, timeout=5, headers={"User-Agent": "Mozilla/5.0 (compatible; BrandGenie/1.0)"})
        if response.status_code == 200:
            return response.text
        return None
    except:
        return None

def check_ai_bot_blocking(robots_content):
    """
    Checks if common AI bots are blocked in robots.txt.
    Returns a dict of {bot_name: status (Allowed/Blocked)}.
    """
    if not robots_content:
        return {"GPTBot": "Unknown (No robots.txt)", "CCBot": "Unknown", "Google-Extended": "Unknown"}
    
    bots = {
        "GPTBot": "OpenAI",
        "CCBot": "Common Crawl", 
        "Google-Extended": "Gemini/Bard",
        "anthropic-ai": "Claude",
        "PerplexityBot": "Perplexity"
    }
    
    results = {}
    
    # Simple parser: check for "User-agent: BotName" followed by "Disallow: /"
    # This is a heuristic. A full parser is complex, but this covers 90% of "Block All" cases.
    
    lines = robots_content.split('\n')
    current_agent = None
    
    bot_status = {k: "Allowed" for k in bots.keys()} # Default to Allowed
    
    for line in lines:
        line = line.strip()
        if line.lower().startswith('user-agent:'):
            agent = line.split(':')[1].strip()
            current_agent = agent
        
        if line.lower().startswith('disallow:') and current_agent:
            path = line.split(':')[1].strip()
            if path == "/": # Blocking root
                # Check if current_agent matches any of our bots
                for bot_key in bots.keys():
                    if bot_key.lower() in current_agent.lower() or current_agent == "*":
                        # If * is blocked, everyone is blocked (unless specific Allow overrides, which we ignore for simplicity)
                        bot_status[bot_key] = "Blocked"
    
    return bot_status

def audit_site_for_ai(url, html_content=None):
    """
    Performs a lightweight audit of the site for AI Readiness.
    1. Robots.txt (Blocking AI?)
    2. Schema Markup (Structured Data?)
    3. Readability (Digestible?)
    """
    audit_results = {
        "robots_status": {},
        "schema_found": [],
        "readability_score": 0,
        "is_ai_friendly": True,
        "warnings": []
    }
    
    # 1. Robots.txt
    robots_txt = fetch_robots_txt(url)
    audit_results["robots_status"] = check_ai_bot_blocking(robots_txt)
    
    # Check if any major bot is blocked
    blocked_count = sum(1 for v in audit_results["robots_status"].values() if v == "Blocked")
    if blocked_count > 0:
        audit_results["is_ai_friendly"] = False
        audit_results["warnings"].append(f"Blocking {blocked_count} major AI crawlers (robots.txt).")

    # 2. Schema Markup (using Regex on HTML)
    if html_content:
        # Look for <script type="application/ld+json">
        schema_matches = re.findall(r'<script\s+type=["\']application/ld\+json["\']>(.*?)</script>', html_content, re.DOTALL)
        
        found_types = set()
        for schema_json in schema_matches:
            try:
                # Naive text check for types to avoid full JSON parsing errors if malformed
                if '"@type":' in schema_json or '"@type" :' in schema_json:
                    # Extract the type value
                    type_match = re.search(r'"@type"\s*:\s*"([^"]+)"', schema_json)
                    if type_match:
                        found_types.add(type_match.group(1))
            except:
                pass
        
        audit_results["schema_found"] = list(found_types)
        
        if not found_types:
            audit_results["warnings"].append("No Structured Data (JSON-LD) found. Hard for AI to parse entities.")
            # Not necessarily 'Unfriendly', but not optimized.
        
        # 3. Readability
        # Strip HTML tags for text analysis
        text_only = re.sub(r'<[^>]+>', ' ', html_content)
        text_only = re.sub(r'\s+', ' ', text_only).strip()
        
        score = calculate_readability(text_only[:5000]) # Analyze first 5k chars
        audit_results["readability_score"] = score
        
        # Flesch-Kincaid: 60-70 is standard. < 30 is confusing. > 90 is very simple.
        # AI loves clear structure.
        if score > 14: # Grade level 14+ (Academic/Complex)
             audit_results["warnings"].append(f"Content is very complex (Grade {score}). Simplify for better AI digestion.")
    
    return audit_results
