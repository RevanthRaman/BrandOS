"""
Brand Manager Module
Handles brand-centric operations including brand creation, URL management,
and loading brand data.
"""

import json
from datetime import datetime
from urllib.parse import urlparse
from sqlalchemy.orm import joinedload


def extract_brand_name_from_url(url):
    """
    Extract brand name from URL.
    
    Examples:
    - stripe.com → Stripe
    - www.twilio.com → Twilio
    - pricing.mailchimp.com → Mailchimp
    """
    try:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        
        # Remove common subdomains
        domain = domain.replace('www.', '').replace('pricing.', '').replace('blog.', '').replace('app.', '')
        
        # Get domain name (before .com/.org/etc)
        brand_name = domain.split('.')[0]
        
        # Capitalize
        brand_name = brand_name.capitalize()
        
        return brand_name
        
    except Exception as e:
        print(f"Error extracting brand name from {url}: {e}")
        return "Unknown Brand"



def check_brand_exists(brand_name):
    """
    Check if a brand already exists in the database.
    
    Returns:
        (brand_id, brand_data) if exists, (None, None) if not
    """
    from utils.db_migration import Brand
    
    session = get_session()
    
    try:
        brand = session.query(Brand).filter(Brand.brand_name == brand_name).first()
        
        if brand:
            return (brand.id, {
                'id': brand.id,
                'brand_name': brand.brand_name,
                'homepage_url': brand.homepage_url,
                'logo_url': brand.logo_url,
                'created_at': brand.created_at.isoformat() if brand.created_at else None,
                'last_updated': brand.last_updated.isoformat() if brand.last_updated else None
            })
        else:
            return (None, None)
            
    except Exception as e:
        print(f"Error checking brand existence: {e}")
        return (None, None)
    finally:
        session.close()


def get_brand_urls(brand_id):
    """
    Get all URLs analyzed for a brand.
    
    Returns:
        List of URL dicts with metadata
    """
    from utils.db_migration import BrandURL
    
    session = get_session()
    
    try:
        urls = session.query(BrandURL).filter(BrandURL.brand_id == brand_id).all()
        
        result = []
        for url_obj in urls:
            result.append({
                'url': url_obj.url,
                'page_type': url_obj.page_type,
                'scraped_at': url_obj.scraped_at.isoformat() if url_obj.scraped_at else None
            })
        
        return result
        
    except Exception as e:
        print(f"Error getting brand URLs: {e}")
        return []
    finally:
        session.close()


