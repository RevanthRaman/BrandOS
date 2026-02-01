import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

def scrape_website(url):
    """
    Scrapes the given URL and returns the text content and meta description.
    """
    try:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        # Use a Session to handle cookies/redirects
        session = requests.Session()
        
        # Modern Chrome User-Agent (Chrome 123)
        ua_str = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
            
        headers = {
            'User-Agent': ua_str,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.google.com/',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'cross-site',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'Sec-Ch-Ua': '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
        }
        
        
        # verify=True is the default, ensuring SSL certificates are valid
        response = session.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract text
        text = soup.get_text(separator=' ', strip=True)
        
        # Extract meta description
        meta_desc = ""
        meta = soup.find('meta', attrs={'name': 'description'})
        if meta:
            meta_desc = meta.get('content')
            
        # Extract Title
        title = soup.title.string if soup.title else "No Title"

        # Extract OG Image
        og_image = ""
        og_img_tag = soup.find('meta', property='og:image')
        if og_img_tag:
            og_image = og_img_tag.get('content')

        return {
            "url": url,
            "title": title,
            "text": text[:2000000], # Increased limit for Gemini 3 (2M chars)
            "meta_description": meta_desc,
            "og_image": og_image,
            "html_content": str(response.content, 'utf-8', errors='ignore')[:500000],  # Store HTML for design extraction
            "status": "success"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

def extract_nav_links(url, html_content):
    """
    Extracts relevant navigation links (About, Pricing, Blog, etc.) from the HTML.
    Returns a list of dictionaries: {'text': 'Link Text', 'url': 'Absolute URL', 'category': 'Category'}
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        links = []
        seen_urls = set()
        
        # Categorized Keywords
        categories = {
            "Company": ['about', 'mission', 'values', 'team', 'careers', 'contact', 'history'],
            "Offerings": ['pricing', 'product', 'services', 'solutions', 'features', 'platform'],
            "Resources": ['blog', 'news', 'resources', 'case studies', 'customers', 'docs', 'documentation']
        }
        
        # Blacklist (Noise)
        blacklist = ['login', 'signin', 'signup', 'register', 'support', 'help', 'faq', 'terms', 'privacy', 'policy']
        
        # Priority tags to search within first
        priority_tags = soup.find_all(['nav', 'header', 'footer'])
        
        # Helper to process a link tag
        def process_link(a_tag, priority_score=0):
            href = a_tag.get('href')
            if not href:
                return
                
            text = a_tag.get_text(strip=True)
            
            if not text or len(text) > 40: # Skip empty or very long link text
                return
                
            # Normalize URL
            if href.startswith('/'):
                # Handle relative URLs
                from urllib.parse import urljoin
                full_url = urljoin(url, href)
            elif href.startswith('http'):
                full_url = href
            else:
                return
                
            # Filter for same domain (simple check)
            from urllib.parse import urlparse
            base_domain = urlparse(url).netloc
            link_domain = urlparse(full_url).netloc
            
            if base_domain not in link_domain:
                return
            
            text_lower = text.lower()
            href_lower = href.lower()
            
            # Check Blacklist
            if any(b in text_lower or b in href_lower for b in blacklist):
                return

            # Determine Category & Score
            category = "Other"
            score = priority_score
            
            for cat, keywords in categories.items():
                if any(k in text_lower or k in href_lower for k in keywords):
                    category = cat
                    score += 2 # Boost categorized links
                    if cat == "Company" or cat == "Offerings":
                        score += 1 # Boost core pages even more
                    break
            
            # Depth Penalty: Penalize deep nesting (e.g. /products/software/v2)
            # Count slashes in path. Root is usually 1 (e.g. /about).
            from urllib.parse import urlparse
            path = urlparse(full_url).path
            depth = path.strip('/').count('/')
            score -= depth * 0.5
            
            # Length Penalty: Slight penalty for very long URLs
            if len(full_url) > 60:
                score -= 0.5
            
            # If not categorized, only include if it looks like a main nav item (short, in nav tag)
            if category == "Other" and priority_score < 2:
                return 

            if full_url not in seen_urls and full_url != url:
                seen_urls.add(full_url)
                links.append({'text': text, 'url': full_url, 'category': category, 'score': score})

        # 1. Scan priority areas first
        for tag in priority_tags:
            for a in tag.find_all('a', href=True):
                process_link(a, priority_score=2)
                
        # 2. Scan the rest of the body if we don't have enough
        for a in soup.find_all('a', href=True):
            process_link(a, priority_score=1)
                
        # Sort by score (descending)
        links.sort(key=lambda x: x['score'], reverse=True)
        
        # Clean up the list to remove score before returning
        final_links = [{'label': l['text'], 'url': l['url'], 'category': l['category']} for l in links]
        
        # Limit to top 15 suggestions
        return final_links[:15]
    except Exception as e:
        print(f"Error extracting links: {e}")
        return []
