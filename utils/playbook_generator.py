"""
Brand Playbook Generator
Generates a comprehensive Markdown document containing all brand intelligence.
"""

def generate_brand_playbook(brand_data):
    """
    Generates a full Brand Playbook in Markdown format.
    """
    if not brand_data:
        return "# Error: No Brand Data Found"
        
    name = brand_data.get("brand_name", "Unknown Brand")
    analysis = brand_data.get("analysis", {})
    personas = brand_data.get("personas", [])
    strategic = brand_data.get("strategic", {})
    knowledge_graph = brand_data.get("knowledge_graph", {})
    design_tokens = brand_data.get("design_tokens", {})
    imagery = brand_data.get("brand_imagery", {})
    
    md = f"# 📖 Brand Playbook: {name}\n\n"
    md += f"Generated on: {brand_data.get('scraped_at', 'N/A')}\n\n"
    
    # 1. Executive Summary
    md += "## 🎯 Executive Summary\n"
    md += f"**Core Identity:** {analysis.get('brand_category', 'N/A')}\n\n"
    md += f"**Mission/Value Prop:** {analysis.get('value_proposition', 'N/A')}\n\n"
    
    # 2. Brand DNA
    md += "## 🧬 Brand DNA\n"
    md += "### Core Values\n"
    for value in analysis.get('brand_values', []):
        md += f"- {value}\n"
    md += "\n"
    
    md += "### Brand Personality\n"
    md += f"{analysis.get('brand_personality', 'N/A')}\n\n"
    
    # 3. Target Personas
    md += "## 👥 Target Personas\n"
    for p in personas:
        md += f"### {p.get('role', 'Unknown')}\n"
        md += f"**Archetype:** {p.get('archetype', 'N/A')}\n\n"
        md += "**Pain Points:**\n"
        for pp in p.get('pain_points', []):
            md += f"- {pp}\n"
        md += "\n**Goals:**\n"
        for g in p.get('goals', []):
            md += f"- {g}\n"
        md += "\n"
        
    # 4. Design System
    md += "## 🎨 Design System\n"
    if imagery.get('logo'):
        md += f"![Logo]({imagery['logo']})\n\n"
        
    md += "### Brand Colors\n"
    if design_tokens.get('colors'):
        for cat, colors in design_tokens['colors'].items():
            md += f"**{cat.capitalize()}:** {', '.join(colors)}\n\n"
    else:
        md += "Not extracted yet.\n\n"
        
    md += "### Typography\n"
    if design_tokens.get('fonts'):
        md += f"- {', '.join(design_tokens['fonts'])}\n\n"
        
    # 5. Strategic Insights
    md += "## 📈 Strategic Insights\n"
    md += "### Content Pillars\n"
    for pillar in strategic.get('content_pillars', []):
        md += f"- {pillar}\n"
    md += "\n"
    
    md += "### Technical Strategy (AEO)\n"
    md += f"{strategic.get('aeo_strategy', 'N/A')}\n\n"
    
    # 6. Knowledge Graph (Products)
    md += "## 🧠 Knowledge Graph\n"
    if knowledge_graph.get('products'):
        for prod in knowledge_graph['products']:
            md += f"### {prod.get('name')}\n"
            md += f"**Features:** {', '.join(prod.get('features', []))}\n\n"
            md += f"**Benefits:** {', '.join(prod.get('benefits', []))}\n\n"
            
    return md
