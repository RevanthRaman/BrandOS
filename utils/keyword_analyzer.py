"""
Keyword Gap Analyzer
AI-driven competitive keyword gap analysis without requiring paid API access.
"""

import json


def analyze_keyword_gap_ai(brand_content, competitor_content, model_name):
    """
    AI-inferred keyword gap analysis.
    Compares brand content vs competitor content to identify keyword opportunities.
    
    Args:
        brand_content: Your brand's website content
        competitor_content: Competitor's website content
        model_name: Gemini model to use
    
    Returns:
        Dict with keyword gap analysis
    """
    from utils.ai_engine import generate_gemini_response, parse_json_response
    
    try:
        prompt = f"""
        You are a Competitive SEO Analyst. Perform a keyword gap analysis by comparing two brands.
        
        **MY BRAND CONTENT:**
        {brand_content[:15000]}
        
        **COMPETITOR CONTENT:**
        {competitor_content[:15000]}
        
        **YOUR TASK:**
        Identify keywords and topics that the competitor emphasizes heavily but our brand underutilizes.
        Focus on keywords that represent real business value (not just filler words).
        
        **Output JSON format:**
        {{
            "gap_keywords": [
                {{
                    "keyword": "specific keyword phrase",
                    "competitor_emphasis": "High/Medium/Low - How strongly competitor focuses on this",
                    "our_coverage": "High/Medium/Low - Our current coverage",
                    "opportunity_score": 0-100 (based on: competitor strength + our gap + relevance),
                    "topic_category": "e.g., Product Feature, Use Case, Industry Term",
                    "rationale": "Why this keyword represents an opportunity for us",
                    "suggested_action": "Specific tactical recommendation (e.g., 'Add dedicated section on homepage', 'Create FAQ entry')",
                    "implementation_effort": "Low/Medium/High"
                }}
            ],
            "strategic_insights": {{
                "biggest_content_gap": "The single largest topical gap we have vs competitor",
                "quick_wins": ["Keyword we could easily add", "Another easy addition"],
                "long_term_opportunities": ["Strategic keyword requiring new content", "Another strategic opportunity"]
            }},
            "methodology_note": "This analysis is AI-inferred based on content comparison. For precise search volume and difficulty data, consider integrating with SEO APIs like SEMrush or Ahrefs."
        }}
        
        **RULES:**
        - Focus on 5-10 high-quality keyword gaps, not 50 mediocre ones
        - Opportunity score should reflect: (competitor emphasis) * (our gap) * (business relevance)
        - Be specific with keywords (not just "security" but "enterprise data security compliance")
        - Suggested actions must be tactical and implementable
        """
        
        result = generate_gemini_response(prompt, model_name=model_name, temperature=0.4)
        gap_data = parse_json_response(result)
        
        if gap_data and "gap_keywords" in gap_data:
            # Sort by opportunity score
            gap_data["gap_keywords"] = sorted(
                gap_data["gap_keywords"],
                key=lambda x: x.get("opportunity_score", 0),
                reverse=True
            )
            return gap_data
        else:
            return {
                "gap_keywords": [],
                "strategic_insights": {
                    "biggest_content_gap": "Unable to analyze",
                    "quick_wins": [],
                    "long_term_opportunities": []
                },
                "methodology_note": "Analysis failed. Please try again."
            }
            
    except Exception as e:
        print(f"Keyword gap analysis error: {e}")
        return {
            "gap_keywords": [],
            "error": str(e)
        }


def prioritize_keywords_by_implementation(gap_keywords):
    """
    Re-sorts gap keywords by implementation effort vs opportunity score.
    Returns "quick wins" (high opportunity, low effort) first.
    """
    if not gap_keywords:
        return []
    
    # Score = opportunity_score / effort_weight
    # Effort: Low=1, Medium=2, High=3
    effort_map = {"low": 1, "medium": 2, "high": 3}
    
    for kw in gap_keywords:
        effort = kw.get("implementation_effort", "medium").lower()
        effort_weight = effort_map.get(effort, 2)
        opp_score = kw.get("opportunity_score", 50)
        
        # Quick win score: higher is better
        kw["quick_win_score"] = opp_score / effort_weight
    
    # Sort by quick win score
    return sorted(gap_keywords, key=lambda x: x.get("quick_win_score", 0), reverse=True)
