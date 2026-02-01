"""
Database migration module for Brand Management Platform upgrade.

This module creates new brand-centric tables and migrates existing data
from the old schema (single brand_analyses table) to the new schema
(brands, brand_urls, brand_analyses with unified profiles).
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint

# Load environment variables
load_dotenv()
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from urllib.parse import urlparse

Base = declarative_base()

# New schema models

class Brand(Base):
    """Core brand entity."""
    __tablename__ = 'brands'
    
    id = Column(Integer, primary_key=True)
    brand_name = Column(String, unique=True, nullable=False)
    homepage_url = Column(String)  # Main URL for brand
    logo_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    urls = relationship("BrandURL", back_populates="brand", cascade="all, delete-orphan")
    analyses = relationship("BrandAnalysisNew", back_populates="brand", cascade="all, delete-orphan")


class BrandURL(Base):
    """URLs analyzed for each brand."""
    __tablename__ = 'brand_urls'
    
    id = Column(Integer, primary_key=True)
    brand_id = Column(Integer, ForeignKey('brands.id', ondelete='CASCADE'), nullable=False)
    url = Column(String, nullable=False)
    page_type = Column(String)  # 'homepage', 'pricing', 'about', 'features', 'blog', 'other'
    scraped_at = Column(DateTime, default=datetime.utcnow)
    html_content = Column(Text)  # For design token extraction
    text_content = Column(Text)  # Scraped text
    
    # Relationships
    brand = relationship("Brand", back_populates="urls")
    
    # Unique constraint: one URL per brand
    __table_args__ = (UniqueConstraint('brand_id', 'url', name='_brand_url_uc'),)


class BrandAnalysisNew(Base):
    """Brand analysis with unified profile and individual page analyses."""
    __tablename__ = 'brand_analyses_new'
    
    id = Column(Integer, primary_key=True)
    brand_id = Column(Integer, ForeignKey('brands.id', ondelete='CASCADE'), nullable=False)
    
    # Unified brand profile (merged from all pages)
    unified_profile_json = Column(Text)  # Brand DNA, personas, strategy merged
    
    # Individual page analyses (preserved for reference)
    individual_analyses_json = Column(Text)  # {"url1": {...}, "url2": {...}}
    
    # Design tokens, knowledge graph, and imagery
    design_tokens_json = Column(Text)
    knowledge_graph_json = Column(Text)
    brand_imagery_json = Column(Text)  # {"logo": "...", "hero_images": ["...", "..."]}
    
    # Competitor analysis (if applicable)
    competitor_analysis_json = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    brand = relationship("Brand", back_populates="analyses")


def extract_brand_name_from_url(url):
    """
    Extract brand name from URL.
    Examples:
    - stripe.com → Stripe
    - www.twilio.com → Twilio
    - pricing.mailchimp.com → Mailchimp
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        
        # Remove www., pricing., etc.
        domain = domain.replace('www.', '').replace('pricing.', '').replace('blog.', '')
        
        # Get domain name (before .com/.org/etc)
        brand_name = domain.split('.')[0]
        
        # Capitalize
        brand_name = brand_name.capitalize()
        
        return brand_name
        
    except Exception as e:
        print(f"Error extracting brand name from {url}: {e}")
        return "Unknown Brand"