def save_or_update_brand(brand_name, urls_data, analysis_data, design_tokens=None, knowledge_graph=None, competitor_analysis=None, brand_imagery=None):
    """
    Save or update a brand with new URLs and analysis.
    
    Args:
        brand_name: Name of the brand
        urls_data: List of {'url': str, 'text': str, 'html': str, 'page_type': str}
        analysis_data: Dict with 'analysis', 'personas', 'strategy'
        design_tokens: Optional design tokens dict
        knowledge_graph: Optional knowledge graph dict
        competitor_analysis: Optional competitor analysis dict
        brand_imagery: Optional dict with 'logo' and 'hero_images'
        
    Returns:
        brand_id
    """
    from utils.db_migration import Brand, BrandURL, BrandAnalysisNew
    
    session = get_session()
    
    try:
        # Check if brand exists
        brand = session.query(Brand).filter(Brand.brand_name == brand_name).first()
        
        if brand:
            # Brand exists - update it
            print(f"Updating existing brand: {brand_name}")
            brand.last_updated = datetime.utcnow()
            is_new = False
        else:
            # Create new brand
            print(f"Creating new brand: {brand_name}")
            brand = Brand(
                brand_name=brand_name,
                homepage_url=urls_data[0]['url'] if urls_data else None,
                created_at=datetime.utcnow(),
                last_updated=datetime.utcnow()
            )
            session.add(brand)
            session.flush()  # Get the brand ID
            is_new = True
            
        # Update Logo if provided
        if brand_imagery and brand_imagery.get('logo'):
            brand.logo_url = brand_imagery['logo']
        
        # Add new URLs
        existing_urls = [u.url for u in brand.urls]
        
        for url_data in urls_data:
            if url_data['url'] not in existing_urls:
                brand_url = BrandURL(
                    brand_id=brand.id,
                    url=url_data['url'],
                    page_type=url_data.get('page_type', 'other'),
                    html_content=url_data.get('html'),
                    text_content=url_data.get('text'),
                    scraped_at=datetime.utcnow()
                )
                session.add(brand_url)
                print(f"  Added URL: {url_data['url']}")
        
        # Handle analysis (new brand or update)
        if is_new:
            # New brand - create initial unified profile
            unified_profile = {
                "analysis": analysis_data.get('analysis', {}),
                "personas": analysis_data.get('personas', []),
                "strategy": analysis_data.get('strategy', {})
            }
            
            # Individual analyses (one per URL)
            individual_analyses = {}
            for url_data in urls_data:
                individual_analyses[url_data['url']] = {
                    "analysis": analysis_data.get('analysis', {}),
                    "personas": analysis_data.get('personas', []),
                    "strategy": analysis_data.get('strategy', {}),
                    "analyzed_at": datetime.utcnow().isoformat()
                }
            
            analysis = BrandAnalysisNew(
                brand_id=brand.id,
                unified_profile_json=json.dumps(unified_profile),
                individual_analyses_json=json.dumps(individual_analyses),
                design_tokens_json=json.dumps(design_tokens) if design_tokens else None,
                knowledge_graph_json=json.dumps(knowledge_graph) if knowledge_graph else None,
                brand_imagery_json=json.dumps(brand_imagery) if brand_imagery else None,
                competitor_analysis_json=json.dumps(competitor_analysis) if competitor_analysis else None,
                created_at=datetime.utcnow()
            )
            session.add(analysis)
            
        else:
            # Existing brand - merge with existing profile (handled in app.py with AI merge)
            # For now, just update the latest analysis
            existing_analysis = session.query(BrandAnalysisNew).filter(
                BrandAnalysisNew.brand_id == brand.id
            ).order_by(BrandAnalysisNew.created_at.desc()).first()
            
            if existing_analysis:
                # Update existing
                existing_analysis.unified_profile_json = json.dumps(analysis_data)
                existing_analysis.updated_at = datetime.utcnow()
                
                # Load existing individual analyses to merge
                current_individual = json.loads(existing_analysis.individual_analyses_json) if existing_analysis.individual_analyses_json else {}
                
                # Add/Update with new URLs
                for url_data in urls_data:
                    current_individual[url_data['url']] = {
                        "analysis": analysis_data.get('analysis', {}),
                        "personas": analysis_data.get('personas', []),
                        "strategy": analysis_data.get('strategy', {}),
                        "analyzed_at": datetime.utcnow().isoformat()
                    }
                
                existing_analysis.individual_analyses_json = json.dumps(current_individual)

                if design_tokens:
                    existing_analysis.design_tokens_json = json.dumps(design_tokens)
                if knowledge_graph:
                    existing_analysis.knowledge_graph_json = json.dumps(knowledge_graph)
                if competitor_analysis:
                    existing_analysis.competitor_analysis_json = json.dumps(competitor_analysis)
                if brand_imagery:
                    existing_analysis.brand_imagery_json = json.dumps(brand_imagery)
            else:
                # Create new analysis record
                unified_profile = analysis_data
                analysis = BrandAnalysisNew(
                    brand_id=brand.id,
                    unified_profile_json=json.dumps(unified_profile),
                    individual_analyses_json="{}",
                    design_tokens_json=json.dumps(design_tokens) if design_tokens else None,
                    knowledge_graph_json=json.dumps(knowledge_graph) if knowledge_graph else None,
                    brand_imagery_json=json.dumps(brand_imagery) if brand_imagery else None,
                    competitor_analysis_json=json.dumps(competitor_analysis) if competitor_analysis else None,
                    created_at=datetime.utcnow()
                )
                session.add(analysis)
        
        session.commit()
        brand_id = brand.id
        
        print(f"✓ Brand saved successfully: {brand_name} (ID: {brand_id})")
        return brand_id
        
    except Exception as e:
        session.rollback()
        print(f"Error saving brand: {e}")
        raise e
    finally:
        session.close()


