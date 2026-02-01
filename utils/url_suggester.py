"""
URL Suggester Utility
Suggests common key pages (Pricing, About, Contact, Features) for a brand based on its homepage.
"""

from urllib.parse import urljoin, urlparse

def suggest_common_urls(homepage_url):
    """
    Returns a list of commonly found URL patterns for companies.
    """
    if not homepage_url:
        return []
        
    parsed = urlparse(homepage_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    
    # Common patterns
    patterns = [
        {"name": "About Us", "path": "/about"},
        {"name": "Pricing", "path": "/pricing"},
        {"name": "Features/Products", "path": "/features"},
        {"name": "Features/Products", "path": "/products"},
        {"name": "Contact", "path": "/contact"},
        {"name": "Blog", "path": "/blog"},
        {"name": "Documentation", "path": "/docs"},
        {"name": "Resources", "path": "/resources"},
        {"name": "Case Studies", "path": "/customers"},
        {"name": "Case Studies", "path": "/case-studies"},
    ]
    
    suggestions = []
    for p in patterns:
        suggestions.append({
            "label": p["name"],
            "url": urljoin(base, p["path"]),
            "category": "Standard"
        })
        
    return suggestions

def verify_url_exists(url):
    """
    Optional: Check if URL actually exists via HEAD request.
    """
    import requests
    try:
        resp = requests.head(url, timeout=3, allow_redirects=True, verify=True)
        return resp.status_code < 400
    except:
        return False
