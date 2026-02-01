"""
Database module for brand analysis application.
Uses SQLAlchemy ORM with PostgreSQL backend.
"""

import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import json

# Create declarative base
Base = declarative_base()

# Database Models
class BrandAnalysis(Base):
    __tablename__ = 'brand_analyses'
    
    id = Column(Integer, primary_key=True)
    url = Column(String, nullable=False)
    title = Column(String)
    analysis_json = Column(Text)  # Brand DNA
    personas_json = Column(Text)  # Buyer Personas
    strategic_insights_json = Column(Text)  # Strategic Insights
    competitor_analysis_json = Column(Text) # Competitor Analysis
    knowledge_graph_json = Column(Text)  # Knowledge Graph
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    # optimizations = relationship("Optimization", back_populates="brand")
    # aeo_analyses = relationship("AEOAnalysis", back_populates="brand")
    # assets = relationship("MarketingAsset", backref="brand")


class Optimization(Base):
    __tablename__ = 'optimizations_v2'
    
    id = Column(Integer, primary_key=True)
    # FK Removed to prevent cross-Base mapper errors
    brand_id = Column(Integer)
    url = Column(String)
    original_content = Column(Text)
    optimized_content = Column(Text)
    optimization_type = Column(String)  # 'seo', 'aeo', 'ab_test'
    metrics_json = Column(Text)  # Readability scores, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    # brand = relationship("BrandAnalysis", back_populates="optimizations")


class MarketingAsset(Base):
    __tablename__ = 'marketing_assets_v2'
    
    id = Column(Integer, primary_key=True)
    # FK Removed to prevent cross-Base mapper errors
    brand_id = Column(Integer)
    campaign_id = Column(Integer, ForeignKey('campaigns_v2.id'), nullable=True)
    asset_type = Column(String)  # 'email', 'social', 'blog', 'ad_copy', 'social_card'
    content = Column(Text)
    persona_target = Column(String)
    image_url = Column(String, nullable=True)  # For social cards
    metadata_json = Column(Text)  # Additional metadata
    created_at = Column(DateTime, default=datetime.utcnow)


class Campaign(Base):
    __tablename__ = 'campaigns_v2'
    
    id = Column(Integer, primary_key=True)
    # FK Removed to prevent cross-Base mapper errors
    brand_id = Column(Integer)
    name = Column(String, nullable=False)
    goal = Column(String)
    theme = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class AEOAnalysis(Base):
    __tablename__ = 'aeo_analyses_v2'
    
    id = Column(Integer, primary_key=True)
    # FK Removed to prevent cross-Base mapper errors
    brand_id = Column(Integer)
    query = Column(String, nullable=False)
    brand_url = Column(String)
    analysis_json = Column(Text)  # Full AEO analysis results
    rank_position = Column(Integer, nullable=True)
    visibility_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    # brand = relationship("BrandAnalysis", back_populates="aeo_analyses")


import streamlit as st

# Global engine and session (kept for backward compatibility logic)
engine = None
Session = None

@st.cache_resource
def get_engine():
    """
    Creates and caches the SQLAlchemy engine.
    This ensures we don't reconnect to Supabase on every script rerun.
    """
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable not set")
    
    # Fix for SQLAlchemy requiring 'postgresql://' instead of 'postgres://'
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    # Create engine (Connection Pooling is handled by Supabase Transaction Pooler URL)
    # pool_pre_ping=True helps with dropped connections
    engine = create_engine(db_url, echo=False, pool_pre_ping=True)
    
    # Create tables (only does so if they don't exist)
    Base.metadata.create_all(engine)
    
    # CRITICAL FIX: Also create tables for the new brand schema (db_migration)
    # This ensures 'brands', 'brand_urls', 'brand_analyses_new' are created
    try:
        from utils.db_migration import create_new_schema
        create_new_schema(engine)
    except Exception as e:
        print(f"Error initializing new schema: {e}")

    return engine

def init_db():
    """
    Initialize the database connection.
    Now just a wrapper around the cached get_engine().
    """
    global engine, Session
    
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    
    return engine

def get_session():
    """Get a new database session."""
    # Ensure engine is initialized
    global Session
    if Session is None:
        init_db()
    return Session()