def migrate_data_to_new_schema(old_engine, new_engine, dry_run=True):
    """
    Migrates data from old schema to new schema.
    
    Args:
        old_engine: SQLAlchemy engine for old database
        new_engine: SQLAlchemy engine for new database (can be same)
        dry_run: If True, shows what would be migrated without committing
        
    Returns:
        Migration report dict
    """
    # Import old schema - handle both standalone and module import
    import sys
    from pathlib import Path
    
    # Add parent directory to path if running standalone
    if __name__ == "__main__":
        parent_dir = Path(__file__).parent.parent
        if str(parent_dir) not in sys.path:
            sys.path.insert(0, str(parent_dir))
    
    try:
        from utils.db import BrandAnalysis as OldBrandAnalysis
    except ImportError:
        # Fallback: try direct import from current location
        from db import BrandAnalysis as OldBrandAnalysis
    
    OldSession = sessionmaker(bind=old_engine)
    NewSession = sessionmaker(bind=new_engine)
    
    old_session = OldSession()
    new_session = NewSession()
    
    report = {
        "total_old_records": 0,
        "brands_created": 0,
        "urls_added": 0,
        "analyses_migrated": 0,
        "errors": []
    }
    
    try:
        # Get all old brand analyses
        old_brands = old_session.query(OldBrandAnalysis).all()
        report["total_old_records"] = len(old_brands)
        
        print(f"\n{'='*60}")
        print(f"MIGRATION REPORT (Dry Run: {dry_run})")
        print(f"{'='*60}\n")
        print(f"Found {len(old_brands)} old brand analysis records\n")
        
        for old_brand in old_brands:
            try:
                # Extract brand name from URL
                brand_name = extract_brand_name_from_url(old_brand.url)
                
                print(f"Processing: {old_brand.url} → Brand: {brand_name}")
                
                # Check if brand already exists in new schema
                existing_brand = new_session.query(Brand).filter(Brand.brand_name == brand_name).first()
                
                if existing_brand:
                    brand = existing_brand
                    print(f"  - Brand '{brand_name}' already exists (ID: {brand.id})")
                else:
                    # Create new brand
                    brand = Brand(
                        brand_name=brand_name,
                        homepage_url=old_brand.url,
                        created_at=old_brand.created_at
                    )
                    if not dry_run:
                        new_session.add(brand)
                        new_session.commit() # Commit brand first to ensure FKs work
                        # Refresh to keep the object in the new session
                        new_session.add(brand)
                    
                    report["brands_created"] += 1
                    print(f"  ✓ Created brand: {brand_name}")
                
                # Create BrandURL entry
                brand_url = BrandURL(
                    brand_id=brand.id if not dry_run else None,
                    url=old_brand.url,
                    page_type='homepage',  # Assume old records are homepage
                    scraped_at=old_brand.created_at,
                    text_content=None  # Old schema didn't store raw content
                )
                if not dry_run:
                    new_session.add(brand_url)
                
                report["urls_added"] += 1
                print(f"  ✓ Added URL: {old_brand.url}")
                
                # Migrate analysis data to new schema
                # Build unified profile from old data
                unified_profile = {
                    "analysis": json.loads(old_brand.analysis_json) if old_brand.analysis_json else {},
                    "personas": json.loads(old_brand.personas_json) if old_brand.personas_json else [],
                    "strategy": json.loads(old_brand.strategic_insights_json) if old_brand.strategic_insights_json else {}
                }
                
                # Individual analyses (just one URL in old schema)
                individual_analyses = {
                    old_brand.url: {
                        "analysis": json.loads(old_brand.analysis_json) if old_brand.analysis_json else {},
                        "personas": json.loads(old_brand.personas_json) if old_brand.personas_json else [],
                        "strategy": json.loads(old_brand.strategic_insights_json) if old_brand.strategic_insights_json else {},
                        "analyzed_at": old_brand.created_at.isoformat() if old_brand.created_at else None
                    }
                }
                
                # Create new analysis record
                new_analysis = BrandAnalysisNew(
                    brand_id=brand.id if not dry_run else None,
                    unified_profile_json=json.dumps(unified_profile),
                    individual_analyses_json=json.dumps(individual_analyses),
                    design_tokens_json=None,  # Will be extracted later
                    knowledge_graph_json=old_brand.knowledge_graph_json,
                    competitor_analysis_json=old_brand.competitor_analysis_json,
                    created_at=old_brand.created_at
                )
                if not dry_run:
                    new_session.add(new_analysis)
                    new_session.commit() # Commit analysis
                
                report["analyses_migrated"] += 1
                print(f"  ✓ Migrated analysis data")
                print()
                
            except Exception as e:
                new_session.rollback()
                error_msg = f"Failed to migrate {old_brand.url}: {str(e)}"
                report["errors"].append(error_msg)
                print(f"  ❌ ERROR: {error_msg}\n")
        
        # Final commitment (optional if we commit per item, but good for dry run logic)
        if not dry_run:
            print(f"\n{'='*60}")
            print("✅ Migration completed successfully!")
        else:
            print(f"\n{'='*60}")
            print("ℹ️  DRY RUN - No changes committed")
        
        print(f"{'='*60}\n")
        print("MIGRATION SUMMARY:")
        print(f"  - Old records processed: {report['total_old_records']}")
        print(f"  - Brands created: {report['brands_created']}")
        print(f"  - URLs added: {report['urls_added']}")
        print(f"  - Analyses migrated: {report['analyses_migrated']}")
        print(f"  - Errors: {len(report['errors'])}")
        
        if report['errors']:
            print("\nErrors encountered:")
            for error in report['errors']:
                print(f"  - {error}")
        
        print(f"\n{'='*60}\n")
        
        return report
        
    except Exception as e:
        new_session.rollback()
        raise e
    finally:
        old_session.close()
        new_session.close()


def create_new_schema(engine):
    """
    Creates new brand-centric tables.
    Safe to run multiple times (won't recreate existing tables).
    """
    print("Creating new schema tables...")
    Base.metadata.create_all(engine)
    print("✓ New schema created successfully!")


def get_session():
    """Get a database session for the new schema."""
    from sqlalchemy.orm import sessionmaker
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable not set")
    
    engine = create_engine(db_url, echo=False)
    Session = sessionmaker(bind=engine)
    return Session()



def run_migration(dry_run=True):
    """
    Main migration function.
    
    Args:
        dry_run: If True, simulates migration without committing
    """
    # Get database URL
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable not set")
    
    engine = create_engine(db_url, echo=False)
    
    print("\n" + "="*60)
    print("BRAND MANAGEMENT PLATFORM - DATABASE MIGRATION")
    print("="*60 + "\n")
    
    # Step 1: Create new schema
    create_new_schema(engine)
    
    # Step 2: Migrate data
    report = migrate_data_to_new_schema(engine, engine, dry_run=dry_run)
    
    return report


if __name__ == "__main__":
    import sys
    
    # Check for --commit flag
    commit = "--commit" in sys.argv
    
    if commit:
        print("\n⚠️  WARNING: Running migration with --commit flag!")
        print("This will modify your database.\n")
        response = input("Are you sure you want to proceed? (yes/no): ")
        if response.lower() != "yes":
            print("Migration cancelled.")
            sys.exit(0)
    
    # Run migration
    report = run_migration(dry_run=not commit)
    
    if not commit:
        print("\n💡 TIP: Run with --commit flag to actually apply changes")
        print("   python utils/db_migration.py --commit")
