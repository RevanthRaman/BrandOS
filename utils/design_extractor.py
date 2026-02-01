"""
Design Token Extractor
Extracts brand design system (colors, fonts, spacing) from website HTML/CSS.
"""

import re
from collections import Counter
import json


def extract_design_tokens(html_content, url=""):
    """
    Extracts design tokens from HTML content.
    
    Args:
        html_content: Raw HTML string
        url: Website URL (for context)
    
    Returns:
        Dict with design tokens or empty dict if extraction fails
    """
    if not html_content:
        return {}
    
    try:
        # 1. Try to extract CSS variables first (Highest Confidence)
        css_vars = extract_css_variables(html_content)
        
        # 2. Extract and analyze all colors
        colors = extract_colors(html_content, css_vars)
        
        # 3. Extract fonts
        fonts = extract_fonts(html_content)
        
        # 4. Extract border radius
        border_radius = extract_border_radius(html_content)
        
        # 5. Detect color scheme
        color_scheme = detect_color_scheme(colors, html_content)
        
        # Build design token dict
        tokens = {}
        
        # Determine Primary & Secondary Colors
        # Priority: CSS Variables > Weighted Extraction > Fallback
        
        primary = None
        secondary = None
        
        # Check CSS Path
        if css_vars.get('primary'):
            primary = css_vars['primary']
        
        if css_vars.get('secondary'):
            secondary = css_vars['secondary']
            
        # Fallback to extracted list if CSS vars missing
        if not primary and colors:
            primary = colors[0]
            
        if not secondary:
            # If we picked primary from list, pick secondary from list (next different color)
            for c in colors:
                if c != primary:
                    secondary = c
                    break
        
        if primary:
            tokens["primary_color"] = primary
            if secondary:
                tokens["secondary_color"] = secondary
                
            # Accent colors (remaining top colors)
            remaining = [c for c in colors if c not in [primary, secondary]]
            if remaining:
                tokens["accent_colors"] = remaining[:3]
        
        if fonts:
            tokens["font_primary"] = fonts[0]
            if len(fonts) > 1:
                tokens["font_headings"] = fonts[1]
        
        if border_radius:
            tokens["border_radius"] = border_radius
        
        tokens["color_scheme"] = color_scheme
        
        # Validation: If results look weak, use AI fallback
        if not tokens.get("primary_color") or len(tokens) < 3:
            print("Regex design extraction insufficient. Falling back to AI inference...")
            return infer_design_tokens_with_ai(html_content, "gemini-3-flash")
            
        return tokens
            
    except Exception as e:
        print(f"Design token extraction error: {e}")
        return {}


def extract_css_variables(html_content):
    """
    Scans for common brand-related CSS variables.
    Returns dict: {'primary': '#...', 'secondary': '#...'}
    """
    found = {}
    
    # Common variable names for primary brand color
    primary_keys = ['--primary', '--brand', '--main', '--core', '--primary-color', '--color-primary']
    secondary_keys = ['--secondary', '--accent', '--secondary-color', '--color-secondary']
    
    # Simple regex to find var definitions in style blocks
    # Matches: --var-name: #hex or rgb(...)
    for key in primary_keys:
        # Try finding hex
        pattern = rf"{key}:\s*(#[0-9a-fA-F]{{3,6}})"
        match = re.search(pattern, html_content, re.IGNORECASE)
        if match:
            found['primary'] = normalize_hex(match.group(1))
            break
            
    for key in secondary_keys:
        pattern = rf"{key}:\s*(#[0-9a-fA-F]{{3,6}})"
        match = re.search(pattern, html_content, re.IGNORECASE)
        if match:
            found['secondary'] = normalize_hex(match.group(1))
            break
            
    return found