def load_brand_data(brand_id):
    """
    Load complete brand data including URLs and analysis.
    
    Returns:
        Dict with brand data in the format expected by the app
    """
    from utils.db_migration import Brand, BrandAnalysisNew
    
    session = get_session()
    
    try:
        # Load brand with relationships
        brand = session.query(Brand).options(
            joinedload(Brand.urls),
            joinedload(Brand.analyses)
        ).filter(Brand.id == brand_id).first()
        
        if not brand:
            return None
        
        # Get latest analysis
        latest_analysis = session.query(BrandAnalysisNew).filter(
            BrandAnalysisNew.brand_id == brand_id
        ).order_by(BrandAnalysisNew.created_at.desc()).first()
        
        if not latest_analysis:
            return None
        
        # Parse JSON fields
        unified_profile = json.loads(latest_analysis.unified_profile_json) if latest_analysis.unified_profile_json else {}
        design_tokens = json.loads(latest_analysis.design_tokens_json) if latest_analysis.design_tokens_json else {}
        knowledge_graph = json.loads(latest_analysis.knowledge_graph_json) if latest_analysis.knowledge_graph_json else {}
        competitor_analysis = json.loads(latest_analysis.competitor_analysis_json) if latest_analysis.competitor_analysis_json else {}
        brand_imagery = json.loads(latest_analysis.brand_imagery_json) if latest_analysis.brand_imagery_json else {}
        
        # Build result in app-compatible format
        result = {
            "brand_id": brand.id,
            "brand_name": brand.brand_name,
            "url": brand.homepage_url,
            "logo_url": brand.logo_url,
            "brand_imagery": brand_imagery,
            "all_urls": [url_obj.url for url_obj in brand.urls],
            "scrape": {
                "url": brand.homepage_url,
                "text": "",  # Aggregate from individual analyses
                "html_content": "",
                "status": "success"
            },
            "individual_scrapes": {},
            "individual_htmls": {},
            "analysis": unified_profile.get('analysis', {}),
            "personas": unified_profile.get('personas', []),
            "strategic": unified_profile.get('strategy', {}),
            "competitor": competitor_analysis,
            "knowledge_graph": knowledge_graph,
            "design_tokens": design_tokens,
            "db_id": brand.id
        }
        
        # Add individual scrapes and htmls
        for url_obj in brand.urls:
            # Populate scrapes/htmls regardless of previous analysis existence
            result["individual_scrapes"][url_obj.url] = url_obj.text_content or ""
            result["individual_htmls"][url_obj.url] = url_obj.html_content or ""
            
            # If this is the homepage, populate the main scrape object
            if url_obj.url == brand.homepage_url:
                result["scrape"]["text"] = url_obj.text_content or ""
                result["scrape"]["html_content"] = url_obj.html_content or ""
        
        return result
        
    except Exception as e:
        print(f"Error loading brand data: {e}")
        return None
    finally:
        session.close()


