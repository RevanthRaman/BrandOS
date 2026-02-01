from google import genai

from google.genai import types

from google.api_core.exceptions import ResourceExhausted, NotFound, ServiceUnavailable

import os

import json

import re

import math

import time

import random



def calculate_readability(text):

    """

    Calculates the Flesch-Kincaid Grade Level.

    """

    if not text or not isinstance(text, str):

        return 0

    

    sentences = max(1, text.count('.') + text.count('!') + text.count('?'))

    words = max(1, len(text.split()))

    syllables = 0

    

    for word in text.split():

        word = word.lower()

        count = 0

        vowels = "aeiouy"

        if word[0] in vowels:

            count += 1

        for index in range(1, len(word)):

            if word[index] in vowels and word[index - 1] not in vowels:

                count += 1

        if word.endswith("e"):

            count -= 1

        if count == 0:

            count += 1

        syllables += count

        

    # Flesch-Kincaid Grade Level formula

    score = 0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59

    return round(max(0, score), 1)



def extract_first_json_object(text):
    """
    Finds the first JSON object or list in the text using a stack-based approach.
    This handles cases where the JSON is followed by commentary or valid-looking braces.
    """
    text = text.strip()
    stack = []
    start_index = -1
    
    # Check for object or list
    first_brace = text.find('{')
    first_bracket = text.find('[')
    
    # Determine which starts first
    if first_brace != -1 and (first_bracket == -1 or first_brace < first_bracket):
        start_char = '{'
        end_char = '}'
        start_index = first_brace
    elif first_bracket != -1:
        start_char = '['
        end_char = ']'
        start_index = first_bracket
    else:
        return None
        
    # Iterate from start_index
    for i, char in enumerate(text[start_index:], start=start_index):
        if char == start_char:
            stack.append(char)
        elif char == end_char:
            if stack:
                stack.pop()
                if not stack:
                    return text[start_index:i+1]
    
    return None

def parse_json_response(response_text):
    """
    Robustly parses JSON from AI response, handling markdown blocks, common issues, and even malformed JSON.
    """
    if not response_text or not isinstance(response_text, str):
        return None

    # Helper: Recursive JSON Repair
    def try_repair_json(json_str):
        try:
            # 1. Remove comments (C-style)
            json_str = re.sub(r'//.*', '', json_str)
            json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
            
            # 2. Fix trailing commas
            json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
            
            return json.loads(json_str)
        except Exception:
            return None

    try:
        # 0. Strip "Safety Wrappers" if present (e.g. START_JSON ... END_JSON)
        wrapper_match = re.search(r'START_JSON(.*?)END_JSON', response_text, re.DOTALL)
        if wrapper_match:
            response_text = wrapper_match.group(1)

        # 1. Try robust stack-based extraction first (Most reliable for messy LLM output)
        extracted_content = extract_first_json_object(response_text)
        if extracted_content:
            try:
                return json.loads(extracted_content)
            except:
                # Try repair on extracted content
                repaired = try_repair_json(extracted_content)
                if repaired: return repaired
                pass 

        # 2. Try direct parsing
        return json.loads(response_text)

    except json.JSONDecodeError:
        try:
            # 3. Try extracting from markdown code blocks (Classic method)
            json_match = re.search(r'```json\n(.*?)\n```', response_text, re.DOTALL)
            if json_match:
                content = json_match.group(1)
                try: return json.loads(content)
                except: 
                    repaired = try_repair_json(content)
                    if repaired: return repaired

            # 4. Try finding the first { and last } (Greedy fallback)
            json_match = re.search(r'(\{.*\})', response_text, re.DOTALL)
            if json_match:
                content = json_match.group(1)
                try: return json.loads(content)
                except:
                     repaired = try_repair_json(content)
                     if repaired: return repaired
                
            # 5. Try finding the first [ and last ] (for lists)
            json_match = re.search(r'(\[.*\])', response_text, re.DOTALL)
            if json_match:
                 content = json_match.group(1)
                 try: return json.loads(content)
                 except: return try_repair_json(content)

            # 6. Fallback: Try ast.literal_eval for Python dict strings (single quotes)
            import ast
            try:
                return ast.literal_eval(response_text)
            except:
                pass
            
            # 7. Last Resort: Log failure for debugging
            print(f"CRITICAL: JSON PARSING FAILED.\nRaw Content Start: {response_text[:200]}\n...\nRaw Content End: {response_text[-200:]}")
            raise ValueError("No valid JSON found in response")

        except Exception as e:
            print(f"JSON Parse Error: {e}")
            return None



def clean_html_response(response_text):
    """
    Cleans the AI response to return only the HTML code, removing markdown blocks.
    """
    if not response_text:
        return ""
    
    # Remove markdown code blocks
    clean_text = re.sub(r'```html\s*', '', response_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'```\s*', '', clean_text)
    
    return clean_text.strip()


def configure_genai():
    """
    Deprecated: Configuration is now handled via Client instantiation.
    """
    pass


# Models (Priority Chain as requested)
MODEL_PRIORITY_CHAIN = [
    'gemini-3-pro-preview', 
    'gemini-3-flash-preview', 
    'gemini-2.5-pro', 
    'gemini-2.5-flash', 
    'gemini-1.5-pro', 
    'gemini-1.5-flash'
]

# Backward compatibility aliases (Pointing to the best available in chain)
GEMINI_3_PRO = MODEL_PRIORITY_CHAIN[0]
GEMINI_3_FLASH = MODEL_PRIORITY_CHAIN[1]
# These were removed but are needed for default args in existing functions
GEMINI_3_PRO_PREVIEW = GEMINI_3_PRO
GEMINI_3_FLASH_PREVIEW = GEMINI_3_FLASH
GEMINI_2_5_PRO = MODEL_PRIORITY_CHAIN[2]
GEMINI_2_5_FLASH = MODEL_PRIORITY_CHAIN[3]
GEMINI_1_5_PRO = MODEL_PRIORITY_CHAIN[4]
GEMINI_1_5_FLASH = MODEL_PRIORITY_CHAIN[5]