def extract_colors(html_content, css_vars=None):
    """
    Extract color values with weighted logic.
    background-color gets higher weight than generic mentions.
    """
    if css_vars is None:
        css_vars = {}
        
    scores = Counter()
    
    # 1. Background Color Scans (Higher Weight)
    # Matches background-color: #ABC or #AABBCC
    bg_hex_pattern = r'background-color:\s*(#[0-9a-fA-F]{3,6})\b'
    bg_matches = re.findall(bg_hex_pattern, html_content, re.IGNORECASE)
    for c in bg_matches:
        norm = normalize_hex(c)
        if is_valid_brand_color(norm):
            scores[norm] += 3
            
    # 2. Text Color Scans (Medium Weight)
    text_hex_pattern = r'color:\s*(#[0-9a-fA-F]{3,6})\b'
    text_matches = re.findall(text_hex_pattern, html_content, re.IGNORECASE)
    for c in text_matches:
        norm = normalize_hex(c)
        if is_valid_brand_color(norm):
            scores[norm] += 2

    # 3. General Hex Scans (Low Weight)
    # Avoids grabbing things that look like hex but aren't (simple boundary check)
    hex_pattern = r'#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b'
    all_hex = re.findall(hex_pattern, html_content)
    for c in all_hex:
        norm = normalize_hex(c)
        if is_valid_brand_color(norm):
            scores[norm] += 1
            
    # Return sorted by score
    return [color for color, score in scores.most_common(5)]


def normalize_hex(hex_str):
    """Normalize #ABC to #AABBCC and lowercase."""
    hex_str = hex_str.lower()
    if len(hex_str) == 4: # #abc
        return f"#{hex_str[1]*2}{hex_str[2]*2}{hex_str[3]*2}"
    return hex_str


def is_valid_brand_color(color):
    """
    Filter out blacks, whites, grays, and common utility colors.
    """
    if not color.startswith('#'):
        return False
        
    # Black/White
    if color in ['#ffffff', '#000000', '#000']:
        return False
        
    try:
        # Parse RGB
        h = color.lstrip('#')
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        
        # Filter Greys: R, G, B are close to each other
        variance = max(r, g, b) - min(r, g, b)
        if variance < 15: # Very little saturation = grey
            return False
            
        # Filter extreme lights/darks that aren't quite black/white
        # Too bright (near white)
        if r > 240 and g > 240 and b > 240:
            return False
        # Too dark (near black) if generic
        if r < 15 and g < 15 and b < 15:
            return False
            
        return True
    except:
        return False


def extract_fonts(html_content):
    """Extract font-family declarations from CSS."""
    # Pattern for font-family in CSS
    font_pattern = r'font-family:\s*([^;}\n]+)'
    
    fonts_raw = re.findall(font_pattern, html_content, re.IGNORECASE)
    
    fonts = []
    for font_str in fonts_raw:
        # Clean up the font string
        font_clean = font_str.strip().strip('"\'')
        # Take first font in the stack
        first_font = font_clean.split(',')[0].strip().strip('"\'')
        if first_font and first_font.lower() not in ['serif', 'sans-serif', 'monospace', 'inherit', 'initial', 'var']:
            # Ignore variable references like var(--font-sans) in this simple regex
            if not first_font.startswith('var('):
                fonts.append(first_font)
    
    # Return most common fonts
    if fonts:
        font_counts = Counter(fonts)
        return [font for font, count in font_counts.most_common(3)]
    
    # Fallback generic
    return ["Inter, sans-serif"]


def extract_border_radius(html_content):
    """Extract border-radius patterns."""
    radius_pattern = r'border-radius:\s*(\d+px|\d+rem|\d+%)'
    
    radii = re.findall(radius_pattern, html_content, re.IGNORECASE)
    
    if radii:
        # Return most common
        radius_counts = Counter(radii)
        return radius_counts.most_common(1)[0][0]
    
    return "8px"  # Default


def detect_color_scheme(colors, html_content):
    """Detect if the site uses dark or light color scheme."""
    # Simple heuristic: look for dark background indicators
    dark_indicators = ['background-color:#000', 'background:#000', 'bg-dark', 'dark-mode', 'theme-dark']
    
    content_lower = html_content.lower()
    
    dark_matches = sum(1 for indicator in dark_indicators if indicator in content_lower)
    
    if dark_matches > 2:
        return "dark"
    
    # Check if primary colors are dark
    if colors:
        first_color = colors[0]
        # Simple brightness check
        if first_color.startswith('#'):
            try:
                hex_val = first_color.lstrip('#')
                r, g, b = int(hex_val[0:2], 16), int(hex_val[2:4], 16), int(hex_val[4:6], 16)
                brightness = (r + g + b) / 3
                # If primary is very bright (white/yellow), likely dark mode BG? No, usually primary is brand color.
                # Actually, if background is not detected, default to light.
                pass
            except:
                pass
    
    return "light"