# Helper Functions
def save_brand_analysis(url, title, analysis_json, personas_json, strategic_json=None, competitor_json=None, knowledge_graph_json=None):
    """
    Save a brand analysis to the database.
    
    Args:
        url: Brand URL
        title: Brand title
        analysis_json: JSON string of brand DNA
        personas_json: JSON string of buyer personas
        strategic_json: JSON string of strategic insights (optional)
        competitor_json: JSON string of competitor analysis (optional)
    
    Returns:
        Brand analysis ID
    """
    session = get_session()
    
    try:
        # Convert to JSON strings if they're dicts
        if isinstance(analysis_json, (dict, list)):
            analysis_json = json.dumps(analysis_json)
        if isinstance(personas_json, (dict, list)):
            personas_json = json.dumps(personas_json)
        if isinstance(strategic_json, (dict, list)):
            strategic_json = json.dumps(strategic_json)
        if isinstance(competitor_json, (dict, list)):
            competitor_json = json.dumps(competitor_json)
        if isinstance(knowledge_graph_json, (dict, list)):
            knowledge_graph_json = json.dumps(knowledge_graph_json)
        
        brand = BrandAnalysis(
            url=url,
            title=title,
            analysis_json=analysis_json,
            personas_json=personas_json,
            strategic_insights_json=strategic_json,
            competitor_analysis_json=competitor_json,
            knowledge_graph_json=knowledge_graph_json
        )
        
        session.add(brand)
        session.commit()
        brand_id = brand.id
        
        return brand_id
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def save_optimization(brand_id, url, original_content, optimized_content, optimization_type, metrics_json=None):
    """
    Save an optimization to the database.
    
    Args:
        brand_id: ID of the brand analysis
        url: URL being optimized
        original_content: Original content
        optimized_content: Optimized content
        optimization_type: Type of optimization ('seo', 'aeo', 'ab_test')
        metrics_json: JSON string of metrics (optional)
    
    Returns:
        Optimization ID
    """
    session = get_session()
    
    try:
        if isinstance(metrics_json, (dict, list)):
            metrics_json = json.dumps(metrics_json)
        
        optimization = Optimization(
            brand_id=brand_id,
            url=url,
            original_content=original_content,
            optimized_content=optimized_content,
            optimization_type=optimization_type,
            metrics_json=metrics_json
        )
        
        session.add(optimization)
        session.commit()
        opt_id = optimization.id
        
        return opt_id
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def save_asset(brand_id, asset_type, content, persona_target=None, image_url=None, metadata_json=None, campaign_id=None):
    """
    Save a marketing asset to the database.
    
    Args:
        brand_id: ID of the brand analysis
        asset_type: Type of asset ('email', 'social', 'blog', etc.)
        content: Asset content
        persona_target: Target persona (optional)
        image_url: URL to generated image (optional)
        metadata_json: Additional metadata (optional)
        campaign_id: ID of the campaign (optional)
    
    Returns:
        Asset ID
    """
    session = get_session()
    
    try:
        if isinstance(metadata_json, (dict, list)):
            metadata_json = json.dumps(metadata_json)
        
        asset = MarketingAsset(
            brand_id=brand_id,
            campaign_id=campaign_id,
            asset_type=asset_type,
            content=content,
            persona_target=persona_target,
            image_url=image_url,
            metadata_json=metadata_json
        )
        
        session.add(asset)
        session.commit()
        asset_id = asset.id
        
        return asset_id
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()





def save_aeo_analysis(brand_id, query, brand_url, analysis_json, rank_position=None, visibility_score=None):
    """
    Save an AEO analysis to the database.
    
    Args:
        brand_id: ID of the brand analysis
        query: Query used for AEO analysis
        brand_url: Brand URL being analyzed
        analysis_json: JSON string of analysis results
        rank_position: Rank position in results (optional)
        visibility_score: Visibility score (optional)
    
    Returns:
        AEO analysis ID
    """
    session = get_session()
    
    try:
        if isinstance(analysis_json, (dict, list)):
            analysis_json = json.dumps(analysis_json)
        
        aeo = AEOAnalysis(
            brand_id=brand_id,
            query=query,
            brand_url=brand_url,
            analysis_json=analysis_json,
            rank_position=rank_position,
            visibility_score=visibility_score
        )
        
        session.add(aeo)
        session.commit()
        aeo_id = aeo.id
        
        return aeo_id
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def get_latest_aeo_keywords(brand_id=None, brand_name=None):
    """
    Retrieves the latest AEO keywords for a given brand ID or brand name.
    """
    session = get_session()
    try:
        # First try by brand_id (new system)
        aeo = None
        if brand_id:
            aeo = session.query(AEOAnalysis).filter(AEOAnalysis.brand_id == brand_id).order_by(AEOAnalysis.created_at.desc()).first()
        
        # If not found, try by brand_name (robust fallback for migration/old data)
        if not aeo and brand_name:
            aeo = session.query(AEOAnalysis).filter(AEOAnalysis.brand_url == brand_name).order_by(AEOAnalysis.created_at.desc()).first()
            
        if aeo:
            # Extract keywords from the query string (comma separated)
            keywords = [k.strip() for k in aeo.query.split(",") if k.strip()]
            return keywords
        return []
    except Exception as e:
        print(f"Error retrieving AEO keywords: {e}")
        return []
    finally:
        session.close()