def get_all_brands(limit=50):
    """
    Get all brands with metadata for dropdown selector.
    Optimized to prevent N+1 queries.
    
    Returns:
        List of brand dicts with name, url_count, last_updated
    """
    from utils.db_migration import Brand
    
    session = get_session()
    
    try:
        # Optimization: JOIN load urls so accessing brand.urls doesn't trigger new queries
        # This fixes the N+1 query issue
        brands = session.query(Brand).options(
            joinedload(Brand.urls)
        ).order_by(Brand.last_updated.desc()).limit(limit).all()
        
        result = []
        for brand in brands:
            # This access is now in-memory thanks to joinedload
            url_count = len(brand.urls)
            
            # Calculate time ago
            if brand.last_updated:
                delta = datetime.utcnow() - brand.last_updated
                if delta.days > 0:
                    time_ago = f"{delta.days} day{'s' if delta.days > 1 else ''} ago"
                elif delta.seconds >= 3600:
                    hours = delta.seconds // 3600
                    time_ago = f"{hours} hour{'s' if hours > 1 else ''} ago"
                else:
                    minutes = delta.seconds // 60
                    time_ago = f"{minutes} minute{'s' if minutes > 1 else ''} ago"
            else:
                time_ago = "unknown"
            
            result.append({
                'id': brand.id,
                'name': brand.brand_name,
                'homepage_url': brand.homepage_url,
                'url_count': url_count,
                'last_updated': brand.last_updated.isoformat() if brand.last_updated else None,
                'last_updated_relative': time_ago
            })
        
        return result
        
    except Exception as e:
        print(f"Error getting brands: {e}")
        return []
    finally:
        session.close()







def delete_brand_related_data(brand_id):
    """
    Delete all auxiliary data (AEO, Assets, Campaigns) associated with a brand ID.
    Uses utils.db session as these tables are in the old/mixed schema.
    """
    from utils.db import AEOAnalysis, MarketingAsset, Campaign, Optimization
    from utils.db import get_session as get_db_session
    
    session = get_db_session()
    try:
        # Delete related records
        aeo_count = session.query(AEOAnalysis).filter(AEOAnalysis.brand_id == brand_id).delete()
        asset_count = session.query(MarketingAsset).filter(MarketingAsset.brand_id == brand_id).delete()
        camp_count = session.query(Campaign).filter(Campaign.brand_id == brand_id).delete()
        opt_count = session.query(Optimization).filter(Optimization.brand_id == brand_id).delete()
        
        session.commit()
        print(f"✓ Cleanup: Deleted {aeo_count} AEO reports, {asset_count} Assets, {camp_count} Campaigns, {opt_count} Optimizations")
        return True
    except Exception as e:
        session.rollback()
        print(f"Error cleaning up related brand data: {e}")
        return False
    finally:
        session.close()


def delete_brand(brand_id):
    """
    Delete a brand and all associated data.
    """
    # First delete related data in other tables
    delete_brand_related_data(brand_id)

    from utils.db_migration import Brand
    
    session = get_session()
    
    try:
        brand = session.query(Brand).filter(Brand.id == brand_id).first()
        if brand:
            session.delete(brand)
            session.commit()
            print(f"✓ Deleted brand ID: {brand_id}")
            return True
        return False
    except Exception as e:
        session.rollback()
        print(f"Error deleting brand: {e}")
        return False
    finally:
        session.close()


def delete_brand_url(brand_id, url):
    """
    Delete a specific URL for a brand.
    """
    from utils.db_migration import BrandURL
    
    session = get_session()
    
    try:
        brand_url = session.query(BrandURL).filter(
            BrandURL.brand_id == brand_id,
            BrandURL.url == url
        ).first()
        
        if brand_url:
            session.delete(brand_url)
            session.commit()
            print(f"✓ Deleted URL: {url} from brand: {brand_id}")
            return True
        return False
    except Exception as e:
        session.rollback()
        print(f"Error deleting URL: {e}")
        return False
    finally:
        session.close()


# Helper function to add get_session to db_migration module
def get_session():
    """
    Get database session from utils.db.
    This effectively manages connection pooling via st.cache_resource in db.py.
    """
    from utils.db import get_session as main_get_session
    return main_get_session()


def delete_aeo_analysis(aeo_id):
    """Delete a specific AEO analysis report."""
    from utils.db import AEOAnalysis, get_session as get_db_session
    session = get_db_session()
    try:
        record = session.query(AEOAnalysis).filter(AEOAnalysis.id == aeo_id).first()
        if record:
            session.delete(record)
            session.commit()
            return True
        return False
    except Exception as e:
        print(f"Error deleting AEO analysis: {e}")
        session.rollback()
        return False
    finally:
        session.close()