def infer_design_tokens_with_ai(content, model_name):
    """
    Fallback: Use AI to infer design style when CSS extraction fails.
    """
    from utils.ai_engine import generate_gemini_response, parse_json_response
    
    try:
        # Take a robust chunk of content (Head + some body)
        # Limit to avoid token overflow but enough to see style definitions
        sample = content[:15000] # Increased from 3000 to catch more CSS
        
        prompt = f"""
        Analyze the following HTML/CSS snippet to reverse-engineer the brand's 'Visual DNA'.
        
        Goal: Extract the VALID Primary and Secondary brand colors.
        
        1. Ignore generic utility colors (red for errors, standard blues for links, grays for borders).
        2. Look for the DOMINANT brand color used in logos, buttons, or headers.
        3. If CSS variables like --primary, --brand are present, use those.
        
        Content Preview:
        {sample}
        
        Return JSON Key-Values:
        - primary_color: Hex Code (The main identity color)
        - secondary_color: Hex Code
        - font_primary: Font family name
        - color_scheme: "light" or "dark"
        - border_radius: "0px", "4px", "8px", "20px" (approximate)
        
        """
        
        result = generate_gemini_response(prompt, model_name=model_name, temperature=0.1) # Low temp for precision
        tokens = parse_json_response(result)
        
        if tokens and "primary_color" in tokens:
            return tokens
        else:
            raise ValueError("AI returned invalid tokens")
            
    except Exception as e:
        print(f"AI design inference error: {e}")
        return {
            "primary_color": "#667eea",
            "secondary_color": "#764ba2",
            "font_primary": "Inter, sans-serif",
            "color_scheme": "light",
            "border_radius": "8px"
        }


def format_design_context(design_tokens):
    """
    Formats design tokens into a prompt-ready string.
    """
    if not design_tokens:
        return ""
    
    context = f"""
    BRAND DESIGN SYSTEM (Use these EXACT values in HTML mockups):
    - Primary Color: {design_tokens.get('primary_color', '#667eea')}
    - Secondary Color: {design_tokens.get('secondary_color', '#764ba2')}
    - Font (Body): {design_tokens.get('font_primary', 'Inter, sans-serif')}
    - Font (Headings): {design_tokens.get('font_headings', design_tokens.get('font_primary', 'Inter, sans-serif'))}
    - Border Radius: {design_tokens.get('border_radius', '8px')}
    - Color Scheme: {design_tokens.get('color_scheme', 'light')}
    """
    
    if 'accent_colors' in design_tokens:
        context += f"\n    - Accent Colors: {', '.join(design_tokens['accent_colors'])}"
    
    context += "\n\n    CRITICAL: The visual mockups MUST use these exact brand colors and fonts. Do not use generic purple gradients or placeholder colors."
    
    return context


def generate_css_vars(design_tokens):
    """
    Generates a string of CSS variables from design tokens for injection into AI prompts.
    """
    if not design_tokens:
        return ":root { --primary: #667eea; --secondary: #764ba2; --bg-color: #ffffff; --text-color: #333333; --font-main: 'Inter', sans-serif; --radius: 8px; }"
    
    css_vars = [":root {"]
    
    # Colors
    primary = design_tokens.get("primary_color", "#667eea")
    secondary = design_tokens.get("secondary_color", "#764ba2")
    css_vars.append(f"  --primary: {primary};")
    css_vars.append(f"  --secondary: {secondary};")
    
    # Color Scheme Logic
    scheme = design_tokens.get("color_scheme", "light")
    if scheme == "dark":
        css_vars.append("  --bg-color: #1a1a1a;")
        css_vars.append("  --text-color: #f0f0f0;")
        css_vars.append("  --card-bg: #2d2d2d;")
    else:
        css_vars.append("  --bg-color: #ffffff;")
        css_vars.append("  --text-color: #111827;")
        css_vars.append("  --card-bg: #ffffff;")
        
    # Fonts
    font = design_tokens.get("font_primary", "system-ui, sans-serif")
    css_vars.append(f"  --font-main: {font};")
    
    # Radius
    radius = design_tokens.get("border_radius", "8px")
    css_vars.append(f"  --radius: {radius};")
    
    css_vars.append("}")
    return "\n".join(css_vars)
