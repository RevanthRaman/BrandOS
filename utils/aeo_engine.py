import time
import random
import functools
import os
import json
import requests
import utils.ai_engine as ai_engine
import concurrent.futures
import difflib
import re # Ensure re is imported
from urllib.parse import urlparse


# --- Retry Logic Decorator ---
def retry_with_backoff(retries=3, backoff_in_seconds=1):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            x = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    # Detect Rate Limits (429) or Service Overload (503)
                    # This depends on the library, but often they raise exceptions with these codes
                    # or we catch generic exceptions and retry.
                    # For now, we retry on ANY exception that represents a failure to get valid text.
                    
                    if x == retries:
                        return None, f"Max retries reached. Error: {str(e)}"
                    
                    sleep = (backoff_in_seconds * 2 ** x) + random.uniform(0, 1)
                    time.sleep(sleep)
                    x += 1
        return wrapper
    return decorator


# --- API Helpers ---

@retry_with_backoff(retries=3, backoff_in_seconds=2)
def query_gemini(prompt, api_key=None, model_name=None):
    """Queries Google's Gemini model using ai_engine's fallback logic."""
    try:
        # Use provided key or env var if needed (ai_engine also handles this)
        if api_key:
            os.environ["GEMINI_API_KEY"] = api_key
            
        # Use the provided model or default to Gemini 3 Pro for AEO tasks if not specified
        model = model_name or ai_engine.GEMINI_3_PRO_PREVIEW
        
        response_text = ai_engine.generate_gemini_response(prompt, model_name=model)
        
        # Check if the response from generate_gemini_response is an error JSON
        if '"error":' in response_text:
             # Raise exception to trigger retry
             raise Exception(f"API Error in response: {response_text}")
            
        return response_text, None
    except Exception as e:
        raise e # Let decorator handle it