def get_aeo_history(brand_id=None, brand_name=None, current_query=None, limit=10):
    """
    Retrieves historical AEO analysis metrics for plotting trends.
    Returns list of dicts: {date, visibility_score, rank_position}
    Filters by current_query to ensure trend consistency (apples-to-apples).
    """
    session = get_session()
    try:
        query = session.query(AEOAnalysis)
        
        if brand_id:
            query = query.filter(AEOAnalysis.brand_id == brand_id)
        elif brand_name:
             query = query.filter(AEOAnalysis.brand_url == brand_name)
             
        # Get historical runs (oldest first for charting)
        # We fetch MORE than the limit initially because filtering might reduce the count
        raw_history = query.order_by(AEOAnalysis.created_at.asc()).limit(limit * 3).all()
        
        data = []
        
        # Normalize current query for comparison
        normalized_current_query = None
        if current_query:
            # Simple normalization: lowercase and strip
            # Ideally we might sort words (e.g. "shoes running" == "running shoes") but standard string match is safer for now
            normalized_current_query = current_query.lower().strip()
            
        for h in raw_history:
            # 1. Filter by Query Consistency
            if normalized_current_query:
                # Handle cases where multiple keywords are stored (often comma separated)
                h_query = h.query.lower().strip() if h.query else ""
                
                # Check for match. We allow partial match if user is expanding query, but exact match is best for charts.
                # Decision: STRICT match for charts prevents "Socks" showing up in "Socks, Shoes" history which is good.
                if h_query != normalized_current_query:
                    continue
            
            # 2. Only include valid runs
            if h.visibility_score is not None:
                # Calculate Risk Score from JSON if possible
                risk_val = 0
                try:
                    if h.analysis_json:
                        res_data = json.loads(h.analysis_json)
                        # Re-calculate Risk logic: (Mentions in Risk Intents / Total Risk Queries) * 100
                        risk_mentions = 0
                        risk_total = 0
                        
                        for model, m_data in res_data.items():
                            if m_data.get("status") == "active":
                                for item in m_data.get("data", []):
                                    intent = item.get("intent", "General")
                                    if intent.startswith("Risk:"):
                                        risk_total += 1
                                        if item.get("analysis", {}).get("mentioned", False):
                                            risk_mentions += 1
                        
                        if risk_total > 0:
                            risk_val = round((risk_mentions / risk_total) * 100, 1)
                except:
                    pass

                data.append({
                    "date": h.created_at.strftime("%Y-%m-%d %H:%M"),
                    "visibility_score": h.visibility_score,
                    "rank_position": h.rank_position if h.rank_position else 0,
                    "risk_score": risk_val,
                    "analysis_json": h.analysis_json # Needed for leaderboard comparison? Only if we want deep diff
                })
        
        # Return only the requested limit, but from the filtered set
        return data[-limit:] 
        
    except Exception as e:
        print(f"Error retrieving AEO history: {e}")
        return []
    finally:
        session.close()
        







def get_brand_by_id(brand_id):
    """
    Get a specific brand analysis by ID.
    
    Args:
        brand_id: ID of the brand analysis
    
    Returns:
        Brand analysis record as dict
    """
    session = get_session()
    
    try:
        brand = session.query(BrandAnalysis).filter(BrandAnalysis.id == brand_id).first()
        
        if not brand:
            return None
        
        return {
            'id': brand.id,
            'url': brand.url,
            'title': brand.title,
            'created_at': brand.created_at.isoformat() if brand.created_at else None,
            'analysis_json': brand.analysis_json,
            'personas_json': brand.personas_json,
            'strategic_insights_json': brand.strategic_insights_json,
            'competitor_analysis_json': brand.competitor_analysis_json,
            'knowledge_graph_json': brand.knowledge_graph_json
        }
        
    except Exception as e:
        raise e
    finally:
        session.close()


def save_campaign(brand_id, name, goal=None, theme=None):
    """
    Save a campaign to the database.
    
    Args:
        brand_id: ID of the brand analysis
        name: Campaign name
        goal: Campaign goal (optional)
        theme: Campaign theme (optional)
    
    Returns:
        Campaign ID
    """
    session = get_session()
    
    try:
        campaign = Campaign(
            brand_id=brand_id,
            name=name,
            goal=goal,
            theme=theme
        )
        
        session.add(campaign)
        session.commit()
        campaign_id = campaign.id
        
        return campaign_id
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def get_campaigns(brand_id=None, limit=20):
    """
    Get campaigns, optionally filtered by brand_id.
    
    Args:
        brand_id: Optional brand ID to filter campaigns
        limit: Maximum number of records to return
    
    Returns:
        List of campaign records
    """
    session = get_session()
    
    try:
        query = session.query(Campaign)
        
        if brand_id:
            query = query.filter(Campaign.brand_id == brand_id)
        
        campaigns = query.order_by(Campaign.created_at.desc()).limit(limit).all()
        
        # Convert to dicts
        result = []
        for campaign in campaigns:
            result.append({
                'id': campaign.id,
                'brand_id': campaign.brand_id,
                'name': campaign.name,
                'goal': campaign.goal,
                'theme': campaign.theme,
                'created_at': campaign.created_at.isoformat() if campaign.created_at else None
            })
        
        return result
        
    except Exception as e:
        raise e
    finally:
        session.close()