def generate_gemini_response(prompt, model_name=None, temperature=0.7):
    """
    Generates content using Gemini models with cascading fallback and exponential backoff.
    Iterates through MODEL_PRIORITY_CHAIN.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return json.dumps({"error": "GEMINI_API_KEY not found.", "status": "failure"})

    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        return json.dumps({"error": f"Failed to initialize Client: {e}", "status": "failure"})

    config = types.GenerateContentConfig(
        temperature=temperature
    )

    # Prioritize the requested model, then fall back to the chain
    execution_chain = []
    if model_name:
        execution_chain.append(model_name)
    
    # Add the rest of the chain, avoiding duplicates
    for m in MODEL_PRIORITY_CHAIN:
        if m not in execution_chain:
            execution_chain.append(m)
    
    last_error = None
    
    for index, model_id in enumerate(execution_chain):
        try:
            # Direct instantiation/call
            response = client.models.generate_content(
                model=model_id,
                contents=prompt,
                config=config
            )
            
            # If successful, return text
            if response.text:
                return response.text
            else:
                # Empty response? Treat as failure?
                raise Exception("Empty response from model")

        except ResourceExhausted:
            # Rate Limit - Exponential Backoff
            wait_time = 2 ** index
            print(f"Rate limit hit for {model_id}. Sleeping {wait_time}s...")
            time.sleep(wait_time)
            last_error = f"ResourceExhausted on {model_id}"
            continue # Try next model
            
        except NotFound:
            # Model not found - Failover immediately
            print(f"Model {model_id} not found. Skipping...")
            last_error = f"NotFound: {model_id}"
            continue # Try next model
            
        except Exception as e:
            print(f"Error with {model_id}: {e}")
            last_error = str(e)
            continue
            
    # If all fail
    error_msg = json.dumps({"error": f"All models failed. Last error: {last_error}", "status": "failure"})
    print(error_msg) # Log it
    return error_msg
    


def analyze_brand_content(content, model_name=GEMINI_3_PRO_PREVIEW):
    """
    Legacy wrapper. Redirects to analyze_brand_complete if possible, 
    but for now just keeps the old signature for backward compatibility if needed.
    """
    try:
        prompt = f'''
        You are the **Head of Brand Strategy** at a Fortune 500 company.
        Analyze the following brand website content and provide a MASTERCLASS strategic analysis.
        
        Content:
        {content}
        
        Output JSON format:
        {{
            "brand_voice": "Describe the tone (e.g., Authoritative, Empathetic, Disruptive)",
            "brand_archetype": "e.g., The Sage, The Hero",
            "brand_mission": "The brand's TRUE north/mission",
            "brand_vision": "The aspirational future state",
            "brand_values": ["Value 1", "Value 2", "Value 3"],
            "brand_personality_traits": {{
                "Modern": 80,
                "Friendly": 60,
                "Professional": 90,
                "Innovative": 75,
                "Aggressive": 20
            }},
            "key_value_propositions": ["Value Prop 1", "Value Prop 2"],
            "primary_products": ["Product 1", "Product 2"],
            "target_audience_summary": "High-level definition of the ICP (Ideal Customer Profile)",
            "visual_style_inference": "Infer the aesthetic direction"
        }}
        '''
        return generate_gemini_response(prompt, model_name=model_name)
    except Exception as e:
        return f"Error analyzing content: {str(e)}"


def analyze_brand_complete(content, competitor_content=None, screenshot_bytes=None, model_name=GEMINI_3_PRO_PREVIEW, raw_html=None):
    """
    Optimized Two-Stage Analysis:
    1. Extraction Phase (Gemini 3 Flash): Fast extraction of factual brand data (DNA, Visuals, Products).
    2. Strategy Phase (Gemini 3 Pro): Deep reasoning for Strategy, SWOT, and Personas.
    
    This reduces latency and token usage vs the monolithic approach.
    """
    try:
        # --- Stage 1: Extraction (Fast) ---
        print("Starting Stage 1: Extraction (Gemini 3 Flash)...")
        # --- Stage 1: Extraction (Fast) ---
        print("Starting Stage 1: Extraction (Gemini 3 Flash)...")
        extraction_json_str = _analyze_brand_extraction(content, screenshot_bytes, raw_html)
        extraction_data = parse_json_response(extraction_json_str)
        
        if not extraction_data or "analysis" not in extraction_data:
            print("Warning: Extraction phase failed or returned empty. Proceeding with raw content only.")
            extraction_data = {"analysis": {}}

        # --- Stage 2: Strategy (Deep) ---
        print("Starting Stage 2: Strategy (Gemini 3 Pro)...")
        # We pass the extracted data as context to help the Pro model, plus the raw content
        strategy_json_str = _analyze_brand_strategy(content, extraction_data, competitor_content, model_name)
        strategy_data = parse_json_response(strategy_json_str)
        
        if not strategy_data:
             print("Warning: Strategy phase failed.")
             strategy_data = {}

        # --- Stage 3: Merge ---
        final_data = extraction_data.copy()
        
        # Merge Top-Level Keys
        final_data["personas"] = strategy_data.get("personas", [])
        final_data["strategy"] = strategy_data.get("strategy", {})
        final_data["competitor_analysis"] = strategy_data.get("competitor_analysis", {})
        
        # Merge specific nested fields (Strategic Recommendations belong in 'analysis')
        if "analysis" not in final_data: final_data["analysis"] = {}
        
        strat_recs = strategy_data.get("strategic_recommendations", [])
        if not strat_recs and "analysis" in strategy_data:
             # Fallback if strategy model put it inside analysis
             strat_recs = strategy_data["analysis"].get("strategic_recommendations", [])
             
        final_data["analysis"]["strategic_recommendations"] = strat_recs
        
        # Wrap in "analysis" wrapper if not present (compat) check
        # The prompt asks for { "analysis": ... }, but let's ensure structure
        
        return json.dumps(final_data)

    except Exception as e:
        return f"Error in combined analysis: {str(e)}"

def _analyze_brand_extraction(content, screenshot_bytes=None, raw_html=None):
    """
    Stage 1: Extracts Brand DNA, Visuals, and Products using Gemini 3 Flash (High Speed).
    """
    model_name = GEMINI_3_FLASH # Force Flash for speed
    
    html_section = ""
    if raw_html:
        # Take a robust chunk of HTML head/body to find styles
        html_section = f"**RAW HTML CONTEXT (FOR VISUAL EXTRACTION):**\n{raw_html[:30000]}\n\n"

    prompt_text = f'''
    You are a Brand Identity Expert & Frontend Developer.
    Analyze the following website content and extract the core Brand DNA and Visual Identity.
    
    **CONTENT:**
    {content[:80000]} 

    {html_section}
    
    **VISUAL INSTRUCTIONS (CRITICAL):**
    - **SCAN THE RAW HTML (if provided)** for CSS variables (e.g. --primary, --brand) or Hex Codes in `<style>` blocks.
    - **EXTRACT EXACT HEX CODES** from the code if found. Do not just guess "Blue", find `#0055ff`.
    - If you cannot find explicit hex codes, INFER them based on the described brand "vibe" or industry standards.
    - Do NOT return empty fields for visual_identity.
    
    **OUTPUT JSON:**
    {{
        "analysis": {{
            "brand_name": "Inferred Brand Name",
            
            "visual_identity": {{
                "primary_palette": ["#Hex1", "#Hex2", "#Hex3"],
                "visual_vibe": "Aesthetic description (e.g. 'Dark Mode SaaS', 'Playful & Vibrant').",
                "image_sentiment": "Emotional impact of imagery (e.g. 'Trusting', 'Energetic')."
            }},

            "brand_voice": "Describe the tone specifically (e.g. 'Authoritative yet Empathetic'). Avoid generic single words.",
            "brand_archetype": "The primary archetype (e.g. The Magician) followed by a short specific reason why (e.g. 'The Magician - Because they transform complex data into clear insights').",
            "brand_enemy": "The 'Villain' this brand fights (e.g. 'Complexity', 'Spreadsheets').",
            "brand_noble_cause": "The 'Why' (Mission).",
            "brand_values": ["Value 1", "Value 2", "Value 3"],
            
            "key_value_propositions": ["Prop 1", "Prop 2"],
            "primary_products": ["Product A", "Product B"],
            "target_audience_summary": "Who is this for? Be specific.",
            "visual_style_inference": "Detailed aesthetic inference."
        }}
    }}
    '''
    
    contents = prompt_text
    if screenshot_bytes:
         image_part = types.Part.from_bytes(data=screenshot_bytes, mime_type='image/jpeg')
         contents = [prompt_text, image_part]
         
    return generate_gemini_response(contents, model_name=model_name)

def _analyze_brand_strategy(content, extracted_context, competitor_content=None, model_name=GEMINI_3_PRO):
    """
    Stage 2: Generates Personas, SWOT, and Strategy using Gemini 3 Pro (Deep Reasoning).
    """
    
    # Context summary minimizes token usage while keeping key info
    context_str = json.dumps(extracted_context)[:5000] 
    
    competitor_section = ""
    if competitor_content:
        competitor_section = f"**COMPETITOR CONTENT:**\n{competitor_content}\n\n"

    prompt_text = f'''
    You are the Chief Strategy Officer (CSO).
    Using the Brand DNA Context provided below, generate high-level STRATEGIC INSIGHTS.
    
    **BRAND DNA CONTEXT:**
    {context_str}
    
    **RAW CONTENT (Source):**
    {content[:80000]}
    
    {competitor_section}
    
    **OBJECTIVE:**
    1. Generate 3-5 detailed **Personas** (JTBD Framework). Ensure these are highly specific to the brand's actual product (e.g. if selling dev tools, target CTOs/Devs, not general 'Managers').
    2. Create a **SWOT Analysis**.
    3. Define the **Strategy** (Moats, Leaks, Wedge).
    4. Provide **Strategic Recommendations** that are actionable and specific, not generic 'marketing speak'.
    
    **OUTPUT JSON:**
    {{
        "personas": [
            {{
                "role": "Specific Job Title",
                "demographics": {{ "age_range": "..", "location": ".." }},
                "jobs_to_be_done": "Main functional/emotional job.",
                "pain_points": ["Specific pain 1", "Specific pain 2"],
                "goals": ["Goal 1", "Goal 2"],
                "buying_trigger": "Crisis that forces purchase.",
                "key_objection": "Why they say no.",
                "preferred_channels": ["Specific Channel 1", "Specific Channel 2"],
                "content_preferences": ["Type 1 (e.g. Whitepapers)", "Type 2 (e.g. API Docs)"],
                "marketing_hook": "One sentence hook that speaks directly to their pain."
            }}
        ],
        "strategy": {{
            "swot_analysis": {{
                "strengths": [".."],
                "weaknesses": [".."],
                "opportunities": [".."],
                "threats": [".."]
            }},
            "market_positioning": "Comparison statement.",
            "competitor_differentiation": ["Diff 1", "Diff 2"],
            "strategic_moats": ["Moat 1", "Moat 2"],
            "strategic_leaks": ["Leak 1"],
            "the_wedge": "Entry point strategy."
        }},
        "strategic_recommendations": ["Rec 1", "Rec 2", "Rec 3"],
        "competitor_analysis": {{
             "comparison_table": [ {{ "feature": "X", "my_brand": "A", "competitor": "B" }} ],
             "competitor_strengths": [".."],
             "our_differentiators": [".."]
        }}
    }}
    '''
    
    return generate_gemini_response(prompt_text, model_name=model_name)



def refine_scanned_links(raw_links, model_name=GEMINI_3_FLASH):

    """

    Refines a list of raw links using Gemini 3 Flash to categorize and rename them intelligently.

    """

    try:

        

        prompt = f'''

        You are a UX Information Architect.

        I will give you a list of raw links found on a homepage.

        Your job is to:

        1.  **Filter** out useless links (Login, Forgot Password, Privacy Policy, Terms, generic 'Read More', 'admin', social media share links).

        2.  **Rename** vague links to be descriptive (e.g. if text is "Learn more" but url is "/pricing", rename to "Pricing"). 

            - **CRITICAL:** Use **Title Case** for all link names (e.g., "About Us" not "about us").

            - **CRITICAL:** Fix any weird spacing or indentation in the text.

        3.  **Categorize** them into: "Company", "Offerings", "Resources", "Contact".

        4.  **Prioritize** the top 15 most important links for a Brand Analysis.

        

        Raw Links:

        {json.dumps(raw_links)}

        

        Output JSON format (Strict List of Objects):

        [

            {{ "label": "About Us", "url": "original_url", "category": "Company" }},

            {{ "label": "Pricing", "url": "original_url", "category": "Offerings" }}

        ]

        '''

        response_text = generate_gemini_response(prompt, model_name=model_name)

        parsed = parse_json_response(response_text)

        

        if isinstance(parsed, list):

            return parsed

        

        print(f"AI returned invalid format (expected list, got {type(parsed)}): {parsed}")

        return raw_links # Fallback to raw if AI fails or returns error dict

    except Exception as e:

        print(f"Error refining links: {e}")

        return raw_links # Fallback to raw



def generate_personas(content, model_name=GEMINI_3_PRO_PREVIEW):

    """

    Generates detailed Buyer Personas with psychographic depth.

    """

    try:

        prompt = f'''
        Based on the following website content, generate **3 to 5 distinct and detailed Buyer Personas** using the **Jobs-to-be-Done (JTBD)** framework.
        
        Content:
        {content[:100000]}
        
        **CRITICAL INSTRUCTIONS:**
        1. **QUANTITY**: You MUST generate between 3 and 5 personas. Do not generate just one.
        2. **NO GENERIC NAMES/ROLES**: Do not use "Marketing Mary" or just "Manager". Use specific roles like "burnout-prone DevOps Lead".
        3. **JOBS TO BE DONE**: Focus on what they are trying to *achieve*, not just who they are.
        4. **REALISTIC CONFLICT**: Identify the specific crisis or trigger that forces them to act.
        5. **ANTI-STEREOTYPE**: Avoid surface-level demographics. Go deep into psychographics.

        Output JSON list format:
        [
            {{
                "role": "Specific Job Title (e.g. 'Overwhelmed CTO')",
                "demographics": {{ "age_range": "...", "gender": "...", "income_level": "..." }},
                "jobs_to_be_done": "Functional/Emotional/Social jobs.",
                "pain_points": ["Deep, visceral pain point 1", "Pain point 2"],
                "goals": ["Strategic Goal 1", "Personal Career Goal"],
                "psychographics": "Values, fears, and motivations.",
                "buying_trigger": "The specific event that forces them to buy.",
                "key_objection": "Why they might say NO.",
                "preferred_channels": ["LinkedIn", "Email", "Slack Communities"],
                "content_preferences": ["Case Studies", "API Docs"],
                "marketing_hook": "The one sentence that will get their attention.",
                "quote": "Verbatim quote of their internal monologue."
            }}
        ]
        '''

        return generate_gemini_response(prompt, model_name=model_name)

    except Exception as e:

        return f"Error generating personas: {str(e)}"



def generate_strategic_insights(content, model_name=GEMINI_3_PRO_PREVIEW):

    """

    Legacy wrapper.

    """

    try:

        prompt = f'''

        As a GTM Strategy Lead, analyze the following brand content and provide strategic insights.

        

        Content:

        {content[:100000]}

        
        **FRAMEWORK: MOATS & LEAKS**
        - **Competitive Moat:** What makes this brand defensible? (e.g. Network Effects, Proprietary Tech). NOT just "Quality".
        - **Strategic Leak:** Where represent the biggest risk of churn or failure?
        - **The Wedge:** What is the specific entry point to win the market?

        Output JSON format:

        {{

            "swot_analysis": {{

                "strengths": ["..."],

                "weaknesses": ["..."],

                "opportunities": ["..."],

                "threats": ["..."]

            }},
            
            "strategic_moats": ["Moat 1", "Moat 2"],
            "strategic_leaks": ["Leak 1", "Leak 2"],
            "market_wedge": "Description of the wedge strategy.",

            "market_positioning": "...",

            "competitor_differentiation": ["..."]

        }}
        '''


        return generate_gemini_response(prompt, model_name=model_name)

    except Exception as e:

        return f"Error generating strategic insights: {str(e)}"



def compare_brands(brand1_content, brand2_content, model_name=GEMINI_3_PRO_PREVIEW):

    """

    Compares two brands.

    """

    try:

        prompt = f'''

        Compare the following two brand contents.

        

        Brand 1 Content:

        {brand1_content[:50000]}

        

        Brand 2 Content:

        {brand2_content[:50000]}

        

        Provide a side-by-side comparison table (Markdown) focusing on:

        1. Brand Voice

        2. Value Proposition

        3. Target Audience

        4. Strengths & Weaknesses relative to each other.

        '''

        return generate_gemini_response(prompt, model_name=model_name)

    except Exception as e:

        return f"Error comparing brands: {str(e)}"



def scan_page_for_opportunities(html_content, brand_context, model_name=GEMINI_3_PRO_PREVIEW):

    """

    X-Ray Scanner: Analyzes the page to find specific elements that need optimization.

    Prioritizes issues that affect SEO/AEO ranking (e.g., generic H1s, text walls).

    

    Args:

        html_content: The raw HTML of the page.

        brand_context: Description of brand/audience.

        

    Returns:

        JSON list of "Opportunity" objects.

    """

    try:

        prompt = f'''

        You are an Elite SEO & Conversion Rate Optimization (CRO) Auditor (X-Ray Scanner).

        

        **OBJECTIVE:**

        Scan the provided HTML and identify 3-5 SPECIFIC components that are suboptimal for:

        1. **Organic SEO**: (e.g., Generic H1s, Missing Keywords in Headings)

        2. **AEO (AI Readiness)**: (e.g., Unstructured text walls that should be tables/lists, missing Schema-worthy Q&A)

           - **CRITICAL DISTINCTION FOR FAQS**: 

             - If you see a visual FAQ section but NO JSON-LD Schema, report "Issue" as: "Visual FAQ detected but missing Schema Markup".

             - If there is NO FAQ section at all, report "Issue" as: "Missing FAQ Section (High AEO Opportunity)".

        3. **UX & Conversion**: (e.g., Weak/Missing CTAs, Buried Value Props, Poor Visual Hierarchy, "Wall of Text")

        

        **BRAND CONTEXT:**

        {brand_context}

        

        **PAGE HTML:**

        {html_content[:50000]}

        

        **INSTRUCTIONS:**

        - Identify specific HTML elements (e.g., " The 'Features' Section", "Hero CTA").

        - Explain WHY it fails (e.g., "Button label 'Submit' causes friction", "Paragraph is 15 lines long").

        - Suggest a FIX TYPE (e.g., "Rewrite", "Structure Swap: Table", "Design: Feature Grid", "CTA Upgrade").

        - **CRITICAL**: Do NOT just look at H1s. Look deep into the body content.

        

        **OUTPUT JSON:**

        {{

            "opportunities": [

                {{

                    "id": "chem_1",

                    "element_name": "Hero Section Headline",

                    "current_snippet_preview": "Welcome to...",

                    "issue": "Headings lacks commercial intent keywords.",

                    "fix_type": "Rewrite",

                    "impact_score": 95,

                    "rationale": "Ranking #1 requires specific intent matching in H1."

                }},

                {{

                    "id": "chem_2",

                    "element_name": "Pricing Section",

                    "current_snippet_preview": "Contact us for price...",

                    "issue": "High friction. Competitors show pricing upfront.",

                    "fix_type": "Structure Swap: Pricing Table",

                    "impact_score": 88,

                    "rationale": "Transparency increases conversion/trust for this persona."

                }},

                 {{

                    "id": "chem_3",

                    "element_name": "Feature List",

                    "current_snippet_preview": "We have fast servers and...",

                    "issue": "Buried in a dense paragraph.",

                    "fix_type": "Design: Icon Grid",

                    "impact_score": 80,

                    "rationale": "Scannability is critical for UX and AEO extraction."

                }}

            ]

        }}

        '''

        

        result = generate_gemini_response(prompt, model_name=model_name)

        data = parse_json_response(result)

        return data.get("opportunities", [])

        

    except Exception as e:

        print(f"Scan error: {e}")

        return []



def generate_growth_asset(content, asset_type, target_element_context, brand_style="Modern, Clean, Professional", model_name=GEMINI_3_PRO_PREVIEW, design_tokens=None, html_context="", visual_identity=None):

    """

    Generates a high-quality, brand-aligned HTML component ('Growth Asset') to fix a detected opportunity.

    

    Args:

        content: Page context

        asset_type: The fix type/asset name (e.g. "Optimized H1", "Pricing Table")

        target_element_context: The specific issue/element found by the scanner.

        brand_style: Style description

        design_tokens: Extracted design variables

        html_context: Raw HTML

        visual_identity: Dict with palette, vibe, etc. (From Visual Analysis)

    """

    try:





        # 1. Format CSS Variables (Strict Enforcement)

        css_vars = ""

        design_context = ""

        

        if design_tokens:

            from utils.design_extractor import format_design_context, generate_css_vars

            design_context = format_design_context(design_tokens)

            css_vars = generate_css_vars(design_tokens)

            

        if not css_vars:

            # Fallback Design System (if extraction failed)

            css_vars = """

            :root {

                --primary: #2563ea; /* Default Blue */

                --secondary: #64748b;

                --text-color: #1e293b;

                --bg-color: #ffffff;

                --radius: 8px;

                --font-main: 'Inter', system-ui, sans-serif;

            }

            """

            design_context += "\n(Using Default Modern Theme as fallback)"

            

        # Integrate Visual Identity if available (Overrides/Enhances)

        visual_context_str = ""

        if visual_identity:

            pal = visual_identity.get('primary_palette', [])

            vibe = visual_identity.get('visual_vibe', 'Modern')

            if pal:

                # Update fallback/vars if possible, or just instruct the AI

                visual_context_str = f"""

                **VISUAL BRAND IDENTITY (PRIORITY):**

                - **Primary Palette**: {', '.join(pal)}

                - **Visual Vibe**: {vibe}

                - **Instruction**: STRICTLY use these specific Hex codes for buttons, borders, and accents. Match this vibe in the design.

                """



        prompt = f'''

        You are a Top-Tier Frontend Engineer & AEO Optimizer.

        

        **TASK:** 

        Create a **High-Conversion HTML Component** to resolve this specific content issue:

        > ISSUE: "{target_element_context}"

        > GOAL: Build a "{asset_type}" that fixes this.

        

        **CONTENT SOURCE:**

        {content[:30000]}

        

        **DESIGN SYSTEM (STRICT):**

        {design_context}

        {visual_context_str}

        

        **CSS VARIABLES (MANDATORY):**

        {css_vars}

        

        **CODING RULES:**

        1. **Standalone Component**: Return a single `div` container. NO `<html>`, `<head>`, or `<body>` tags.

        2. **Styling**: 

           - Use `style="..."` attribute for EVERYTHING.

           - **NEVER** use `<style>` blocks. Use inline styles.

           - **ALWAYS** use the provided CSS Variables (`background: var(--bg-color)`).

           - Use `display: flex` or `grid` for layout. Padding: `2rem`.

        3. **Content (CRITICAL)**:

           - **DO NOT INVENT CONTENT**. Do not use "Lorem Ipsum" or generic "Company Name".

           - Use the **Real Brand Name** and **Real Text** found in the CONTENT SOURCE.

           - If the specific section (e.g. detailed pricing) is missing in the source, use intelligent, brand-specific placeholders (e.g. "Enterprise Plan" instead of "Plan A"), but clearly mark them.

           - **Better Structure**: If the issue is "dense text", convert it to a **List** or **Table**.

        4. **Schema**:

           - Improve AEO understanding by adding a `<script type="application/ld+json">` block at the end (e.g. `FAQPage` or `Product`).

        

        **OUTPUT JSON:**

        {{

            "asset_name": "{asset_type}",

            "strategic_rationale": "One sentence on why this design wins.",

            "original_html_snippet": "The specific HTML snippet from the source that this component replaces (extracted effectively).",

            "optimized_html_code": "<div style='background: var(--bg-color); border: 1px solid var(--primary); padding: 2rem; border-radius: var(--radius); font-family: var(--font-main);'> ...content... <script type='application/ld+json'>...</script></div>"

        }}

        '''

        

        result_text = generate_gemini_response(prompt, model_name=model_name)

        return json.dumps(parse_json_response(result_text))

        

    except Exception as e:

        return json.dumps({"error": str(e), "optimized_html_code": f"<div>Error generating asset: {e}</div>"})





def generate_ab_test(content, brand_style="Modern, Clean, Professional", model_name=GEMINI_3_PRO_PREVIEW):

    """

    Generates A/B testing hypotheses.

    """

    try:

        prompt = f'''

        Based on the content, generate 2 distinct A/B testing variations to improve conversion.

        

        Content:

        {content[:100000]}

        

        Output JSON format:

        {{

            "original_content_snippet": "The exact original text section that is being tested.",

            "original_html_mockup": "A visual HTML/CSS representation of the ORIGINAL content. Use inline CSS. Infer the likely current design based on the brand style '{brand_style}'.",

            "variants": [

                {{

                    "variant_name": "Variation A: [Name]",

                    "hypothesis": "If we change X, then Y will happen because Z.",

                    "changes": ["Change headline to...", "Add CTA..."],

                    "html_snippet": "<div>...HTML of the new section with inline CSS. Design this to match the brand style: '{brand_style}'. Use modern design trends and make it look like a professional landing page section...</div>"

                }},

                {{

                    "variant_name": "Variation B: [Name]",

                    "hypothesis": "...",

                    "changes": ["..."],

                    "html_snippet": "<div>...HTML with inline CSS. Design this to be VISUALLY DISTINCT from Variant A but still adhering to the brand style: '{brand_style}'. Maintain a premium, high-quality look...</div>"

                }}

            ]

        }}

        '''

        return generate_gemini_response(prompt, model_name=model_name)

    except Exception as e:

        return f"Error generating A/B tests: {str(e)}"













def generate_marketing_asset(brand_content, asset_type, theme, model_name='gemini-2.0-pro-exp-02-05'):

    # Legacy function - keeping for compatibility but redirecting logic if needed or just simple wrapper

    # For now, just standard generation

    try:

        prompt = f'''

        You are a Marketing Expert. Create a {asset_type} for the following brand.

        

        Brand Context:

        {brand_content[:50000]}

        

        Theme/Topic: {theme}

        

        Requirements:

        - Professional tone.

        - High quality, ready to publish.

        - Format in Markdown.

        '''

        return generate_gemini_response(prompt, model_name=model_name)

    except Exception as e:

        return f"Error generating asset: {str(e)}"



def calculate_brand_health(analysis_json, personas_json, strategic_json=None, model_name=GEMINI_3_PRO_PREVIEW):

    """

    Calculates a 0-100 Brand Health Score based on the analysis.

    """

    try:

        prompt = f'''

        Analyze the following brand data and calculate a "Brand Health Score" from 0 to 100.

        

        Brand Analysis:

        {json.dumps(analysis_json)}

        

        Buyer Personas:

        {json.dumps(personas_json)}

        

        Strategic Insights:

        {json.dumps(strategic_json) if strategic_json else "N/A"}

        

        **SCORING RUBRIC (STRICTLY FOLLOW):**

        - **Clarity (0-100)**: 

           - 90-100: "What is it?" is answered instantly in the Hero H1. Value Prop is explicit.

           - 70-89: H1 is slightly vague but H2/Subheader explains it well.

           - <70: Confusing jargon, "Welcome to...", or buried value proposition.

        - **Consistency (0-100)**:

           - 90-100: Tone and Voice are perfectly uniform across all sections.

           - <70: Voice shifts (e.g. erratic shifts from formal to slang).

        - **Audience Alignment (0-100)**:

           - 90-100: Explicitly calls out the target learner/buyer (e.g. "For CTOs").

           - <60: Generic "For everyone" messaging.

        - **Uniqueness (0-100)**:

           - 90-100: Clearly defined Unique Selling Proposition (USP) or proprietary mechanism.

           - <60: Generic claims ("We are the best", "High quality") without proof.



        **STRATEGIC RECOMMENDATIONS RULE:**

        - Identify the metrics with the LOWEST scores provided above.

        - Generate 3 detailed, tactical recommendations specifically addressing those weak points.

        - Start each recommendation with an ACTION VERB (e.g., "Add", "Rewrite", "Simplify", "Remove").

        

        Output JSON format:

        {{

            "overall_health_score": 85,

            "metrics": {{

                "clarity": {{ "score": 80, "description": "H1 is vague, but subheader saves it." }},

                "consistency": {{ "score": 90, "description": "Uniform professional tone." }},

                "audience_alignment": {{ "score": 70, "description": "Implies targeting but doesn't name it." }},

                "uniqueness": {{ "score": 85, "description": "Proprietary 'X-Ray' feature mentioned." }}

            }},

            "strategic_recommendations": [

                "Action 1: Fix the [Lowest Score Area] by doing X...", 

                "Action 2: Enhance [Next Weakest] by...",

                "Action 3: ..."

            ],

            "strengths": ["Strength 1", "Strength 2"]

        }}

        '''

        # Low temperature for deterministic results

        return generate_gemini_response(prompt, model_name=model_name, temperature=0.1)

    except Exception as e:

        return f"Error calculating brand health: {str(e)}"



def extract_brand_knowledge(content, model_name=GEMINI_3_PRO_PREVIEW):

    """

    Extracts structured brand knowledge (products, features, benefits) from content.

    """

    try:

        prompt = f'''

        Analyze the following website content and extract a structured Knowledge Graph of the brand's offerings.

        

        Content:

        {content[:100000]}

        

        Output JSON format:

        {{

            "products": [

                {{

                    "name": "Product Name",

                    "description": "Brief one-line description",

                    "features": ["Feature 1", "Feature 2"],

                    "benefits": ["Benefit 1", "Benefit 2"]

                }}

            ],

            "key_terms": ["Term 1", "Term 2 (Proprietary tech, etc.)"],

            "brand_colors": ["#HexCode1", "#HexCode2"] (Infer from text if mentioned, otherwise null)

        }}

        '''

        return generate_gemini_response(prompt, model_name=model_name)

    except Exception as e:

        return f"Error extracting brand knowledge: {str(e)}"



def generate_viral_hooks(topic, persona_role, brand_voice_desc="", persona_details=None, model_name=GEMINI_3_FLASH):

    """

    Generates 10 high-conversion viral hooks/headlines context-aware of Persona and Brand Voice.

    """

    try:

        # Context Construction

        persona_context = ""

        if persona_details:

             role = persona_details.get('role', 'General Audience')

             pain_points = persona_details.get('pain_points', [])

             persona_context = f"Target Audience: {role}.\n - Pain Points: {', '.join(pain_points[:3])}."

        elif persona_role:

             persona_context = f"Target Audience: {persona_role}"



        voice_instruction = ""

        if brand_voice_desc:

            voice_instruction = f"Brand Voice: '{brand_voice_desc}'. Adapt hooks to this tone (e.g., if 'Professional', avoid clickbait; if 'Edgy', be bold)."



        prompt = f'''

        You are a Viral Copywriting Expert.

        Generate 10 HIGH-CONVERSION hooks/headlines for a piece of content about "{topic}".

        

        CONTEXT:

        {persona_context}

        {voice_instruction}

        

        Patterns to use (adapted to the Voice/Persona above):

        - "How to [Benefit] without [Pain]"

        - "The [Adjective] Guide to..."

        - "Stop doing [Common Mistake]..."

        - "X vs Y: The Truth"

        - Contrarian/Polarizing takes

        - Numbers/Lists (e.g. "7 ways to...")

        

        Output format: JSON list of strings.

        Example: ["Hook 1", "Hook 2"]

        '''

        response = generate_gemini_response(prompt, model_name=model_name)

        return parse_json_response(response)

    except Exception as e:

        return [f"Error generating hooks: {e}"]





def generate_campaign_asset(content, asset_type, theme, campaign_context, knowledge_graph=None, model_name=GEMINI_3_PRO_PREVIEW, temperature=0.7, tone_instruction="", persona_details=None, seo_keywords=None, strict_voice=False, brand_voice_desc="", visual_identity=None, design_tokens=None, brand_archetype=None, brand_dna=None, funnel_stage=None):

    """

    Generates a marketing asset using a "Deep Writer" 3-step chain (Strategy -> Draft -> Polish).

    Includes structural branching for specific asset types (Email, Video, Social).
    
    [UPDATED] Now strictly enforces Tone/Style and Anti-Fluff rules.
    """

    try:
        # --- Context Construction ---

        # [NEW] Anti-Fluff & Quality Rules (Global)
        quality_rules = """
        **QUALITY CONTROL (STRICT):**
        1. **NO GENERIC AI FLUFF**: Forbidden phrases: "In today's fast-paced world", "Unlock", "Elevate", "Delve", "Game-changer", "Revolutionize", "Landscape".
        2. **NO CORPORATE JARGON**: Avoid "Synergy", "Paradigm shift", "Thought leader" (unless satirizing).
        3. **BE SPECIFIC**: Use concrete nouns and verbs. Don't say "We improve efficiency", say "We cut deployment time by 40%".
        """

        # [NEW] Knowledge Graph Parsing & Vocabulary Lock
        kg_str = "Not available"
        vocabulary_instruction = ""
        
        if knowledge_graph:
            kg_str = json.dumps(knowledge_graph, indent=2)
            
            # Extract Key Terms for Vocabulary Lock
            key_terms = knowledge_graph.get("key_terms", [])
            if key_terms:
                term_list = ", ".join(key_terms)
                vocabulary_instruction = f"""
                **VOCABULARY LOCK (STRICT):**
                You MUST use the brand's specific terminology.
                - Terms to use: {term_list}
                - Do NOT use generic synonyms for these terms.
                """

        persona_context = ""

        if persona_details:

             role = persona_details.get('role', 'General Audience')

             pain_points = persona_details.get('pain_points', [])

             psychographics = persona_details.get('psychographics', '')

             if role and not pain_points:

                  persona_context = f"Target Audience: {role}. (Infer pain points)."

             else:

                  persona_context = f"Target Audience: {role}.\n- Pain Points: {', '.join(pain_points)}.\n- Psychographics: {psychographics}\n- Marketing Hook: {persona_details.get('marketing_hook', '')}"



        seo_instruction = ""

        if seo_keywords:

            seo_instruction = f"""

            **SEO & STRATEGY LOCK:**

            You MUST naturally integrate the following keywords/concepts. Do not stuff them, but ensure they are present in key areas (Headings, First Paragraph):

            Keywords: {', '.join(seo_keywords)}

            """



        voice_instruction = ""

        if strict_voice and brand_voice_desc:
            voice_instruction = f"**BRAND VOICE DNA (STRICT):**\n'{brand_voice_desc}'\n- Adhere to this personality, **but adjust your vocabulary/complexity** to match the Target Audience & Tone defined below.\n- Do not use generic AI fluff."

        # [NEW] Tone/Style Override (The "Humanizer" Connection)
        tone_override = ""
        if tone_instruction:
            tone_override = f"""
            **TONE & STYLE SETTING (HIGHEST PRIORITY):**
            {tone_instruction}
            - If this confuses with Brand Voice, the TONE SETTING wins for the 'Vibe' (e.g. valid to have a 'Professional' brand write a 'Funky' post if requested).
            """

            



        # [NEW] Archetype Logic (Personality Chip)
        archetype_instruction = ""
        if brand_archetype:
            archetype_rules = {
                "The Outlaw": "Be rebellious. Challenge the status quo. Use short, punchy sentences. Break grammar rules for effect.",
                "The Magician": "Be visionary and transformative. Use metaphors of change and alchemy. Focus on the 'possibility'.",
                "The Hero": "Be inspiring and courageous. Focus on overcoming obstacles. Use strong, active verbs.",
                "The Sage": "Be authoritative, factual, and objective. Use data and logic. Avoid fluff.",
                "The Creator": "Be expressive and original. Focus on innovation and imagination.",
                "The Ruler": "Be commanding and confident. Focus on leadership, stability, and control.",
                "The Caregiver": "Be empathetic, warm, and supportive. Focus on service and protection.",
                "The Innocent": "Be optimistic, honest, and humble. Focus on simplicity and happiness.",
                "The Jester": "Be humorous, playful, and irreverent. Don't take things too seriously.",
                "The Lover": "Be passionate, sensory, and intimate. Focus on relationships and pleasure.",
                "The Explorer": "Be adventurous and authentic. Focus on discovery and freedom.",
                "The Everyman": "Be down-to-earth, relatable, and unpretentious. Avoid jargon."
            }
            # Find the best match (simple substring check)
            matched_rule = next((rule for arc, rule in archetype_rules.items() if arc in brand_archetype), "Maintain a consistent brand personality.")
            
            archetype_instruction = f"""
            **ARCHETYPE DNA ({brand_archetype}):**
            {matched_rule}
            """

        # [NEW] Strategic Narrative (The Enemy & The Cause)
        narrative_instruction = ""
        if brand_dna:
            enemy = brand_dna.get("brand_enemy", "")
            cause = brand_dna.get("brand_noble_cause", "")
            if enemy or cause:
                narrative_instruction = f"""
                **STRATEGIC NARRATIVE:**
                - **The Enemy (The Villain):** {enemy}. (Frame your copy to fight against this).
                - **The Noble Cause (The Why):** {cause}. (This is the ultimate goal).
                """

        visual_tone_instruction = ""
        if visual_identity:
            vibe = visual_identity.get('visual_vibe', '')
            sentiment = visual_identity.get('image_sentiment', '')

            if vibe or sentiment:
                visual_tone_instruction = f"""
                **VISUAL & ATMOSPHERIC DIRECTION:**
                The brand's visual identity is "{vibe}" with imagery that conveys "{sentiment}".
                Ensure the content's tone and imagery suggestions align with this aesthetic.
                """


        # [NEW] Funnel Stage Logic
        funnel_instruction = ""
        if funnel_stage:
             # Basic mapping
             if "ToFU" in funnel_stage:
                 funnel_instruction = """
                 **FUNNEL STAGE CONTEXT: ToFU (Top of Funnel - Awareness)**
                 - **Goal**: Educate, Entertain, and Inspire.
                 - **Strategy**: Focus on the *Problem* and *Possibility*. Do NOT sell hard. Do NOT focus on technical specs yet.
                 - **Content Depth**: Broad, accessible, high-level.
                 - **Call to Action**: Low friction (e.g., "Learn more", "Subscribe", "Read this").
                 """
             elif "MoFU" in funnel_stage:
                 funnel_instruction = """
                 **FUNNEL STAGE CONTEXT: MoFU (Middle of Funnel - Consideration)**
                 - **Goal**: Prove, Compare, and Build Trust.
                 - **Strategy**: Position the brand as the best solution. Use social proof, comparisons, and case studies.
                 - **Content Depth**: Moderate depth, focus on "How it works" and "Why us".
                 - **Call to Action**: Medium friction (e.g., "View Case Study", "Watch Demo", "Download Guide").
                 """
             elif "BoFU" in funnel_stage:
                 funnel_instruction = """
                 **FUNNEL STAGE CONTEXT: BoFU (Bottom of Funnel - Decision)**
                 - **Goal**: Convert, Close, and reassure.
                 - **Strategy**: Address objections, focus on ROI/Value, and ask for the sale.
                 - **Content Depth**: Specific, technical (if needed), detailed, reassurance-heavy.
                 - **Call to Action**: High friction (e.g., "Buy Now", "Book Call", "Start Trial").
                 """
                 
        # [NEW] Visual DNA Hard Lock (Design Tokens)
        if design_tokens:
            try:
                from utils.design_extractor import format_design_context
                # Append strict rules to the visual instruction
                visual_tone_instruction += "\n" + format_design_context(design_tokens)
            except ImportError:
                pass



        # --- BRANCHING LOGIC: Asset Type Specifics ---

        format_guidelines = ""

        structure_prompt = ""

        

        if asset_type == "Email Newsletter":

            format_guidelines = """

            - **Format**: Email Newsletter (Professional Memo).
            
            - **Vibe Constraint**: "Colleague Memo" style. Helpful, Concise, Professional. Think of it as a brief memo from a colleague rather than a marketing blast.

            - **Length Constraint**: STRICTLY 200–400 words.

            - **Structure (Mandatory)**:
                1. **Subject Lines**: 3 options. MUST be lower-case or sentence-case (e.g., "quick question about retention").
                2. **The Hook**: One punchy sentence reflecting a common industry pain point.
                3. **The Solution**: 2–3 sentences on how the offering addresses it.
                4. **The Proof**: A single data point or a 2-line mini-case study.
                5. **The CTA**: One clear, bolded action.
                6. **The P.S.**: Mandatory "Hidden Gem" trick (tip or low-friction CTA).

            - **Style**: Personal, direct, 1:1 conversation style. NO "H1/H2" blog headers inside the body. Use bolding and bullet points for readability.
            
            - **CRITICAL FORMAT RULE**:
                - Output **PURE MARKDOWN** only.
                - **DO NOT** generate HTML code (<div>, <body>, <style>).
                - **DO NOT** use inline CSS.
                - Write it as if you are typing a plain text email.

            """

            structure_prompt = "Draft the Memo: Hook (Pain), Solution (Brief), Proof (Data), and CTA."

            

        elif asset_type == "Video Script (Long Form)":

            format_guidelines = """

            - **Format**: 2-Column Video Script (Markdown Table or clear separation).

            - **Components**: 

                1. Visual/Scene Description (Left).

                2. Audio/Dialogue (Right).

            - **Style**: Spoken word, rhythmic, easy to read for a narrator.

            """

            structure_prompt = "Outline the Video Arc: Hook, Retention Points, and Call to Action."



        elif asset_type == "TikTok/Reels Script":

             format_guidelines = """

            - **Format**: Short-Form Video Script (Vertical).

            - **Components**:

                1. **Screen Text**: what appears on screen.

                2. **Spoken Audio**: Fast-paced voiceover.

                3. **Visual Cue**: B-roll or face-cam instruction.

            - **Pacing**: FAST. Changes every 3 seconds.

            - **Length**: 30-60 seconds max.

            """

             structure_prompt = "Outline the Viral Arc: The 'Pattern Interrupt' (Hook), The Turn, and The Payoff."



        elif asset_type == "Cold Email (Outreach)":

             format_guidelines = """

            - **Format**: Modern B2B Cold Email (The "Anti-Sales" Approach).

            - **CORE PHILOSOPHY**:
                1. **Hyper-Concise**: Max 100 words. Mobile-optimized.
                2. **No Fluff**: No "I hope you are well". No "My name is X and I work at Y". Start immediately.
                3. **Value-First**: Give them a reason to care before asking for anything.

            - **Components**:
                1. **Subject Line**: 3 Options. MUST be short (1-4 words), lowercase, neutral. 
                   - *Good*: "question", "quick thought", "marketing ideas".
                   - *Bad*: "Unlock Your Potential", "Meeting Request", "Partnership Opportunity".
                
                2. **The "Trigger" (First Sentence)**: A specific observation. "Saw you are hiring for X", "Noticed your post about Y". (Since you are AI, simulate a relevant observation based on the Brand/Persona context).
                
                3. **The Problem**: A one-sentence agitation of a pain point derived from the Persona.
                
                4. **The Fix**: How we solve it unique (The Value Prop).
                
                5. **The Soft Ask**: Interest-based CTA. Low friction.
                   - *Good*: "Worth a chat?", "Open to seeing how?", "Any interest?"
                   - *Bad*: "Can I book 15 mins?", "Click here to buy".

            - **Style**: Humble, conversational, "Human-to-Human". NOT corporate or salesy.
            
            - **Visuals**: NONE. Pure text.

            """

             structure_prompt = "Draft a 'Spear' Email: Observation -> Problem -> Solution -> Soft Ask."





        elif asset_type == "Landing Page Copy":

             # [NEW] Strict Visual DNA Construction
             visual_dna_script = ""
             if design_tokens:
                 # extract fallback if keys missing
                 p_color = design_tokens.get("primary_color", "#667eea")
                 s_color = design_tokens.get("secondary_color", "#764ba2") 
                 bg_color = design_tokens.get("background_color", "#ffffff") if design_tokens.get("color_scheme") == "light" else "#111827"
                 font = design_tokens.get("font_primary", "Inter")

                 visual_dna_script = f"""
                 <!-- BRAND DNA INJECTION -->
                 <script>
                    tailwind.config = {{
                      theme: {{
                        extend: {{
                          colors: {{
                            brand: {{
                              primary: '{p_color}',
                              secondary: '{s_color}',
                              accent: '{p_color}',
                              bg: '{bg_color}',
                              surface: '{ "#ffffff" if design_tokens.get("color_scheme") == "light" else "#1f2937" }',
                              text: '{ "#111827" if design_tokens.get("color_scheme") == "light" else "#f9fafb" }'
                            }}
                          }},
                          fontFamily: {{
                            brand: ['{font}', 'sans-serif'],
                            sans: ['{font}', 'sans-serif']
                          }}
                        }}
                      }}
                    }}
                 </script>
                 """
             
             format_guidelines = f"""
            - **Format**: Single-File HTML Bundle (Embedded in a Markdown Code Block).
            
            - **FRAMEWORK: "The StoryBrand Bento UI"**:
                - Combine the narrative power of StoryBrand (Clear Message) with the visual density of Bento Grids.
            
            - **VISUAL DNA (STRICT)**:
                - **MUST** include this Tailwind Configuration Script inside the `<head>`:
                {visual_dna_script if visual_dna_script else "<!-- Use Default Tailwind -->"}
                
            - **COMPONENT RULES (Tailwind)**:
                1. **Buttons**: Use `bg-brand-primary text-white hover:opacity-90 rounded-full px-8 py-4 shadow-lg active:scale-95 transition-all`.
                2. **Typography**: Use `font-brand` for everything.
                3. **Cards**: Use `bg-brand-surface border border-gray-200/10 shadow-xl rounded-2xl` (Glassmorphism if dark mode).
                4. **Hero Section**: CENTERED Layout. Massive H1 (text-5xl+). Subhead. Two Buttons (Primary & Secondary).
                5. **Bento Grid**: For "Features", use a CSS Grid (`grid-cols-3`) with varying col-spans to create a Bento-style layout.
            
            - **STRUCTURE (The Narrative)**:
                1. **The Header**: Logo (Text) + Nav + CTA.
                2. **The Hero**: "The Promise". One clear benefit.
                3. **The Logic**: "Three-Step Process" (How it works).
                4. **The Proof**: Testimonial Wall (Masonry or Grid).
                5. **The Value**: Bento Grid of Benefits.
                6. **The Explainer**: FAQ Accordion.
                7. **The Footer**: Clean, multi-column.

            - **Output Constraint**:
                - Return **ONLY valid HTML** inside a `html` code block.
                - Do NOT include markdown outside the code block (except for a brief strategy memo *before* it).
                - Ensure `<script src="https://cdn.tailwindcss.com"></script>` is included.
            """

             structure_prompt = "Outline the StoryBrand Flow: Hero (Promise) -> Guide (Process) -> Victory (Bento Grid) -> Action."



        elif asset_type == "Case Study":

             format_guidelines = """

            - **Format**: B2B Case Study (Markdown) - The Hero's Journey.

            - **1. ATTRACTING READERS (THE MAGNET)**:
                - **Headline (Strict)**: MUST be specific: "How [Customer] [Result Verb] [Metric] in [Timeframe] using [Solution]".
                  - *Bad*: "How Company X improved operations."
                  - *Good*: "How Acme Corp Reduced Costs by 40% in 6 Months using Our AI."
                - **The "Peer" Factor**: Adjust tone to match the customer's specific industry/role.
                - **Visual Marker**: Insert `[INSERT_IMAGE_HERE]` at the top for the "Before/After" visual concept.

            - **2. THE JOURNEY (NARRATIVE STRUCTURE)**:
                - **The Villain (The Challenge)**: Define the problem in emotional/financial terms (Chaos). What was at stake?
                - **The Selection (Turning Point)**: Briefly explain why they chose US over others (handling objections).
                - **The Solution (Implementation)**: How it fit into their life. Punchy timeline/process steps.
                - **The Victory (Results)**:
                    - **Hard Metrics**: Use a **Mermaid Bar Chart** (`mermaid`) to visualize the growth/savings.
                    - **Soft Metrics**: Improved morale, vibe, ease.
                    - **The Quote**: A powerful, human testimonial.

            - **3. ENGAGEMENT TACTICS**:
                - **Sidebars**: Use Blockquotes (`> **Technical Specs**: ...`) to hide boring technical details.
                - **Power Breaks**: Use bold, centered pull-quotes to break up long text.

            """

             structure_prompt = "Outline the Hero's Journey: The Villain (Pain) -> The Guide (Us) -> The Path (Plan) -> The Victory (Metrics via Chart)."
             
             # [NEW] 2026 Standard: Visual Snapshot
             format_guidelines += "\n\n**VISUAL REQUIREMENT**: Include a description of a 'Results Snapshot' chart/graphic that summarizes the win."



        elif asset_type == "Press Release":

             format_guidelines = """

            - **Format**: Standard Press Release (AP Style).

            - **Components**:

                1. **FOR IMMEDIATE RELEASE** (at top).

                2. **Dateline**: (City, State) – Date.

                3. **Headline**: Strong, news-worthy, active voice.

                4. **Body**: Inverted Pyramid style (Most important info first).

                5. **Quote**: Executive quote.

                6. **Boilerplate**: "About Us" section.

                7. **Media Contact**: Name, Email, Phone.

                8. **###** (Centered at bottom).

            """

             structure_prompt = "Draft the News Angle: The 'New' thing, the Quote, and the Impact."



        elif asset_type == "Whitepaper":

             format_guidelines = """

            - **Format**: Professional Whitepaper (Markdown).

            - **Structure**:

                1. **Title Page**: Compelling Title + Subtitle.

                2. **Executive Summary**: High-level overview (10% of length).

                3. **Introduction**: The Landscape/Problem.

                4. **Deep Dive**: Technical/Strategic Analysis (Data-driven).

                5. **The Solution**: Methodology/Framework.

                6. **Conclusion**: Summary + Future Outlook.
                
                7. **About the Author/Company**: Brief credibility statement.

            - **VISUALS & DATA (STRICT)**:
                - **NO "DESIGN SPECS"**: Do NOT write instructions like "Insert image here" or "Visual specs for designer".
                - **IMPLEMENT DIRECTLY**: 
                    - Use **Mermaid.js** for flowcharts/diagrams (wrap in ```mermaid code block).
                    - Use **Markdown Tables** for data comparison.
                    - Use **Blockquotes (>)** for key statistics or pull-quotes.
                - **Chart Requirement**: You MUST include at least one Mermaid Diagram (e.g., a Process Flow or Pie Chart) to visualize the data.

            - **Tone & Persona**: 
                - **Strictly adhere** to the complexity level defined (e.g., if "Jargon-Heavy", use technical depth; if "Simple", use analogies).
                - Write for the target persona: {persona_details.get('role', 'Reader') if persona_details else 'Decision Maker'}.

            """

             structure_prompt = "Outline the Authority Arc: Landscape -> Problem data (with Table) -> Methodology (with Diagram) -> Solution."
             
             # [NEW] 2026 Standard: Sidebar & Executive Summary
             format_guidelines += "\n\n**SIDEBAR REQUIREMENT**: You MUST include a 'Key Takeaways' sidebar/blockquote at the start of the deep dive section."



        elif asset_type == "Blog Post":

            format_guidelines = """

            - **Format**: High-Performance Blog Post (Markdown).

            - **1. ATTRACTING READERS (THE MAGNETISM)**:
                - **The "Search-Social" Split**:
                    - IF the goal implies SEARCH/SEO (e.g. "Rank for...", "How to..."): Title must answer a specific question (e.g., "How to Measure Brand ROI in 2026").
                    - IF the goal implies SOCIAL/VIRAL (e.g. "Challenge...", "Thought Leadership"): Title must challenge a belief (e.g., "Why Most Brand Awareness Campaigns Are Just Expensive Noise").
                    - **Action**: Provide 2 Title Options (Option A: Search Optimized, Option B: Social/Provocative) at the very top.
                - **Leverage "The Gap"**: Start the Introduction with a startling statistic or a counter-intuitive fact that opens a curiosity gap.

            - **2. KEEPING THEM ENGAGED (THE "GREASED SLIDE")**:
                - **The "You" Focus**: Strict Rule: For every 1 mention of "We/Us/The Brand", use "You/Your" 5 times.
                - **Bucket Brigades**: Use short bridge sentences to keep momentum (e.g., "Here is the kicker...", "But it gets better...", "Why does this matter?").
                - **Interactive Elements**: Include "Think Points" or mini-checklists (e.g., "Ask yourself: If your brand disappeared tomorrow...").
                - **The "Soft" Middle CTA**: About 50%% through, include a Call-out Box (Blockquote) with a value-add unrelated to a hard sale (e.g., "Download the template", "Check the webinar").
                
                - **5. VISUAL PLACEMENT (STRICT)**:
                     - You MUST insert the marker `[INSERT_IMAGE_HERE]` exactly where the Hero Image should appear.
                     - This usually works best AFTER the Title but BEFORE the Body, or sometimes after the "Gap" intro. Evaluate the best flow.

            - **3. THE CAMPAIGN THREAD**:
                - Hyperlink specific keywords to "Product Page" or "Demo" where relevant solution concepts are mentioned.

            - **4. EXPERT BEST PRACTICES**:
                - **Scannability**: Short paragraphs (max 3-4 lines).
                - **Structure**: H1 -> Intro (The Gap) -> H2s (The Meat) -> H3s (The Detail) -> Conclusion -> CTA.
                - **Tone Alignment**: Strictly follow the Humanizer/Persona settings.

            """

            structure_prompt = "Outline the Flow: Magnetism Titles -> Curiosity Gap Intro -> The Core Value (with Bucket Brigades) -> Soft Middle CTA -> The Solution -> Conclusion."
             
            # [NEW] 2026 Standard: Social Metadata
            format_guidelines += """
             
            **SOCIAL METADATA (STRICT)**:
            At the very end of the post, generate a "Social Sharing Metadata" block (in a code block) containing:
            - **OG Title**: Optimized for clicks.
            - **OG Description**: <160 chars.
            - **Twitter Card**: Summary.
            
            **STYLING RULES (CRITICAL)**:
            - Do NOT use HTML tags (like <p>, <div>, <span>) for styling. 
            - Use standard Markdown exclusively (e.g. `>` for quotes, `**` for bold).
            """

            

        elif asset_type == "Instagram Post (Visual)":

             format_guidelines = """

            - **Format**: Instagram Visual + Caption.

            - **Components**:

                1. **Visual Concept Description**: (Detailed prompt for what the image/reel should be).

                2. **The Hook**: First line overlaid on image or caption start.

                3. **Caption Body**: Short, punchy, visually spaced.

                4. **Hashtags**: 30 Relevant tags.

            - **Style**: Aesthetic, visual-first, inspiring.

            """

             structure_prompt = "Outline the Visual Concept and the accompanying Caption story."



        elif asset_type == "LinkedIn Post (Professional)":

             format_guidelines = """

            - **Format**: LinkedIn Text Post.

            - **Components**:

                1. **The Hook**: A standalone one-liner that STOPS the scroll. (Pattern Interrupt).
                
                2. **The Meat**: Actionable advice or a counter-intuitive take. NO FLUFF.

                3. **The Engagement**: A genuine question.

            - **Style**: 
                - If Tone is 'Professional': Clean, crisp, authoritative.
                - If Tone is 'Funky'/'Creative': Use slang, lower case starts, punchy fragments, maybe 1-2 shocking emojis.
                - If Tone is 'Edgy': Be polarizing. "Most people are wrong about X".
            
            - **Formatting**: Short paragraphs. "Bro-etry" spacing ONLY if it aids readability, not just for length.

            - **CONSTRAINTS (STRICT)**:
                - **Length**: MUST be between 1300 and 1500 characters. No more, no less.
                - **Emojis**: Use exactly 3 to 5 emojis. (e.g., 🚀, ✅, 📈). Do not use more.
                - **Tone**: Defaults to "Human-to-Human" conversational interaction. Sound like a real person sharing insights, not a corporate bot.

            """

             structure_prompt = "Outline 3 potential Hooks (Choose the weirdest/best one). Then outline the main value argument."



        elif asset_type == "LinkedIn Carousel (PDF/Images)":

             format_guidelines = """

            - **Format**: Carousel Script (Markdown Table).

            - **Structure**: 5 to 8 Slides MAX.

            - **Columns**:
                1. **Slide #**: (1-8)
                2. **Visual Prompt**: What should be on the slide image (Minimal text, icons, colors).
                3. **Text Overlay**: Big, punchy text for the slide (Max 10 words).
                4. **Speaker Notes/Caption**: The detailed explanation for the post caption.

            - **Flow**:
                - Slide 1: Hook / Title.
                - Slide 2: The Problem.
                - Slide 3-6: The Solution / Steps.
                - Slide 7: Proof/Outcome.
                - Slide 8: CTA.

            """

             structure_prompt = "Outline the Carousel Arc: Hook -> Agitation -> 3-Step Solution -> CTA."





        elif asset_type == "Twitter/X Thread (Viral)":

             format_guidelines = """

            - **Format**: Twitter/X Thread (1/N).

            - **Components**:

                1. **Tweet 1 (The Hook)**: Aggressive or curiosity-inducing hook.

                2. **Body Tweets**: Value breakdown.

                3. **Final Tweet**: Summary + Call to Action.

            - **Style**: Casual, conversational, internet-native slang allowed, high emoji usage, rapid fire.

            """

             structure_prompt = "Outline the Thread Flow: The Hook, The Value Steps, and The CTA."



        elif asset_type == "WhatsApp/SMS Message (Direct)":

             format_guidelines = """

            - **Format**: Direct Message / SMS / WhatsApp.

            - **Components**:

                1. **The Greeting**: Personal and short.

                2. **The Nudge**: High-value offer or update.

                3. **The Call to Action**: Click link or Reply.

            - **Length**: MAX 3-4 sentences.

            - **Style**: Extremely personal, high-urgency, conversational (like a friend).

            """

             structure_prompt = "Draft the single most effective high-intent message."



        elif asset_type == "Social Media Post":

             # Legacy Fallback

             format_guidelines = """

            - **Format**: Social Media Caption + Visual Concept.

            - **Components**:

                1. The Hook (First line).

                2. Value Body (The meat).

                3. Engagement Ask (CTA).

                4. Hashtags.

                5. Visual Description (What image/video goes with this?).

            """

             structure_prompt = "Outline the Social Angle: The Hook and the Core Value Prop."

             

        else: # Blog, Whitepaper, etc.

            format_guidelines = f"""

            - **Format**: Standard {asset_type} (Markdown).

            - **Structure**: H1 Title, Introduction, H2 Subheaders, Conclusion.

            """

            structure_prompt = f"Outline the structure using a framework (like PAS - Pain, Agitate, Solution) suitable for a {asset_type}."



        # --- Step 1: The Strategist (Outline & Angle) ---

        strategy_prompt = f'''

        You are a Senior Content Strategist. Plan a {asset_type} for the campaign "{campaign_context.get('name')}".

        

        DUAL-OBJECTIVE CONTEXT:

        1. TACTICAL GOAL (This Asset): {campaign_context.get('goal')}

        2. STRATEGIC GOAL (Campaign): {campaign_context.get('parent_goal', 'Increase Brand Awareness')}

        

        THEME & VIBE:

        - Topic: {theme}

        - Campaign Vibe: {campaign_context.get('parent_theme', '')}

        

        Context:

        {persona_context}

        {voice_instruction}

        {archetype_instruction}

        {narrative_instruction}
        
        {vocabulary_instruction}

        {visual_tone_instruction}

        {tone_override}
        
        {quality_rules}

        {funnel_instruction}

        {seo_instruction}

        

        Brand Knowledge (TRUTH SOURCE):

        {kg_str}
        **CRITICAL:** You must ONLY reference products/features found in the Brand Knowledge above. Do not hallucinate features.

        

        Brand Source:

        {content[:20000]}

        

        TASK:

        Do not write the asset yet. Create a STRATEGIC OUTLINE.

        1. Identify a "Counter-Intuitive Insight" or specific "Angle" that creates immediate interest.

        2. {structure_prompt}

        3. List the key points for each section.

        

        Output: Detailed Outline.

        '''

        outline = generate_gemini_response(strategy_prompt, model_name=model_name, temperature=0.7)

        

        # Error Check: If outline extraction failed or returned an API error

        if not outline or "error" in outline.lower() or len(outline) < 20: 

             return "Error: Failed to generate strategic outline. Please try again or use a different model."



        # --- Step 2: The Drafter (Writing) ---

        draft_prompt = f'''

        You are a Lead Copywriter. Write the FULL DRAFT of the {asset_type} based on this outline.

        

        STRATEGIC OUTLINE:

        {outline}

        

        REQUIREMENTS:

        {format_guidelines}

        

        TONE & STYLE:

        - Write in the voice of a deep subject matter expert.

        - No fluff, no ChatGPT-isms (like "In today's digital landscape").

        - Use short, punchy sentences interspersed with rhythm.

        - {tone_instruction}

        

        {voice_instruction}
        
        {vocabulary_instruction}

        {funnel_instruction}

        {visual_tone_instruction}

        

        DRAFT:

        '''

        draft = generate_gemini_response(draft_prompt, model_name=model_name, temperature=0.7)



        # Error Check: If draft failed

        if not draft or "error" in draft.lower() or len(draft) < 20:

             return "Error: Failed to generate draft content."



        # --- Step 3: The Polisher (Refining) ---

        polish_prompt = f'''

        You are an Editor-in-Chief. Polish this draft to perfection.

        

        DRAFT:

        {draft}

        

        TASK:

        - Fix any awkward phrasing.

        - Ensure the hook is irresistible.

        - Verify meaningful use of SEO keywords: {seo_keywords if seo_keywords else "N/A"}.

        - Format perfectly in Markdown.

        

        CRITICAL FORMATTING CHECK:

        {format_guidelines}

        

        OUTPUT: Final Polished Markdown Asset.

        '''

        final_asset = generate_gemini_response(polish_prompt, model_name=model_name, temperature=0.7)

        

        return final_asset

    except Exception as e:

        return f"Error generating campaign asset: {e}"



def repurpose_content(content, target_format, platform="Social Media", model_name=GEMINI_3_PRO_PREVIEW, temperature=0.7, tone_instruction="", persona_details=None, brand_voice_desc="", seo_keywords=None):

    """

    Repurposes existing content into a new format for a specific platform.

    """

    try:

        # Context Construction

        persona_context = ""

        if persona_details:

            role = persona_details.get('role', 'General Audience')

            persona_context = f"Target Audience: {role}. {tone_instruction}"

            

        voice_instruction = ""

        if brand_voice_desc:

            voice_instruction = f"STRICT BRAND VOICE: '{brand_voice_desc}'. Do not deviate."

            

        seo_instruction = ""

        if seo_keywords:

            seo_instruction = f"MUST integrate these AEO Keywords naturally: {', '.join(seo_keywords)}"



        prompt = f'''

        You are a Content Repurposing Specialist.

        Take the following content and repurpose it into a {target_format} for {platform}.

        

        Source Content:

        {content[:20000]}

        

        STRATEGIC CONTEXT:

        {persona_context}

        {voice_instruction}

        {seo_instruction}

        

        Constraints:

        - Optimize for {platform}'s best practices (e.g. hashtags for Twitter, professional token for LinkedIn).

        - Maintain the core message but adapt the tone.

        - Format appropriate for the platform (Markdown).
        
        STYLING RULES (CRITICAL):
        - Do NOT use HTML tags (like <p>, <div>, <span>) for styling. 
        - Use standard Markdown exclusively.
        '''

        return generate_gemini_response(prompt, model_name=model_name, temperature=temperature)

    except Exception as e:

        return f"Error repurposing content: {e}"



def generate_counter_messaging(my_brand_content, competitor_content, model_name=GEMINI_3_PRO_PREVIEW):

    """

    Generates messaging to counter a competitor.

    """

    try:

        prompt = f'''

        You are a Competitive Strategy Expert.

        Develop specific "Counter-Messaging" to position our brand against this competitor.

        

        Our Brand:

        {my_brand_content[:10000]}

        

        Competitor Brand:

        {competitor_content[:10000]}

        

        Task:

        1. Identify the competitor's main weakness or gap.

        2. Write 3 distinct messaging angles that exploit this weakness.

        

        Output JSON:

        [

            {{ "angle": "Angle Name", "message": "The actual copy...", "rationale": "Why this works" }}

        ]

        '''

        response = generate_gemini_response(prompt, model_name=model_name)

        return parse_json_response(response)

    except Exception as e:

        return [{"angle": "Error", "message": str(e), "rationale": "Failed to generate"}]



def generate_image_prompt(content, asset_type, style="Modern", creativity="Balanced", persona_details=None, model_name=GEMINI_3_PRO_PREVIEW, visual_identity=None):

    """

    Generates a detailed image generation prompt based on content, style, and target audience.
    
    [UPDATED] Now includes Asset Type logic and Visual DNA enforcement.

    """

    try:

        persona_ctx = f"Target Audience: {persona_details.get('role', 'General')}" if persona_details else ""

        # [NEW] Visual DNA Construction (The "Nanobanana" Lock)
        visual_dna_instruction = ""
        if visual_identity:
             v_vibe = visual_identity.get('visual_vibe', 'Modern & Professional')
             v_palette = visual_identity.get('primary_palette', [])
             
             # Force specific colors if available
             color_instruction = ""
             if v_palette:
                 color_instruction = f"DOMAIN PALETTE: Use the brand's primary colors: {', '.join(v_palette)}. These are non-negotiable."
             
             visual_dna_instruction = f"""
             **VISUAL DNA (STRICT):**
             - Brand Vibe: {v_vibe}
             - {color_instruction}
             - Sentiment: {visual_identity.get('image_sentiment', 'Trustworthy')}
             """
        
        # [NEW] Asset Type Specific Logic
        asset_instruction = ""
        if asset_type == "Blog Post":
            asset_instruction = "Generate a prompt for a **Wide Landscape (16:9) Hero Image**. Stick to 'Editorial Illustration' or 'Abstract Tech Photography' style. No text."
        elif asset_type == "Whitepaper":
             asset_instruction = "Generate a prompt for a **Vertical (3:4) PDF Cover**. Minimalist, title-safe composition. Abstract 3D shapes or high-end photography."
        elif asset_type == "Case Study":
             asset_instruction = "Generate a prompt for a **Corporate Success Feature Image**. Shows confident professionals (diverse) in a modern office, or an abstract representation of 'Growth'."
        elif asset_type in ["Instagram Post (Visual)", "TikTok/Reels Script"]:
             asset_instruction = "Generate a prompt for a **Vertical (9:16) Full-Screen Visual**. Highly engaging, vibrant, 'Stop-the-Scroll' quality."
        else:
             asset_instruction = "Generate a balanced, professional image suitable for marketing materials."


        prompt = f'''

        Create a detailed, high-quality AI image generation prompt (for Imagen 3 / Midjourney) 
        that would create a perfect visual accompaniment for this asset.

        
        CONTEXT:
        - Asset Type: {asset_type}
        - Content Theme: {content[:3000]}
        - Visual Style: {style}
        - Creativity: {creativity}
        {persona_ctx}

        
        INSTRUCTIONS:
        1. **{asset_instruction}**
        2. {visual_dna_instruction}
        3. Be highly descriptive about lighting (e.g. "Cinematic lighting", "Soft diffused studio light"), texture, and composition.
        4. If the style is "Modern", lean towards minimal, geometric, or tech-forward aesthetics.
        5. **NO TEXT**: Inspect the prompt to ensure it doesn't ask for specific text, as AI struggles with text rendering. Focus on the VISUALS.
        

        Output: Just the prompt text. No markdown.

        '''

        return generate_gemini_response(prompt, model_name=model_name)

    except Exception as e:

        return f"Error generating prompt: {e}"



def generate_image_asset(prompt, model_name="models/imagen-4.0-fast-generate-001", api_key=None, brand_color="667eea", aspect_ratio="16:9"):
    """
    Generates a REAL image using Google GenAI Imagen 3.
    Returns a Base64 encoded string ready for HTML display.
    """
    try:
        if not api_key:
             api_key = os.getenv("GEMINI_API_KEY") # Use Gemini Key for Imagen
             
        if not api_key:
            return "https://placehold.co/800x400/e2e8f0/475569/png?text=API+Key+Missing"

        client = genai.Client(api_key=api_key)
        
        # Determine aspect ratio
        ar = "16:9" # Default
        if "Instagram" in prompt or "TikTok" in prompt or "Story" in prompt:
            ar = "9:16"

        elif "Square" in prompt or "Post" in prompt:
            ar = "1:1"
            
        print(f"Generating Image with {model_name}... Prompt len: {len(prompt)}")
        
        try:
            response = client.models.generate_images(
                model=model_name,
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio=ar,
                    safety_filter_level="BLOCK_ONLY_HIGH",
                    person_generation="ALLOW_ADULT", 
                )
            )
        except Exception as e:
            # Fallback Logic - Waterfall Strategy
            print(f"Primary ({model_name}) failed: {e}")
            
            # 1. Try Imagen 3 Standard
            try:
                print("Falling back to 'models/imagen-3.0-generate-001'...")
                response = client.models.generate_images(
                    model='models/imagen-3.0-generate-001',
                    prompt=prompt,
                        config=types.GenerateImagesConfig(
                        number_of_images=1,
                        aspect_ratio=ar,
                        safety_filter_level="BLOCK_ONLY_HIGH",
                        person_generation="ALLOW_ADULT", 
                    )
                )
            except Exception as e2:
                # 2. Try Imagen 2 (Legacy)
                print(f"Imagen 3 failed. Falling back to 'models/image-generation-001'...")
                try:
                    response = client.models.generate_images(
                        model='models/image-generation-001',
                        prompt=prompt,
                        config=types.GenerateImagesConfig(
                            number_of_images=1,
                            aspect_ratio=ar
                        )
                    )
                except Exception as e3:
                     print(f"All image models failed. Error: {e3}")
                     raise e3
        
        if response.generated_images:
            img = response.generated_images[0]
            if img.image.image_bytes:
                import base64
                b64_data = base64.b64encode(img.image.image_bytes).decode('utf-8')
                mime_type = "image/png" # Imagen returns PNG usually
                return f"data:{mime_type};base64,{b64_data}"
                
        return "https://placehold.co/800x400/e2e8f0/475569/png?text=Image+Generation+Failed"

    except Exception as e:
        print(f"Imagen Error: {e}")
        # Fallback to placeholder if quota exceeded or error
        return f"https://placehold.co/800x400/e2e8f0/475569/png?text=Error:+{str(e)[:20]}"



def run_hybrid_seo_audit(content, brand_name, model_name=GEMINI_3_PRO_PREVIEW):

    """

    Performs a Hybrid Search Audit (Traditional SEO + AEO Simulation).

    """

    try:

        prompt = f'''

        You are a **Hybrid Search Engine Algorithm Simulator** (Google + Perplexity + ChatGPT).

        

        **OBJECTIVE:**

        Analyze the specific webpage content below and simulate how both Traditional Search Engines (SEO) and AI Answer Engines (AEO) perceive it.

        Then, generate strategic fixes.

        

        **BRAND CONTEXT:**

        Brand Name: "{brand_name}"

        

            "organic_health": {{

                "branded_presence": {{ "status": "Pass", "rationale": "Brand name found in H1." }},

                "category_ownership": {{ 

                    "top_keywords_found": ["Cloud", "SaaS"],

                    "keywords_in_h1": [],

                    "status": "Miss",

                    "rationale": "H1 'Welcome to Future' fails to mention 'Cloud'."

                }},

                "meta_health": {{ "score": 75, "critique": "Title is optimized but H1 is weak. It dilutes the keyword X." }}

            }},

            "aeo_simulation": {{

                "before_definition": "A generic software provider...",

                "after_definition": "The leading Cloud Security Platform for...",

                "confusion_analysis": {{

                    "root_cause_element": "H1 Tag",

                    "current_text": "Welcome to the Future",

                    "missing_signal": "Category Keyword 'Cloud Security'",

                    "reasoning": "Because the H1 is vague, the AI defaults to generic classification.",

                    "dev_action": "Update H1 to include 'Cloud Security'."

                }}

            }},

            "fixes": {{

                "original_headline_found": "Welcome to our website",

                "variants": [

                    {{ 

                        "name": "Technical & Feature-Focused", 

                        "headline": "...", 

                        "subheadline": "...", 

                        "meta_tags": {{ "keyword": "Zero Trust", "hook": "Security", "persona": "CTO" }},

                        "rationale": "..." 

                    }},

                    {{ 

                        "name": "Business Value & ROI", 

                        "headline": "...", 

                        "subheadline": "...", 

                        "meta_tags": {{ "keyword": "Cost Savings", "hook": "Efficiency", "persona": "CFO" }},

                        "rationale": "..." 

                    }},

                    {{ 

                        "name": "AI-Optimized", 

                        "headline": "...", 

                        "subheadline": "...", 

                        "meta_tags": {{ "keyword": "Platform Definition", "hook": "Clarity", "persona": "AI Agent" }},

                        "rationale": "..." 

                    }}

                ],

                "json_ld": "{{ ... }}"

            }}

        }}

        '''

        

        return generate_gemini_response(prompt, model_name=model_name)

    except Exception as e:

        return f'{{"error": "{str(e)}"}}'



def simulate_variant_impact(variant_headline, variant_subheadline, brand_name, model_name=GEMINI_3_FLASH):

    """

    Runs a micro-simulation to predict how a specific content variation impacts AEO visibility.

    """

    try:

        prompt = f'''

        You are an **AEO (Answer Engine Optimization) Algorithm Simulator**.

        

        **TASK:**

        We are testing a specific change to a brand's Hero Section (Homepage). 

        Predict how this change affects how AI Assistants (ChatGPT, Gemini, Perplexity) perceive and rank the brand.

        

        **BRAND:** {brand_name}

        

        **NEW CONTENT VARIANT:**

        - **Headline:** "{variant_headline}"

        - **Subheadline:** "{variant_subheadline}"

        

        **ANALYZE & PREDICT:**

        1. **AI Perception**: How would an AI summarize the brand based ONLY on this new text? (1 sentence).

        2. **Why it Works (or Fails)**: Identify specific keywords, intent-signals, or clarity improvements in the text.

        3. **Predicted Impact**: "High", "Medium", or "Low" (Probability of ranking for non-branded category keywords).

        

        **OUTPUT JSON:**

        {{

            "aeo_perception": "The brand is now clearly defined as a [Category Leader] for [Target Audience]...",

            "why_it_works": "The use of '[Keyword]' directly answers the commercial intent query 'Best way to...'",

            "predicted_impact": "High"

        }}

        '''

        

        response = generate_gemini_response(prompt, model_name=model_name)

        return parse_json_response(response)

        

    except Exception as e:

        return {"error": str(e), "aeo_perception": "Error simulating impact.", "predicted_impact": "Unknown"}





def suggest_aeo_keywords(brand_content, brand_dna, personas=None, model_name=GEMINI_3_FLASH):

    """

    Suggests high-impact AEO/SEO keywords based on brand DNA and personas.

    Used as a fallback for users who haven't run a full analysis.

    """

    try:

        personas_context = f"Target Personas: {json.dumps(personas)}" if personas else ""

        

        prompt = f'''

        You are an AEO (AI Engine Optimization) Strategist. 

        Based on the Brand DNA and content below, suggest 5 high-impact, commercial-intent keywords or phrases.

        These keywords should be designed to make this brand appear in AI-generated answers (like ChatGPT/Perplexity).

        

        Brand DNA:

        {json.dumps(brand_dna)}

        

        {personas_context}

        

        Brand Content Snippet:

        {brand_content[:10000]}

        

        Output format: Just a comma-separated list of 5 keywords/phrases. No other text.

        Example: "low-code sms api, affordable customer engagement, twilio alternatives, secure messaging platform, developer communication tools"

        '''

        

        response = generate_gemini_response(prompt, model_name=model_name)

        if response and "error" not in response.lower():

            # Clean up response to ensure it's just comma separated

            keywords = [k.strip() for k in response.split(",") if k.strip()]

            return keywords[:5]

        return []

    except Exception as e:

        print(f"Error suggesting keywords: {e}")

        return []



def generate_social_card_html(theme, brand_style="Modern", model_name=GEMINI_3_FLASH):

    """

    Generates a beautiful HTML/CSS Social Media Card (OG Image style) for a given theme.

    Useful for visualizing how the content would look when shared.

    """

    try:

        prompt = f'''

        You are a UI Design Expert.

        Create a single HTML file containing a beautiful 1200x630px container (Social Media Card / OpenGraph Image).

        

        **CONTENT THEME:** "{theme}"

        **BRAND STYLE:** "{brand_style}"

        

        **Instructions:**

        1. create a `div` with class "card".

        2. Use **Inline CSS** for everything. Make it look premium, modern, and aligned with the brand style.

        3. Include a gradient background or stylish pattern.

        4. Include a catchy Headline based on the theme.

        5. Include a "Read More" or "Brand Name" footer.

        6. Dimensions should be responsive but max-width 600px for the preview (aspect ratio 1.91:1).

        

        **Output:** Just the HTML code for the card `div`, no ```html blocks.

        '''

        response = generate_gemini_response(prompt, model_name=model_name)

        return clean_html_response(response)

    except Exception as e:

        return f"<div style='padding:20px; background:red; color:white'>Error generating card: {e}</div>"



def generate_instagram_carousel_html(content, brand_style="Modern", brand_colors=None, model_name=GEMINI_3_FLASH):

    """

    Generates a High-Fidelity HTML/CSS representation of an Instagram Carousel.

    """

    try:

        colors_css = ""

        if brand_colors and isinstance(brand_colors, list):

            colors_css = f"Primary: {brand_colors[0]}, Secondary: {brand_colors[1] if len(brand_colors)>1 else '#333'}"

        

        prompt = f'''

        You are a Senior Visual Designer.

        Create a High-Fidelity HTML/CSS preview for an Instagram Carousel (5 Slides) based on the content below.

        

        **CONTENT SOURCE:**

        {content[:10000]}

        

        **DESIGN DNA:**

        - Style: {brand_style}

        - Brand Colors: {colors_css}

        

        **TECHNICAL REQUIREMENTS (CRITICAL):**

        1. **Container**: Use `display: flex; overflow-x: auto; gap: 1rem; padding: 1rem; scroll-snap-type: x mandatory;`.

           - The container MUST allow horizontal scrolling.

        2. **Slides**: 5 Slides. Each slide MUST have `flex: 0 0 320px; width: 320px; height: 400px; scroll-snap-align: center;`.

           - **IMPORTANT**: Do not let them shrink. They must be side-by-side.

        3. **Styling**:

           - Use **Inline CSS** for EVERYTHING.

           - Use gradients, shadows, and modern typography (Inter/Roboto).

           - Slide 1: Hook/Title (Big Bold Text).

           - Slide 2-4: Value/Education (Bullet points / Diagrams).

           - Slide 5: Call to Action.

           - **Visuals**: Use CSS shapes (circles, gradients) to make it look premium.

        

        **OUTPUT:** 

        Return ONLY the Raw HTML string for the container `div`. No markdown fences.

        '''

        response = generate_gemini_response(prompt, model_name=model_name)

        return clean_html_response(response)

    except Exception as e:

         return f"<div>Error generating carousel: {e}</div>"



def generate_visual_html_asset(asset_type, content, brand_data, model_name=GEMINI_3_FLASH):

    """

    Router for generating specific visual HTML assets.

    """

    brand_style = brand_data.get("analysis", {}).get("visual_style_inference", "Modern & Professional")

    brand_colors = brand_data.get("knowledge_graph", {}).get("brand_colors", ["#000000", "#ffffff"])

    

    if "Instagram" in asset_type:

        return generate_instagram_carousel_html(content, brand_style, brand_colors, model_name)

    elif "LinkedIn" in asset_type or "Social" in asset_type:

        return generate_social_card_html(content, brand_style=brand_style, model_name=model_name)

    elif asset_type == "Cold Email (Outreach)":
        # Strict No-Op for Cold Email - No visuals needed
        return None

    elif asset_type == "Landing Page Copy":

        # Extract HTML from the markdown content if present

        import re

        html_match = re.search(r"```html\s*(.*?)\s*```", content, re.DOTALL)

        if html_match:

            return html_match.group(1)

        else:

            # Fallback: Generate a preview if no code block found

            return generate_growth_asset(content, "Landing Page Preview", "Visual Mockup", brand_style=brand_style, model_name=model_name)

    

    return None


def merge_brand_insights(existing_data, new_data, new_source, model_name=GEMINI_3_PRO_PREVIEW):
    """
    Intelligently merges new brand insights with an existing profile.
    Used when scanning multiple pages to build a cumulative "Master Profile".
    """
    try:
        prompt = f'''
        You are a **Strategic Brand Archivist**.
        
        **OBJECTIVE:**
        We have an **Existing Brand Profile** and we just scanned a **New Page** ({new_source}).
        Merge the new insights into the existing profile to create an UPDATED Master Profile.
        
        **EXISTING PROFILE:**
        {json.dumps(existing_data)[:50000]}
        
        **NEW FINDINGS (from {new_source}):**
        {json.dumps(new_data)[:50000]}
        
        **MERGE RULES:**
        1. **Augment, Don't Overwrite**: If the new data contains specific details (e.g., specific pricing models, new features) that were missing, ADD them.
        2. **Conflict Resolution**: If there is a direct conflict (e.g., Vision Statement), use the version that sounds more specific and authoritative.
        3. **Personas**: If new personas are found, add them. If similar ones exist, merge their pain points.
        4. **Visuals**: Refine the visual identity if the new page provided better color codes.
        
        **OUTPUT FORMAT:**
        Return the exact same JSON structure as the inputs (keys: analysis, personas, strategy).
        '''
        
        return generate_gemini_response(prompt, model_name=model_name)
    except Exception as e:
        return json.dumps(existing_data) # Fallback: Return original state


def generate_aeo_strategy(leaderboard_data, opportunity_urls, brand_name, focus_intents=None, model_name=GEMINI_3_PRO_PREVIEW):
    """
    Generates actionable strategic recommendations to improve AEO performance.
    
    Args:
        leaderboard_data (list): List of competitor rankings and stats.
        opportunity_urls (list): List of domains where competitors are cited but user is not.
        brand_name (str): Name of the user's brand.
        focus_intents (list): List of intents selected by the user (e.g. ['Commercial', 'Transactional']).
        model_name (str): AI model to use.
    
    Returns:
        str: JSON string containing the strategy playbook.
    """
    try:
        intent_context = ""
        if focus_intents:
            intent_context = f"**FOCUS INTENTS:** {', '.join(focus_intents)}\n        **CRITICAL:** IGNORE low scores for intents NOT listed above. Only optimize for the selected intents."

        prompt = f'''
        You are an **AEO (Answer Engine Optimization) Strategist**.
        
        **CONTEXT:**
        We have analyzed the "AI Market Share" for the brand: **{brand_name}**.
        
        {intent_context}
        
        **DATA:**
        1. **Leaderboard** (Who is winning):
        {json.dumps(leaderboard_data[:5])}
        
        2. **Opportunity Gaps** (Where winners are cited, but we are NOT):
        {json.dumps(opportunity_urls[:5])}
        
        **OBJECTIVE:**
        Generate a "Strategic Playbook" to help {brand_name} climb the rankings.
        
        **CRITICAL NEW LOGIC: COMPETITOR DISPLACEMENT**
        - Look at the "competitor_reliance_score" in the Leaderboard.
        - If {brand_name} (or a target competitor) has a HIGH score, it means **they are being defined by their competitors**.
        - **STRATEGY:** "Competitor Displacement". Identify WHICH competitor page is being cited, and write a better version of that page on {brand_name}'s site to "steal" the citation.
        
        **RULES:**
        1. **CITATION PROVENANCE:** Do NOT recommend getting citations from domains that appear to be direct competitors or the brand itself. Focus on NEUTRAL third-party authorities (e.g. TechTech, G2, Capterra, News Sites).
        2. **INTENT ALIGNMENT:** If the user selected 'Commercial', do NOT tell them to write 'What is' definitions (Informational). Tell them to win comparisons.
        
        **OUTPUT FORMAT (JSON):**
        {{
            "headline_strategy": "A punchy, 3-5 word name for the overall strategy (e.g. 'The Wikipedia Blitz' or 'Authority Borrowing').",
            "executive_summary": "2-sent summary. If reliance is high, mention 'We need to displace competitor citations'.",
            "citation_health_check": {{
                "status": "Safe/Vulnerable",
                "message": "You are currently relying on [Competitor Name] for X% of your visibility. This is risky." (Only if reliance > 10%)
            }},
            "top_3_actions": [
                {{
                    "title": "Action Title (e.g. Displace Competitor X)",
                    "description": "Specific instruction. If displacing, say: 'Create a page that defines [Topic] better than [Competitor URL]'.",
                    "impact": "High/Medium/Low",
                    "difficulty": "Easy/Hard"
                }}
            ],
            "content_pivot": "What specific type of content should they produce? (e.g. 'More comparison tables', 'Clear definitions').",
            "citation_targets": ["Domain 1", "Domain 2"]
        }}
        '''
        
        return generate_gemini_response(prompt, model_name=model_name)
    except Exception as e:
        return json.dumps({"error": str(e)})


def analyze_entity_density(content, target_keywords=None, model_name=GEMINI_3_FLASH):
    """
    Analyzes the density and coverage of key entities/concepts in the content.
    Crucial for AEO/GEO to ensure the AI understands the topic depth.
    """
    try:
        keywords_str = ", ".join(target_keywords) if target_keywords else "General Industry Terms"
        
        prompt = f'''
        You are a Semantic SEO Analyst. Analyze the text below for "Entity Density".
        
        TARGET ENTITIES/TOPICS: {keywords_str}
        
        TEXT TO ANALYZE:
        {content[:15000]}
        
        YOUR TASK:
        1. Identify which important entities/concepts are MISSING or weakly covered.
        2. Identify which entities are well-covered.
        3. Assign an "Entity Density Score" (0-100) based on topical depth.
        
        Output JSON format:
        {{
            "score": 75,
            "missing_entities": ["Term A", "Term B"],
            "strong_entities": ["Term C", "Term D"],
            "analysis": "Brief explanation of the gap."
        }}
        '''
        response = generate_gemini_response(prompt, model_name=model_name)
        return parse_json_response(response)
    except Exception as e:
        return {"error": str(e), "score": 0}

def score_trust_signals(content, model_name=GEMINI_3_FLASH):
    """
    Evaluates content for "Trust Signals" favored by AEO engines (e.g. Citations, Data, Expert Tone).
    """
    try:
        prompt = f'''
        You are a Trust & Credibility Auditor for AI Search Engines.
        Analyze the text below for TRUST SIGNALS.
        
        TEXT:
        {content[:15000]}
        
        CRITERIA:
        - specific data/statistics (not just "many")
        - citations/sources
        - first-person expertise ("I", "We tested")
        - lack of fluff
        
        Output JSON format:
        {{
            "score": 60,
            "issues": ["Lack of specific data points", "No external citations"],
            "positive_signals": ["Good usage of 'We found'"],
            "improvement_tip": "Add a statistic about X."
        }}
        '''
        response = generate_gemini_response(prompt, model_name=model_name)
        return parse_json_response(response)
    except Exception as e:
        return {"error": str(e), "score": 0}

def simulate_geo_impact(original_text, new_text, target_keyword, model_name=GEMINI_3_PRO_PREVIEW):
    """
    Simulates the "Before vs After" impact of content changes on AI perception.
    Used in the GEO Lab Playground.
    """
    try:
        prompt = f'''
        You are an AI Search Engine Simulator (like a hybrid of Google and Perplexity).
        
        I will show you ORIGINAL content and NEW (modified) content.
        Target Query: "{target_keyword}"
        
        ORIGINAL CONTENT:
        {original_text[:10000]}
        
        NEW CONTENT:
        {new_text[:10000]}
        
        Evaluate the CHANGE within the context of the Target Query.
        Did the new content improve "Answerability", "Authority", and "Trust"?
        
        Output JSON format:
        {{
            "impact_score": 85 (0-100, where 50 is no change, >50 is improvement),
            "before_perception": "How you viewed the original (e.g. 'Vague, promotional')",
            "after_perception": "How you view the new one (e.g. 'Authoritative, data-rich')",
            "key_improvements": ["Added specific pricing data", "Removed fluff"],
            "remaining_gaps": ["Still lacks a direct definition"]
        }}
        '''
        response = generate_gemini_response(prompt, model_name=model_name)
        return parse_json_response(response)
    except Exception as e:
        return {"error": str(e)}