@retry_with_backoff(retries=3, backoff_in_seconds=2)
def query_chatgpt(prompt, api_key=None):
    """Queries OpenAI's ChatGPT."""
    try:
        if not OPENAI_AVAILABLE:
            return None, "OpenAI library not installed"
            
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            return None, "Missing API Key"
            
        client = OpenAI(api_key=key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", # Cost-effective default
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content, None
    except Exception as e:
        raise e

@retry_with_backoff(retries=3, backoff_in_seconds=2)
def query_claude(prompt, api_key=None):
    """Queries Anthropic's Claude."""
    try:
        if not ANTHROPIC_AVAILABLE:
            return None, "Anthropic library not installed"
            
        key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not key:
            return None, "Missing API Key"
            
        client = anthropic.Anthropic(api_key=key)
        message = client.messages.create(
            model="claude-3-haiku-20240307", # Cost-effective default
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text, None
    except Exception as e:
        raise e

@retry_with_backoff(retries=3, backoff_in_seconds=2)
def query_perplexity(prompt, api_key=None):
    """Queries Perplexity AI."""
    try:
        key = api_key or os.getenv("PERPLEXITY_API_KEY")
        if not key:
            return None, "Missing API Key"
            
        url = "https://api.perplexity.ai/chat/completions"
        payload = {
            "model": "llama-3-sonar-small-32k-online",
            "messages": [
                {"role": "system", "content": "Be precise and concise."},
                {"role": "user", "content": prompt}
            ]
        }
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content'], None
        elif response.status_code == 429:
             raise Exception("Rate limited (429)")
        else:
            return None, f"Error {response.status_code}: {response.text}"
    except Exception as e:
        raise e

# --- Core Logic ---



def analyze_mention_json(response_data, brand_name, is_risk_analysis=False):
    """
    Analyzes a JSON-structured AI response.
    Expected structure:
    [
        {"rank": 1, "name": "Brand A", "description": "...", "sentiment": "Positive"},
        {"rank": 2, "name": "Brand B", "description": "...", "sentiment": "Neutral"}
    ]
    or
    {
        "ranking": [...],
        "sources": [...]
    }
    """
    
    brand_lower = brand_name.lower()
    
    mentioned = False
    sentiment = "N/A"
    rank = "Unranked"
    snippet = "No response"
    share_of_voice = 0
    competitors_found = []
    citations_found = []
    extracted_adjectives = []
    
    # Handle list or dict
    items = []
    if isinstance(response_data, list):
        items = response_data
    elif isinstance(response_data, dict):
        if "ranking" in response_data: items = response_data["ranking"]
        if "sources" in response_data: citations_found = response_data["sources"]
        
    total_list_items = len(items)
    brand_rank_val = 999
    
    # Iterate items
    for idx, item in enumerate(items):
        name = item.get("name", "Unknown")
        desc = item.get("description", "")
        item_rank = item.get("rank", idx + 1)
        
        # Check if user brand
        if brand_lower in name.lower():
            mentioned = True
            rank = item_rank
            if isinstance(rank, int): brand_rank_val = rank
            
            # Snippet & Sentiment
            # Snippet & Sentiment
            # [FIX] Include Rank in Snippet for Trust/Verification
            snippet = f"**#{item_rank} {name}** - {desc}"
            sentiment = item.get("sentiment", "Neutral")
            
            # Adjectives (from description)
            common_descriptors = [
               "innovative", "reliable", "expensive", "cheap", "fast", "slow", "secure", "vulnerable",
               "popular", "niche", "complex", "easy", "powerful", "limited", "corporate", "startup-friendly",
               "enterprise", "leading", "trusted", "questionable", "seamless", "clunky", "robust", "outdated"
            ]
            found_descs = [d for d in common_descriptors if d in desc.lower()]
            extracted_adjectives.extend(found_descs)
            
        else:
            # Competitor
            competitors_found.append({
                "rank": item_rank,
                "name": name
            })
            
    # Logic refinements
    if not mentioned:
        rank = "Unranked"
        share_of_voice = 0
    else:
        # Simple SoV (1 / Position) or Just Presence?
        # Use existing logic: Count mentions vs Total
        share_of_voice = round((1 / total_list_items) * 100, 1) if total_list_items > 0 else 0
        
        if is_risk_analysis:
             # Check for risk keywords in the description if not explicitly 'Negative'
             critical_keywords = ["scam", "fraud", "security breach", "unsafe", "avoid", "worst"]
             if any(x in snippet.lower() for x in critical_keywords):
                 sentiment = "CRITICAL WARNING"

    # Weighted SoV
    weight_sov = 0
    if total_list_items > 0:
        total_weight = sum(1/i for i in range(1, total_list_items + 1))
        brand_w = 1/brand_rank_val if mentioned and isinstance(brand_rank_val, int) else 0
        if total_weight > 0:
             weight_sov = round((brand_w / total_weight) * 100, 1)
             
    return {
        "mentioned": mentioned,
        "sentiment": sentiment,
        "rank": rank,
        "snippet": snippet,
        "share_of_voice": share_of_voice,
        "weighted_share_of_voice": weight_sov,
        "competitors_found": competitors_found,
        "citations_found": citations_found,
        "extracted_adjectives": extracted_adjectives,
        "total_list_items": total_list_items
    }


def check_visibility(brand_name, keywords, api_keys={}, gemini_model=None, intents=["General"], context="General Audience", region="United States (US)", runs=1, include_risk_analysis=False):
    """
    Checks brand visibility across multiple models for given keywords and intents.
    Supports stability testing by running multiple iterations.
    Supports 'Risk Analysis' to detect negative sentiment/reputation issues.
    """
    results = {}
    
    models = {
        "Gemini": query_gemini,
        "ChatGPT": query_chatgpt,
        "Claude": query_claude,
        "Perplexity": query_perplexity
    }
    
    # Map friendly names to API key keys
    key_map = {
        "Gemini": "gemini",
        "ChatGPT": "openai",
        "Claude": "anthropic",
        "Perplexity": "perplexity"
    }

    # Define Risk Intents (Negative Semantic Search)
    risk_intents = []
    if include_risk_analysis:
        risk_intents = ["Risk: Cost", "Risk: Security", "Risk: Avoidance"]

    # Combine regular intents + risk intents (if active)
    active_intents = intents + risk_intents

    # --- HELPER: Single Query Execution ---
    def execute_query(task):
        t_model_name, t_query_func, t_keyword, t_intent, t_run_idx, t_api_key = task
        
        # Stability: Small sleep if strict sequential, but we rely on rate limit backoff in parallel
        # time.sleep(0.5) 
        
        # Intent-based Prompt Construction
        # INJECT REGION HERE
        geo_context = f"Context: You are acting as a user searching from {region}. Prioritize results relevant to this location."
        
        # JSON Schema Instruction
        json_instruction = """
        Output strictly in JSON format. Do not use Markdown blocks.
        Result Structure:
        {
            "ranking": [
                {"rank": 1, "name": "Brand Name", "description": "Short explanation", "sentiment": "Positive/Neutral/Negative"}
            ],
            "sources": ["url1", "url2"]
        }
        """
        
        base_instruction = f"Return a strictly numbered list of the top 10 BRANDS/COMPANIES only. Do NOT list issues, features, or pros/cons as list items. {json_instruction}"
        
        is_risk = t_intent.startswith("Risk:")
        
        prompt = ""
        if t_intent == "Informational":
            prompt = f"{geo_context} What is {t_keyword}? Please explain the core concepts and key players who define this space. {base_instruction}"
        elif t_intent == "Commercial":
            prompt = f"{geo_context} I am looking for the best {t_keyword} for {context}. Who are the top contenders? Please compare the top options. {base_instruction}"
        elif t_intent == "Transactional":
            prompt = f"{geo_context} Where can I sign up for or buy {t_keyword}? What are the best options for {context} ready for immediate implementation? {base_instruction}"
        elif t_intent == "Risk: Cost":
            prompt = f"{geo_context} Which {t_keyword} providers are the most expensive or have hidden fees? Which are not worth the money? {base_instruction}"
        elif t_intent == "Risk: Security":
            prompt = f"{geo_context} Are there any {t_keyword} providers with security vulnerabilities, data breaches, or trust issues? Is {t_keyword} a space with many scams? {base_instruction}"
        elif t_intent == "Risk: Avoidance":
            prompt = f"{geo_context} Why should I avoid certain {t_keyword} providers? What are common reasons to switch away from popular brands in this space? {base_instruction}"
        else: # General
            prompt = f"{geo_context} I am looking for recommendations for {t_keyword}. Who are the top brands or solutions you would suggest? {base_instruction}"
        
        try:
            # Execute Model Call
            if t_model_name == "Gemini":
                 # Use JSON safe parsing where possible or text
                 response_text, error = t_query_func(prompt, api_key=t_api_key, model_name=gemini_model)
            else:
                 response_text, error = t_query_func(prompt, api_key=t_api_key)
            
            if error:
                 return {
                    "keyword": t_keyword,
                    "intent": t_intent,
                    "run_index": t_run_idx + 1,
                    "status": "error",
                    "error": error
                }
            
            # --- Analysis (Try JSON first, Fallback to Regex) ---
            parsed_json = ai_engine.parse_json_response(response_text)
            
            if parsed_json:
                analysis = analyze_mention_json(parsed_json, brand_name, is_risk_analysis=is_risk)
            else:
                # [FIX] Fallback to Regex Parsing
                fallback_data = extract_rankings_from_text(response_text)
                if fallback_data:
                    analysis = analyze_mention_json(fallback_data, brand_name, is_risk_analysis=is_risk)
                    analysis["snippet"] = "Source content was unstructured text. Parsed via Regex fallback."
                else:
                    # Final Fail State
                    analysis = {
                         "mentioned": False, "sentiment": "Error", "rank": "N/A", "snippet": "Failed to parse JSON and Regex Fallback failed.", 
                         "share_of_voice": 0, "competitors_found": [], "citations_found": []
                    }
                
            # Skip default block - handled in if/else above
            
            analysis["intent"] = t_intent
            
            return {
                "keyword": t_keyword,
                "intent": t_intent,
                "run_index": t_run_idx + 1,
                "status": "success",
                "analysis": analysis,
                "prompt_used": prompt
            }
            
        except Exception as e:
            return {
                "keyword": t_keyword,
                "intent": t_intent,
                "run_index": t_run_idx + 1,
                "status": "error",
                "error": str(e)
            }


    # --- HELPER: Regex Ranked List Extractor (Fallback) ---
    def extract_rankings_from_text(text):
        """
        Fallback parser when JSON fails. Looks for numbered lists like:
        1. BrandName - Description
        2) BrandName: Description
        """
        extracted_items = []
        # Pattern matches: Start of line, number, separator, possible bold, BrandName, possible bold, separator or end
        # Group 1: Rank, Group 2: Name
        pattern = r"^\s*(\d+)[\.\)]\s*\**([A-Za-z0-9 .&+]+?)\**(?::|-|\n|$)"
        
        lines = text.split('\n')
        for line in lines:
            match = re.match(pattern, line)
            if match:
                try:
                    rank = int(match.group(1))
                    name = match.group(2).strip()
                    # Basic cleanup - remove common trailing words if regex grabbed too much
                    if " - " in name: name = name.split(" - ")[0]
                    
                    if len(name) > 1 and rank < 20: # Sanity check
                        extracted_items.append({
                            "rank": rank,
                            "name": name,
                            "rank": rank,
                            "name": name,
                            # [FIX] Capture the original line as description for authentic context
                            "description": line.split(name)[-1].strip(": -"), 
                            "sentiment": "Neutral" # Default
                        })
                except:
                    pass
                    
        if extracted_items:
             return {"ranking": extracted_items, "sources": []}
        return None

    # --- TASK QUEUE GENERATION ---
    tasks = []
    
    for model_name, query_func in models.items():
        # Check for API Key
        user_key = api_keys.get(key_map[model_name])
        
        # Fallback: Check env var if user key is empty/None
        if not user_key:
            env_key_name = f"{key_map[model_name].upper()}_API_KEY"
            user_key = os.getenv(env_key_name)
            
        # If still no key, skip
        if not user_key:
            results[model_name] = {"status": "skipped", "reason": "No API Key"}
            continue
            
        # Prepare Tasks
        results[model_name] = {"status": "active", "data": []}
        
        for keyword in keywords:
            for intent in active_intents:
                for run_idx in range(runs):
                    tasks.append((model_name, query_func, keyword, intent, run_idx, user_key))
                    
    # --- PARALLEL EXECUTION ---
    # Safe Max Workers = 2 (Free Tier Friendly)
    MAX_WORKERS = 2
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks
        future_to_task = {executor.submit(execute_query, task): task for task in tasks}
        
        for future in concurrent.futures.as_completed(future_to_task):
            task_data = future_to_task[future]
            model_name = task_data[0] # Tuple: (model, func, kw, intent, run, key)
            
            try:
                result = future.result()
                # Append to the correct model bucket
                if result:
                    results[model_name]["data"].append(result)
            except Exception as exc:
                print(f"Task generated an exception: {exc}")
                
    return results


def analyze_competitors(aeo_results, user_brand_name="", previous_leaderboard=None):
    """
    Aggregates AEO results to find the top competitors, citations, and 'Source Gaps'.
    Also calculates Stability Scores and Per-Intent Visibility (Matrix).
    """
    leaderboard = {} 
    citations = {} # Global citation count
    
    # Source Gap Logic
    market_leader_citations = {} # domain -> count
    user_citations = {} # domain -> count
    
    # Stability Logic
    stability_map = {}
    
    total_queries = 0
    # Track totals per intent
    intent_totals = {"Informational": 0, "Commercial": 0, "Transactional": 0, "General": 0, "Risk": 0}
    
    for model, res in aeo_results.items():
        if res.get("status") != "active":
            continue
            
        for item in res.get("data", []):
            if item.get("status") != "success":
                continue
                
            total_queries += 1
            current_intent = item.get("intent", "General")
            
            # Map specific Risk intents to broad "Risk" bucket
            tracking_intent = current_intent
            if current_intent.startswith("Risk:"):
                tracking_intent = "Risk"
            
            if tracking_intent in intent_totals:
                intent_totals[tracking_intent] += 1
            else:
                intent_totals["General"] += 1 # Fallback
            
            analysis = item.get("analysis", {})
            kw_key = f"{item['keyword']}_{item['intent']}"
            
            # 1. Stability Tracking
            if kw_key not in stability_map:
                stability_map[kw_key] = {"total_runs": 0, "user_mentions": 0}
            stability_map[kw_key]["total_runs"] += 1
            if analysis.get("mentioned", False):
                stability_map[kw_key]["user_mentions"] += 1
            
            # 2. Extract Citations for this query (Smart Filtering)
            query_citations = []
            from urllib.parse import urlparse
            
            def get_root_domain(url):
                try:
                    # Remove protocol
                    clean_url = url.replace("https://", "").replace("http://", "")
                    # Split by / to get domain part
                    domain_part = clean_url.split('/')[0]
                    # Remove port if exists
                    domain_part = domain_part.split(':')[0]
                    
                    parts = domain_part.split('.')
                    if len(parts) > 2:
                        # Heuristic: Take last 2 parts (e.g. twilio.com from blog.twilio.com)
                        # Exception for co.uk etc. (simple heuristic for now: if last part is 2 chars, take 3)
                        if len(parts[-1]) == 2 and len(parts[-2]) <= 3: 
                            return ".".join(parts[-3:])
                        return ".".join(parts[-2:])
                    return domain_part
                except:
                    return url

            for cit in analysis.get("citations_found", []):
                try:
                    root_dom = get_root_domain(cit)
                    # Use existing urlparse for safety fallback
                    if not root_dom: 
                        root_dom = urlparse(cit).netloc.replace("www.", "")
                        
                    if root_dom:
                        query_citations.append(root_dom)
                        citations[root_dom] = citations.get(root_dom, 0) + 1
                except:
                    pass
            
            # 3. User Citations (If user is present)
            if analysis.get("mentioned", False):
                for dom in query_citations:
                    user_citations[dom] = user_citations.get(dom, 0) + 1

            # 4. Competitor/Leaderboard Aggregation
            winner_name = None # Rank #1
            
            seen_in_this_query = set()
            
            # [FIX] Include User Brand in the Leaderboard Loop if they are ranked
            items_to_process = analysis.get("competitors_found", []).copy()
            
            if analysis.get("mentioned", False):
                # Construct user brand entry for leaderboard processing
                # Use the canonical 'user_brand_name' to ensure it merges correctly in the leaderboard dict
                user_entry = {
                    "name": user_brand_name if user_brand_name else "My Brand", # Fallback
                    "rank": analysis.get("rank"),
                    "sentiment": analysis.get("sentiment", "Neutral")
                }
                items_to_process.append(user_entry)
            
            # [FIX] Competitor Name Normalization (Fuzzy Match / Canonical Mapping)
            canonical_map = {} # transient map for this analysis could be persisted
            # Since we don't have a persisted database of canonicals, we build one on the fly for this result set
            # But the loop below processes items one by one. 
            # Better strategy: We don't have the full list yet. 
            # We will use a "Known Competitors" set built up during iteration to merge.
            
            # This is complex inside a loop. 
            # Alternative: Just normalize strictly by lowercase for now + basic fuzzy check against EXISTING leaderboard keys.
            
            for comp in items_to_process:
                raw_name = comp["name"]
                
                # Normalization Logic
                norm_name = raw_name # Default
                
                # 1. Check against existing leaderboard keys for fuzzy match
                existing_names = list(leaderboard.keys())
                # Use strict cutoff (0.85) to avoid false positives (e.g. "Twilio" vs "Twilio Segment" might be different)
                matches = difflib.get_close_matches(raw_name, existing_names, n=1, cutoff=0.85)
                
                if matches:
                    norm_name = matches[0] # Merge to existing
                else:
                    # 2. Substring check (e.g. "Vonage Inc." -> "Vonage" if "Vonage" exists)
                    for exist in existing_names:
                        if len(exist) > 3 and (exist in raw_name or raw_name in exist):
                             # Use the shorter one as canonical? Or the longer?
                             # Usually shorter is better (Brand Name vs Legal Name)
                             if len(exist) < len(raw_name):
                                 norm_name = exist
                             else:
                                 # If we are renaming the EXISTING key, that is hard.
                                 # So we stick to: match to the ALREADY SEEN one.
                                 norm_name = exist
                             break
                
                name = norm_name
                rank = comp["rank"]
                
                # Identify Winner (Rank 1)
                is_winner = False
                if rank == 1 or rank == "1":
                    is_winner = True
                    winner_name = name
                elif isinstance(rank, str) and rank.isdigit() and int(rank) == 1:
                    is_winner = True
                    winner_name = name
                
                if name not in leaderboard:
                    leaderboard[name] = {
                        "mentions": 0, 
                        "unique_queries": 0, 
                        "weighted_score": 0,
                        "total_shelf_share": 0,
                        "rank_sum": 0,
                        "citation_sources": {}, # domain -> count
                        "competitor_sources": 0, # Count of sources that are KNOWN competitors
                        "total_sources_count": 0, # Total valid sources found for this brand
                        # Intent Breakdown
                        "intent_mentions": {"Informational": 0, "Commercial": 0, "Transactional": 0, "General": 0, "Risk": 0}
                    }
                    
                leaderboard[name]["mentions"] += 1
                
                if name not in seen_in_this_query:
                    leaderboard[name]["unique_queries"] += 1
                    # Increment Intent Mention (only once per query per brand)
                    
                    # [FIX] Risk Logic Refinement
                    # If this is a RISK intent, only count it if it's actually a risk.
                    # For the User Brand, we have the 'sentiment' from analysis.
                    # For competitors, we assume worst-case (if they are in a risk list, they are risk) unless we have deep analysis for them too.
                    should_count_intent = True
                    
                    if tracking_intent == "Risk":
                        # Check if this is the User Brand
                        if user_brand_name and user_brand_name.lower() in name.lower():
                            # Check sentiment
                            sent = analysis.get("sentiment", "N/A").lower()
                            if "safe" in sent or "positive" in sent or "neutral" in sent:
                                should_count_intent = False
                    
                    if tracking_intent in leaderboard[name]["intent_mentions"]:
                        if should_count_intent:
                            leaderboard[name]["intent_mentions"][tracking_intent] += 1
                    else:
                        leaderboard[name]["intent_mentions"]["General"] += 1
                        
                    seen_in_this_query.add(name)
                
                # Attribute sources to this competitor (Association)
                for dom in query_citations:
                    # SMART CITATION FILTERING
                    # 1. Start with valid domain
                    if not dom: continue
                    
                    # 2. Exclude User Brand Self-Citation ONLY
                    # Allow User Brand to appear as a source for competitors (e.g. Vonage cited by Twilio)
                    # But exclude if the current entity IS the User Brand (e.g. Twilio cited by Twilio)
                    if user_brand_name.lower() in dom.lower() and user_brand_name.lower() in name.lower():
                        continue
                        
                    # 3. Exclude Self-Citation (e.g. Salesforce citing salesforce.com)
                    if name.lower() in dom.lower():
                        continue
                        
                    leaderboard[name]["citation_sources"][dom] = leaderboard[name]["citation_sources"].get(dom, 0) + 1
                
                # Weighting
                weight = 1.0
                if isinstance(rank, int):
                    weight = 1.0 / rank
                elif isinstance(rank, str) and rank.isdigit():
                    weight = 1.0 / int(rank)
                elif rank != "Unranked": # Listed
                    weight = 0.5 
                    
                leaderboard[name]["weighted_score"] += weight
                
                list_count = analysis.get("total_list_items", 0)
                if list_count > 0:
                    comp_sov = (1 / list_count) * 100
                else:
                    comp_sov = 0
                leaderboard[name]["total_shelf_share"] += comp_sov
                
                r_val = 10
                if isinstance(rank, int): r_val = rank
                elif isinstance(rank, str) and rank.isdigit(): r_val = int(rank)
                leaderboard[name]["rank_sum"] += r_val
            
            # End of Competitor Loop
            
            # 5. Market Leader Citation Attribution
            # If there was a clear winner (Rank #1) and it wasn't the user:
            if winner_name and winner_name.lower() != user_brand_name.lower():
                 # Create a set of all competitor names for filtering
                 all_competitors = set(x.lower() for x in leaderboard.keys())
                 all_competitors.add(user_brand_name.lower())
                 
                 for dom in query_citations:
                     dom_lower = dom.lower()
                     # Filter: Exclude if domain matches ANY competitor name (including User and Winner)
                     # matching logic: simple substring check
                     is_competitor_domain = False
                     for comp_name in all_competitors:
                         if comp_name in dom_lower:
                             is_competitor_domain = True
                             break
                     
                     if is_competitor_domain:
                         continue
                     
                     market_leader_citations[dom] = market_leader_citations.get(dom, 0) + 1

    # --- Post Processing ---

    # 1. Stability Score
    total_stability = 0
    keyword_count = len(stability_map)
    for k, v in stability_map.items():
        if v["total_runs"] > 0:
            score = (v["user_mentions"] / v["total_runs"]) * 100
            total_stability += score
    
    avg_stability_score = round(total_stability / keyword_count, 1) if keyword_count > 0 else 0

    avg_stability_score = round(total_stability / keyword_count, 1) if keyword_count > 0 else 0

    # 2. Source Intelligence (Renamed: Opportunity vs Strength)
    # Opportunity URLs: Top sources for Leaders where User is missing
    opportunity_urls = []
    # Strength URLs: Where User is already cited
    strength_urls = []
    for dom, count in market_leader_citations.items():
        if dom not in user_citations:
            opportunity_urls.append({"domain": dom, "leader_count": count, "user_count": 0})
        elif user_citations[dom] < count:
             # Weakness
             opportunity_urls.append({"domain": dom, "leader_count": count, "user_count": user_citations[dom]})
    
    opportunity_urls.sort(key=lambda x: x["leader_count"], reverse=True)
    
    for dom, count in user_citations.items():
        strength_urls.append({"domain": dom, "count": count})
    strength_urls.sort(key=lambda x: x["count"], reverse=True)

    # 3. Leaderboard Finalization
    final_leaderboard = []
    for name, stats in leaderboard.items():
        score = round((stats["weighted_score"] / total_queries) * 100, 1) 
        visibility = round((stats["unique_queries"] / total_queries) * 100, 1)
        
        # Calculate Intent Win %
        # Avoid division by zero
        info_score = round((stats["intent_mentions"]["Informational"] / intent_totals["Informational"]) * 100, 1) if intent_totals["Informational"] > 0 else 0
        comm_score = round((stats["intent_mentions"]["Commercial"] / intent_totals["Commercial"]) * 100, 1) if intent_totals["Commercial"] > 0 else 0
        trans_score = round((stats["intent_mentions"]["Transactional"] / intent_totals["Transactional"]) * 100, 1) if intent_totals["Transactional"] > 0 else 0
        general_score = round((stats["intent_mentions"]["General"] / intent_totals["General"]) * 100, 1) if intent_totals["General"] > 0 else 0
        risk_score = round((stats["intent_mentions"]["Risk"] / intent_totals["Risk"]) * 100, 1) if intent_totals["Risk"] > 0 else 0
        
        avg_shelf = 0
        if stats["mentions"] > 0:
            avg_shelf = round(stats["total_shelf_share"] / stats["mentions"], 1)
            
        avg_rank = 0
        if stats["mentions"] > 0:
            avg_rank = round(stats["rank_sum"] / stats["mentions"], 1)
            
        # Determine Dominant Source
        dom_source = "N/A"
        if stats["citation_sources"]:
            # Sort by count
            sorted_srcs = sorted(stats["citation_sources"].items(), key=lambda x: x[1], reverse=True)
            dom_source = sorted_srcs[0][0] # Top domain
        
        final_leaderboard.append({
            "name": name,
            "mentions": stats["mentions"],
            "share_of_voice": visibility,
            "avg_shelf_share": avg_shelf,
            "avg_rank": avg_rank,
            "impact_score": score,
            "dominant_source": dom_source,
            # New Matrix Data
            "info_score": info_score,
            "comm_score": comm_score,
            "trans_score": trans_score,
            "general_score": general_score,
            "risk_score": risk_score,
            "competitor_reliance_score": 0 # Placeholder, calculated below
        })
        
    # --- COMPETITOR RELIANCE CALCULATION (Post-Aggregation) ---
    # We do this here because we need the FULL list of competitors to know who is a competitor
    all_known_competitors = set(x["name"].lower() for x in final_leaderboard)
    all_known_competitors.add(user_brand_name.lower()) # User is also a competitor
    
    for entry in final_leaderboard:
        name = entry["name"]
        stats = leaderboard.get(name)
        if not stats: continue
        
        comp_source_count = 0
        total_src_count = 0
        
        for src_dom, count in stats["citation_sources"].items():
            total_src_count += count
            # Check if source domain matches ANY known competitor
            for comp_name in all_known_competitors:
                if comp_name in src_dom.lower():
                    comp_source_count += count
                    break
        
        reliance_score = 0
        if total_src_count > 0:
            reliance_score = round((comp_source_count / total_src_count) * 100, 1)
            
        entry["competitor_reliance_score"] = reliance_score
        
    final_leaderboard.sort(key=lambda x: x["impact_score"], reverse=True)
    
    # 4. Rank Change Calculation
    if previous_leaderboard:
        # Create map of name -> rank (index + 1)
        prev_map = {entry['name']: idx + 1 for idx, entry in enumerate(previous_leaderboard)}
        
        for idx, entry in enumerate(final_leaderboard):
            curr_rank = idx + 1
            prev_rank = prev_map.get(entry['name'])
            
            if prev_rank:
                # Rank Change: Higher rank (lower number) is better
                # e.g. Prev=5, Curr=2 -> Change = +3 (Improved)
                # e.g. Prev=1, Curr=4 -> Change = -3 (Declined)
                change = prev_rank - curr_rank
                entry['rank_change'] = change
            else:
                entry['rank_change'] = "New" # New entrant
    else:
        # Initialize
        for entry in final_leaderboard:
            entry['rank_change'] = 0
    
    final_citations = [{"domain": k, "count": v} for k, v in citations.items()]
    final_citations.sort(key=lambda x: x["count"], reverse=True)
    
    return {
        "leaderboard": final_leaderboard[:15],
        "strength_urls": strength_urls[:15], # Renamed from citations
        "total_queries": total_queries,
        "stability_score": avg_stability_score,
        "opportunity_urls": opportunity_urls[:5] # Renamed from source_gaps
    }

def evaluate_page_index(brand_name, page_url, page_type, content_snippet="", api_key=None, model_name=None):
    """
    Evaluates a specific webpage's performance in AI responses.
    
    Args:
        brand_name: Name of the brand.
        page_url: The specific URL to test.
        page_type: Type of page (e.g., 'Pricing', 'About', 'Blog').
        content_snippet: Optional snippet of page content to check for relevance.
        
    Returns:
        Dict with score (0-100), citation_status, relevance, sentiment.
    """
    # 1. Determine Native Query
    query = ""
    target_intent = "General"
    
    if page_type.lower() == "pricing":
        query = f"How much does {brand_name} cost? What are the pricing plans?"
        target_intent = "Transactional"
    elif page_type.lower() == "about" or page_type.lower() == "company":
        query = f"What is {brand_name}? Tell me about the company history and mission."
        target_intent = "Informational"
    elif page_type.lower() == "contact" or page_type.lower() == "support":
        query = f"How do I contact {brand_name} support?"
        target_intent = "Transactional"
    elif page_type.lower() == "blog" or page_type.lower() == "resource":
        query = f"What are some key resources or articles from {brand_name}?"
        target_intent = "Informational"
    else:
        # Default / Homepage
        query = f"What does {brand_name} do? Give me a summary."
        
    # 2. Run Query
    # Use existing query_gemini from this module
    response_text, error = query_gemini(query, api_key=api_key, model_name=model_name)
    
    if error:
        return {
            "status": "error",
            "error": error,
            "score": 0
        }
        
    # 3. Analyze Response (Scoring)
    
    # A. Citation Score (40 pts)
    # 0 = No citation
    # 20 = Domain match (e.g. brand.com)
    # 40 = Exact URL match (or close enough)
    
    citation_score = 0
    citation_status = "None"
    
    # Normalize
    clean_url = page_url.lower().replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/")
    clean_domain = clean_url.split("/")[0]
    
    # Extract citations from response
    found_citations = []
    import re
    # Simple URL extraction
    url_pattern = re.compile(r'https?://[a-zA-Z0-9.-]+(?:/[a-zA-Z0-9._~:/?#\[\]@!$&\'()*+,;=%-]*)?')
    raw_found = url_pattern.findall(response_text)
    
    # Markdown links
    md_links = re.findall(r'\[.*?\]\((https?://.*?)\)', response_text)
    raw_found.extend(md_links)
    
    for link in raw_found:
        link_clean = link.lower().replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/")
        
        # Exactish match
        if clean_url in link_clean or link_clean in clean_url:
            citation_status = "Exact URL"
            citation_score = 40
            break # Max score achieved
            
        # Domain match
        if clean_domain in link_clean and citation_score < 20:
             citation_status = "Domain Only"
             citation_score = 20
             
    # B. Relevance/Accuracy Score (40 pts)
    # Heuristic: Does the AI mention key terms likely on that page?
    # Better: If we have content_snippet, check if AI response reflects it.
    
    relevance_score = 0
    text_lower = response_text.lower()
    
    # Base relevance: Mentions brand?
    if brand_name.lower() in text_lower:
        relevance_score += 10
        
    # Context relevance
    if page_type.lower() == "pricing":
        if any(x in text_lower for x in ["free", "plan", "$", "subscription", "enterprise", "pricing", "cost"]):
            relevance_score += 30
    elif page_type.lower() == "about":
         if any(x in text_lower for x in ["founded", "mission", "ceo", "company", "based in", "history"]):
            relevance_score += 30
    else:
        # Generic check
        if len(response_text) > 100: # Decent length answer
            relevance_score += 30
            
    # Cap
    relevance_score = min(relevance_score, 40)
    
    # C. Sentiment Score (20 pts)
    sentiment_score = 0
    negatives = ["avoid", "bad", "poor", "error", "issue", "scam", "expensive"]
    positives = ["good", "great", "excellent", "best", "reliable", "leader"]
    
    is_negative = any(x in text_lower for x in negatives)
    is_positive = any(x in text_lower for x in positives)
    
    if is_negative:
        sentiment_score = 0
    elif is_positive:
        sentiment_score = 20
    else:
        sentiment_score = 10 # Neutral
        
    final_score = citation_score + relevance_score + sentiment_score
    
    return {
        "status": "success",
        "url": page_url,
        "page_type": page_type,
        "query_used": query,
        "prompt_used": query,
        "response_snippet": response_text[:200] + "...",
        "scores": {
            "total": final_score,
            "citation": citation_score,
            "relevance": relevance_score,
            "sentiment": sentiment_score
        },
        "citation_status": citation_status,
        "found_citations": [l.lower() for l in raw_found] # Return all raw citations found
    }

def run_branded_simulation(brand_name, keywords, competitors=[], api_key=None, model_name=None, region="United States (US)", context="General Audience"):
    """
    Runs a defensive analysis on BRANDED queries to check for competitor leakage and narrative alignment.
    
    Args:
        brand_name: Name of the brand (e.g. 'Twilio')
        keywords: Core keywords (e.g. ['SMS API'])
        competitors: Known competitors to check for (e.g. ['Plivo', 'Vonage'])
        region: Geographic location for simulation.
        context: Target audience persona.
    
    Returns:
        Dict with moat_score, leakage_stats, and detailed results.
    """
    # 1. Generate Branded Intents
    queries = []
    
    for kw in keywords:
        # A. Direct Intent ("Twilio SMS API")
        queries.append({
            "type": "Direct",
            "query": f"{brand_name} {kw}",
            "keyword": kw
        })
        
        # B. Comparative Intent ("Twilio vs Plivo SMS API")
        # If no competitors provided, use generic "competitors" string
        if competitors:
            top_comp = competitors[0] # Use top competitor for the main check
            queries.append({
                "type": "Comparative",
                "query": f"{brand_name} vs {top_comp} {kw}",
                "keyword": kw
            })
        else:
             queries.append({
                "type": "Comparative",
                "query": f"{brand_name} vs competitors {kw}",
                "keyword": kw
            })
            
        # C. Review/Risk Intent ("Twilio SMS API Reviews")
        queries.append({
            "type": "Reviews",
            "query": f"{brand_name} {kw} reviews pros and cons",
            "keyword": kw
        })
        
        # D. Pricing Intent ("Twilio SMS API Pricing")
        queries.append({
            "type": "Pricing",
            "query": f"{brand_name} {kw} pricing",
            "keyword": kw
        })

    # 2. Run Queries
    results = []
    total_queries = 0
    clean_responses = 0 # No competitors mention
    leakage_counts = {} # Comp -> Count
    
    import time
    
    for q in queries:
        time.sleep(1) # Rate limit safety
        
        # Custom Prompts based on Intent Type (Simulating Real User Personas)
        # INJECT CONTEXT
        persona_context = f"Context: You are searching from {region}. You are a {context} looking for accurate information."
        
        prompt = ""
        
        if q['type'] == 'Reviews':
            prompt = f"""
            {persona_context}
            You are a critical software reviewer. A user asks: "{q['query']}"
            
            Task:
            1. Summarize the honest user consensus (G2, Capterra, Reddit vibe).
            2. highlighting specific PROS and CONS. 
            3. Be objective but don't hold back on common complaints.
            
            Final Step: End your response with a new line starting with "NARRATIVE:" that summarizes the core competitive sentiment/comparison in 1 concise sentence.
            """
        elif q['type'] == 'Pricing':
             prompt = f"""
            {persona_context}
            You are a cost efficiency analyst. A user asks: "{q['query']}"
            
            Task:
            1. Explain the pricing model clearly.
            2. specific costs if known.
            3. Are there hidden fees? Is it considered expensive or cheap vs market?
            
            Final Step: End your response with a new line starting with "NARRATIVE:" that summarizes the core competitive sentiment/comparison in 1 concise sentence.
            """
        elif q['type'] == 'Comparative':
             prompt = f"""
            {persona_context}
            You are a procurement consultant. A client asks: "{q['query']}"
            
            Task:
            1. Compare these options head-to-head.
            2. Declare a winner for specific use cases (e.g. "X is better for Enterprise, Y for Startups").
            3. Be decisive.
            
            Final Step: End your response with a new line starting with "NARRATIVE:" that summarizes the core competitive sentiment/comparison in 1 concise sentence.
            """
        else: # Direct
             prompt = f"""
            {persona_context}
            You are an expert tech consultant. A CTO asks you: "{q['query']}"
            
            Task:
            1. Explain clearly what this brand does and its key value proposition.
            2. Why does it matter?
            3. Is it an industry standard?
            
            Final Step: End your response with a new line starting with "NARRATIVE:" that summarizes the core competitive sentiment/comparison in 1 concise sentence.
            """
        
        response_text, error = query_gemini(prompt, api_key=api_key, model_name=model_name)
        
        if error:
            # [FIX] Record error instead of skipping to show user what happened
            results.append({
                "query": q['query'],
                "type": q['type'],
                "prompt_used": prompt,
                "response_snippet": f"⚠️ SIMULATION FAILED: {error}",
                "narrative_summary": "Error",
                "leaked_to": [],
                "sentiment": "N/A",
                "descriptors": [],
                "is_moat_breach": False
            })
            continue
            
        total_queries += 1
        
        # --- NARRATIVE EXTRACTION (Single-Pass) ---
        narrative_summary = "No summary available."
        clean_response_text = response_text
        
        if "NARRATIVE:" in response_text:
            parts = response_text.split("NARRATIVE:")
            clean_response_text = parts[0].strip() # The main answer
            narrative_summary = parts[1].strip() # The summary
        
        response_lower = clean_response_text.lower()
        
        # 3. Analyze Leakage (Defensive Moat)
        # Check if ANY competitor is mentioned
        leaked = False
        leaked_to = []
        
        # If specific competitors provided, check them
        if competitors:
            for comp in competitors:
                if comp.lower() in response_lower and comp.lower() != brand_name.lower():
                    leaked = True
                    leaked_to.append(comp)
                    leakage_counts[comp] = leakage_counts.get(comp, 0) + 1
        else:
            # Generic heuristic for "alternatives" or "competitors" usually followed by names
            pass 
            
        # Exception: Comparative queries SHOULD have competitors. 
        # Moat Score applies mainly to Direct, Pricing, and Reviews.
        # If I search "Twilio vs Plivo", Plivo MUST be there.
        # But if I search "Twilio Pricing", Plivo SHOULD NOT be there.
        
        is_safe_query = True
        if q['type'] == "Comparative":
             # We don't penalize presence of competitor in a Vs query, 
             # BUT we check if the sentiment favors the user.
             # For Moat Score calculation, we might exclude this or treat differently.
             # Let's exclude Comparative from the "Clean Response" count for Moat Score
             pass
        else:
            if not leaked:
                clean_responses += 1
                is_safe_query = True
            else:
                is_safe_query = False
                
        # 4. Sentiment / Narrative Check
        sentiment = "Neutral"
        if any(x in response_lower for x in ["best", "excellent", "industry standard", "leader", "highly recommend"]):
            sentiment = "Positive"
        elif any(x in response_lower for x in ["expensive", "complex", "slow", "hard", "limited", "poor"]):
             sentiment = "Negative"
             
        # Narrative extraction (Key adjectives)
        descriptors = []
        try:
           common_descriptors = [
               "expensive", "cheap", "scalable", "enterprise", "complex", "easy", "developer-friendly", 
               "reliable", "innovative", "legacy", "popular", "secure"
           ]
           descriptors = [d for d in common_descriptors if d in response_lower]
        except:
            pass
            
        # [NEW] Smart Snippet Logic
        snippet = clean_response_text[:200] + "..."
        
        # If leakage detected, ensure the context is visible
        if leaked_to:
            for lk in leaked_to:
                # Check if this leaker is already in the visible snippet
                if lk.lower() not in snippet.lower():
                    # Find where they are mentioned
                    try:
                        lk_idx = response_lower.find(lk.lower())
                        if lk_idx != -1:
                            # Extract context window (50 chars before, 100 after)
                            start_ctx = max(0, lk_idx - 50)
                            end_ctx = min(len(clean_response_text), lk_idx + 100)
                            
                            ctx_text = clean_response_text[start_ctx:end_ctx].replace("\n", " ").strip()
                            
                            # Append to snippet in a clean way
                            snippet += f"\n\n**Context ({lk}):** \"...{ctx_text}...\""
                    except:
                        pass # Fallback to default snippet

        results.append({
            "query": q['query'],
            "type": q['type'],
            "prompt_used": prompt,
            "response_snippet": snippet,
            "narrative_summary": narrative_summary, # NEW FIELD
            "leaked_to": leaked_to,
            "sentiment": sentiment,
            "descriptors": descriptors,
            "is_moat_breach": not is_safe_query if q['type'] != "Comparative" else False
        })

    # 5. Calculate Metrics
    # Moat Score: % of Non-Comparative queries that were clean
    non_comp_queries = [r for r in results if r['type'] != "Comparative"]
    safe_non_comp = [r for r in non_comp_queries if not r['is_moat_breach']]
    
    moat_score = 0
    if non_comp_queries:
        moat_score = (len(safe_non_comp) / len(non_comp_queries)) * 100
        
    return {
        "moat_score": round(moat_score, 1),
        "leakage_counts": leakage_counts,
        "results": results,
        "narrative_descriptors": [d for r in results for d in r['descriptors']]
    }

def generate_defense_strategy(brand_name, defense_results, api_key=None, model_name=None):
    """
    Generates a strategic defense playbook based on AEO simulation results.
    """
    moat_score = defense_results.get("moat_score", 0)
    leakage = defense_results.get("leakage_counts", {})
    top_leakers = sorted(leakage.items(), key=lambda x: x[1], reverse=True)[:3]
    leaker_str = ", ".join([f"{k} ({v})" for k,v in top_leakers]) if top_leakers else "None"
    
    narrative = list(set(defense_results.get("narrative_descriptors", [])))
    narrative_str = ", ".join(narrative[:5]) if narrative else "Neutral/Generic"
    
    prompt = f"""
    Act as a Crisis Brand Reputation Manager. Analyze these 'Brand Defense' metrics for the brand '{brand_name}' on AI Search engines.
    
    METRICS:
    - Defensive Moat Score: {moat_score}/100 (100 is perfect, 0 is full leakage).
    - Competitor Leakage: {leaker_str} (These competitors appear when users search for OUR brand).
    - Current Narrative Association: {narrative_str}
    
    TASK:
    Generate a JSON response with a specific strategic plan to fix these issues.
    
    JSON FORMAT:
    {{
        "headline_strategy": "The Punchy Title of the Strategy",
        "executive_summary": "1-2 sentences explaining the core problem and fix.",
        "tactics": [
            {{
                "title": "Tactic Name",
                "description": "Specific action to take (e.g. create a specific comparison page, change schema, etc).",
                "impact": "High/Medium/Low"
            }}
        ]
    }}
    
    If Moat Score is < 80, focus HEAVILY on creating specific 'Brand vs Competitor' comparison assets to reclaim the narrative.
    If Narrative is negative, focus on reviews and trust signals.
    """
    
    try:
        response_text, error = query_gemini(prompt, api_key=api_key, model_name=model_name)
        if error: return "{}"
        return response_text
    except:
        return "{}"
