"""
Image Extractor Utility
Extracts logo and hero images from HTML content to enhance brand profiles.
"""

from bs4 import BeautifulSoup
from urllib.parse import urljoin

def extract_brand_images(html_content, base_url):
    """
    Extracts potential logo and hero images.
    """
    if not html_content:
        return {"logo": None, "hero_images": []}
        
    soup = BeautifulSoup(html_content, 'html.parser')
    images = {
        "logo": None,
        "hero_images": []
    }
    
    # 1. Try to find Logo
    # Look for common logo classes/ids or alt text
    logo_candidates = soup.find_all('img', alt=lambda x: x and 'logo' in x.lower())
    if not logo_candidates:
        logo_candidates = soup.find_all('img', src=lambda x: x and 'logo' in x.lower())
    
    if logo_candidates:
        images["logo"] = urljoin(base_url, logo_candidates[0]['src'])
        
    # 2. Try to find Hero Image
    # Look for large images or images in <header>, <section> with 'hero' or 'banner'
    hero_containers = soup.find_all(['section', 'div', 'header'], class_=lambda x: x and ('hero' in x.lower() or 'banner' in x.lower()))
    
    for container in hero_containers:
        img = container.find('img')
        if img and img.get('src'):
            images["hero_images"].append(urljoin(base_url, img['src']))
            
    # Fallback: get top 3 large images
    if not images["hero_images"]:
        all_imgs = soup.find_all('img')
        # Filter by width/height if available, otherwise just take first few
        for img in all_imgs[:5]:
            if img.get('src') and not any(ext in img['src'].lower() for ext in ['.svg', '.gif', 'icon']):
                images["hero_images"].append(urljoin(base_url, img['src']))
                
    # Unique and limited
    images["hero_images"] = list(set(images["hero_images"]))[:3]
    
    return images