def delete_marketing_asset(asset_id):
    """Delete a specific marketing asset."""
    from utils.db import MarketingAsset, get_session as get_db_session
    session = get_db_session()
    try:
        record = session.query(MarketingAsset).filter(MarketingAsset.id == asset_id).first()
        if record:
            session.delete(record)
            session.commit()
            return True
        return False
    except Exception as e:
        print(f"Error deleting asset: {e}")
        session.rollback()
        return False
    finally:
        session.close()


def delete_campaign(campaign_id):
    """Delete a campaign and its assets."""
    from utils.db import Campaign, MarketingAsset, get_session as get_db_session
    session = get_db_session()
    try:
        # Assets should cascade or be deleted manually
        session.query(MarketingAsset).filter(MarketingAsset.campaign_id == campaign_id).delete()
        
        record = session.query(Campaign).filter(Campaign.id == campaign_id).first()
        if record:
            session.delete(record)
            session.commit()
            return True
        return False
    except Exception as e:
        print(f"Error deleting campaign: {e}")
        session.rollback()
        return False
    finally:
        session.close()


def rename_brand(brand_id, new_name):
    """Rename a brand."""
    from utils.db_migration import Brand
    session = get_session()
    try:
        brand = session.query(Brand).filter(Brand.id == brand_id).first()
        if brand:
            brand.brand_name = new_name
            brand.last_updated = datetime.utcnow()
            session.commit()
            return True
        return False
    except Exception as e:
        print(f"Error renaming brand: {e}")
        session.rollback()
        return False
    finally:
        session.close()


def get_brand_stats(brand_id):
    """
    Get statistics for a brand (Url count, AEO reports, Assets).
    """
    from utils.db_migration import Brand
    from utils.db import AEOAnalysis, MarketingAsset, Campaign
    
    stats = {"urls": 0, "aeo_reports": 0, "assets": 0, "campaigns": 0}
    
    # Use the same session manager for both checks if possible, or separate
    session = get_session()
    try:
        brand = session.query(Brand).filter(Brand.id == brand_id).first()
        if brand:
            stats["urls"] = len(brand.urls)
            
        # Using the same session to query other tables as likely they drift into same DB structure
        # but safely we can keep using the models
        stats["aeo_reports"] = session.query(AEOAnalysis).filter(AEOAnalysis.brand_id == brand_id).count()
        stats["assets"] = session.query(MarketingAsset).filter(MarketingAsset.brand_id == brand_id).count()
        stats["campaigns"] = session.query(Campaign).filter(Campaign.brand_id == brand_id).count()
        
    except Exception as e:
        # print(f"Error fetching stats: {e}")
        pass
    finally:
        session.close()
        
    return stats


def get_brand_aeo_reports(brand_id):
    """Get list of AEO reports for a brand."""
    from utils.db import AEOAnalysis
    session = get_session()
    try:
        reports = session.query(AEOAnalysis).filter(AEOAnalysis.brand_id == brand_id).order_by(AEOAnalysis.created_at.desc()).all()
        return [{
            "id": r.id,
            "date": r.created_at.isoformat(),
            "query": r.query,
            "rank": r.rank_position,
            "vis_score": r.visibility_score
        } for r in reports]
    finally:
        session.close()


def get_brand_assets(brand_id):
    """Get list of Assets for a brand."""
    from utils.db import MarketingAsset
    session = get_session()
    try:
        assets = session.query(MarketingAsset).filter(MarketingAsset.brand_id == brand_id).order_by(MarketingAsset.created_at.desc()).limit(50).all()
        return [{
            "id": a.id,
            "type": a.asset_type,
            "content_preview": a.content[:50] + "..." if a.content else "",
            "date": a.created_at.isoformat(),
            "campaign_id": a.campaign_id
        } for a in assets]
    finally:
        session.close()
