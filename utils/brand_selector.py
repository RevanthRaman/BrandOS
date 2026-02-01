"""
Brand Selector Utility
Provides Streamlit components for selecting brands and their associated URLs.
"""

import streamlit as st
from utils.brand_manager import get_all_brands, get_brand_urls, load_brand_data

def render_brand_selector(key_suffix="default"):
    """
    Renders a dropdown to select a brand from the database.
    Updates st.session_state.brand_data when a brand is selected.
    """
    brands = get_all_brands()
    
    if not brands:
        st.info("No brands found in database. Go to 'Brand Analysis' to add your first brand.")
        return None
    
    brand_options = {f"{b['name']} ({b['homepage_url']})": b['id'] for b in brands}
    
    selected_label = st.selectbox(
        "Select Brand",
        options=list(brand_options.keys()),
        key=f"brand_selector_{key_suffix}",
        help="Select a brand to load its intelligence profile."
    )
    
    brand_id = brand_options[selected_label]
    
    # Load brand data into session state if it's not already there or if it changed
    if "brand_data" not in st.session_state or st.session_state.brand_data.get("brand_id") != brand_id:
        with st.spinner(f"Loading {selected_label} profile..."):
            brand_data = load_brand_data(brand_id)
            if brand_data:
                st.session_state.brand_data = brand_data
                
                # NEW: Load latest AEO keywords for this brand
                from utils.db import get_latest_aeo_keywords
                db_keywords = get_latest_aeo_keywords(brand_id=brand_id, brand_name=brand_data['brand_name'])
                if db_keywords:
                    if "aeo_meta" not in st.session_state:
                        st.session_state.aeo_meta = {}
                    st.session_state.aeo_meta["keywords"] = db_keywords
                    st.toast(f"Loaded {len(db_keywords)} saved SEO keywords!", icon="🎯")
                
                st.toast(f"Loaded {brand_data['brand_name']} profile!", icon="🚀")
            else:
                st.error("Failed to load brand data.")
                return None
                
    return brand_id

def render_url_selector(brand_id, key_suffix="default"):
    """
    Renders a dropdown to select a URL from the brand's analyzed URLs.
    """
    if not brand_id:
        return None
        
    urls = get_brand_urls(brand_id)
    
    if not urls:
        st.warning("No URLs found for this brand.")
        return None
        
    url_options = [u['url'] for u in urls]
    
    selected_url = st.selectbox(
        "Select Page to Optimize",
        options=url_options,
        key=f"url_selector_{key_suffix}",
        help="Select which page of the brand you want to optimize."
    )
    
    return selected_url
