
import streamlit as st
import uuid
import os
from dotenv import load_dotenv

# Load environment variables
# Load environment variables
load_dotenv()

import pandas as pd # Moved here to avoid NameError
import json

# Initialize Database
from utils.db import init_db, save_brand_analysis, save_optimization, save_asset, save_aeo_analysis, get_aeo_history
import utils.ai_engine as ai_engine
from utils.ai_engine import parse_json_response, generate_aeo_strategy
from utils.brand_manager import check_brand_exists, get_brand_urls, save_or_update_brand, load_brand_data, extract_brand_name_from_url, delete_brand, delete_brand_url, rename_brand, get_brand_stats, delete_aeo_analysis, delete_marketing_asset, delete_campaign, get_brand_aeo_reports, get_brand_assets
from utils.brand_selector import render_brand_selector, render_url_selector
from utils.url_suggester import suggest_common_urls
from utils.image_extractor import extract_brand_images
from utils.playbook_generator import generate_brand_playbook
import utils.pdf_generator as pdf_gen
try:
    init_db()
except Exception as e:
    st.error(f"Database Connection Error: {e}")

# Page Config
st.set_page_config(
    page_title="Brand Analysis & Optimization",
    page_icon="🚀",
    layout="wide"
)

import utils.ui as ui
import re

# Helper: Render Mermaid
def render_content_with_mermaid(content):
    """
    Parses content for ```mermaid blocks and renders them using HTML/JS.
    Splits the content and renders markdown and html components accordingly.
    """
    if "```mermaid" not in content:
        st.markdown(content)
        return

    # Split by mermaid blocks
    parts = re.split(r"```mermaid\s*(.*?)\s*```", content, flags=re.DOTALL)
    
    for i, part in enumerate(parts):
        if i % 2 == 0:
            # Even parts are normal markdown
            if part.strip():
                st.markdown(part)
        else:
            # Odd parts are mermaid code
            mermaid_code = part.strip()
            if mermaid_code:
                # Render Mermaid
                mermaid_html = f"""
                <div class="mermaid">
                {mermaid_code}
                </div>
                <script type="module">
                import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
                mermaid.initialize({{ startOnLoad: true, theme: 'dark' }});
                </script>
                """
                st.components.v1.html(mermaid_html, height=400, scrolling=True)

# Apply Premium UI Styles
ui.setup_app_styling()

# Sidebar Navigation
ui.setup_app_styling()

with st.sidebar:
    st.markdown('<div class="brand-os-logo">BrandOS</div>', unsafe_allow_html=True)
    st.write("") # Spacer
    
    # Custom Navigation (Styled as Tabs by CSS)
    selection = st.radio(
        "Navigation", 
        ["Brand Analysis", "AEO Analysis", "Brand Studio", "Content Optimizer", "Brand Management"],
        label_visibility="collapsed"
    )

# Model Configuration moved to individual pages


# --- PAGE ROUTING ---

# Duplicate header removed

    
    # ... (rest of Brand Analysis logic remains same, just ensuring indent is correct if needed)
    
    # Brand Selector (Reused across pages)
    

    
    # ... rest of code ...
    
    # [NOTE: Since I'm using replace_file_content, I need to match exact context. 
    # The user asked to rename 'Marketing Assets' to 'Brand Studio'. 
    # I will target the specific blocks.]






# Main Content

# Helper for Model Selection
def render_model_selector(key_suffix, default_model=ai_engine.GEMINI_3_PRO_PREVIEW):
    """
    Renders a select box for Gemini model selection using standardized constants.
    """
    model_options = [
        ai_engine.GEMINI_3_PRO_PREVIEW,
        ai_engine.GEMINI_2_5_PRO,
        ai_engine.GEMINI_3_FLASH_PREVIEW,
        ai_engine.GEMINI_2_5_FLASH,
        ai_engine.GEMINI_1_5_PRO,
        ai_engine.GEMINI_1_5_FLASH
    ]
    
    # Ensure default is in options or handle custom model
    if default_model not in model_options:
        model_options.insert(0, default_model)
        
    return st.selectbox(
        "Select AI Model",
        options=model_options,
        index=model_options.index(default_model) if default_model in model_options else 0,
        key=f"model_selector_{key_suffix}",
        help="Select the Gemini model. Higher-tier models provide better reasoning but may have stricter quota limits. The system will automatically fall back to lower-tier models if the selected one is unavailable."
    )

if selection == "Brand Analysis":
    st.header("🔍 Brand Analysis & DNA (Gemini 3 Powered)")
    st.caption("Deep-dive into your brand's digital soul.")
    
    # Simple Badge
    st.caption("⚡ Powered by **Gemini 3 Pro** (Deep Reasoner) & **Flash** (High Speed)")


    
    # Initialize session state for URLs if not exists
    if "brand_urls" not in st.session_state:
        st.session_state.brand_urls = [""]
    if "url_ids" not in st.session_state:
        st.session_state.url_ids = [str(uuid.uuid4())]

    # Function to add a new URL input
    def add_url():
        st.session_state.brand_urls.append("")
        st.session_state.url_ids.append(str(uuid.uuid4()))

    # Function to remove a URL input
    def remove_url(index):
        if len(st.session_state.brand_urls) > 1:
            st.session_state.brand_urls.pop(index)
            st.session_state.url_ids.pop(index)

    # Display URL Inputs
    st.subheader("Brand Management")
    
    from utils.brand_manager import get_all_brands, load_brand_data
    
    # Fetch all brands for dropdown
    all_brands = get_all_brands()
    options = ["➕ Create New Brand"] + [f"{b['name']} ({b['last_updated_relative']})" for b in all_brands]
    
    # Helper to find brand by display name
    def get_brand_id_by_option(option):
        for b in all_brands:
            if f"{b['name']} ({b['last_updated_relative']})" == option:
                return b['id']
        return None

    # Handle Selection
    selected_option = st.selectbox(
        "Select Brand", 
        options, 
        index=0, 
        key="brand_dropdown",
        help="Select an existing brand to view results or add new URLs. Choose 'Create New' to start fresh."
    )
    
    brand_name = ""
    
    if selected_option == "➕ Create New Brand":
        # New Brand Logic
        st.session_state.existing_brand_id = None
        
        # [Visual Improvement] Card-like container for new brand input
        st.markdown("""
        <div style="background-color:#f8f9fa; padding:1.5rem; border-radius:10px; border:1px solid #e9ecef; margin-bottom:1rem;">
            <p style="margin:0; font-weight:600; color:#495057;">✨ Start a New Analysis or Select an existing Brand from the Dropdown</p>
        </div>
        """, unsafe_allow_html=True)
        
        col_name, col_status = st.columns([3, 1])
        with col_name:
            # (Rest of name input logic)...
            # Auto-detect logic
            first_url = st.session_state.brand_urls[0] if st.session_state.brand_urls else ""
            if first_url and "brand_name_detected" not in st.session_state:
                default_brand_name = extract_brand_name_from_url(first_url)
                st.session_state.brand_name_detected = default_brand_name
            
            brand_name = st.text_input("Enter Brand Name", value=st.session_state.get("brand_name_detected", ""), placeholder="e.g., Stripe, Twilio")
            st.session_state.brand_name_input = brand_name
            
        # Check existence only if typed manually
        if brand_name:
             brand_id, _ = check_brand_exists(brand_name)
             if brand_id:
                 st.caption(f"⚠️ **{brand_name}** already exists in the database. Switches to 'Existing' mode recommended.")
                 st.session_state.existing_brand_id = brand_id

    else:
        # Existing Brand Logic
        selected_id = get_brand_id_by_option(selected_option)
        st.session_state.existing_brand_id = selected_id
        
        # Load Data IMMEDIATELY if not recently loaded or switched
        if selected_id:
            # Check if we need to load (prevent constant reloading if already active)
            if "brand_data" not in st.session_state or st.session_state.brand_data.get("db_id") != selected_id:
                with st.spinner("Loading Brand Profile..."):
                    loaded_data = load_brand_data(selected_id)
                    if loaded_data:
                        st.session_state.brand_data = loaded_data
                        brand_name = loaded_data['brand_name']
                        st.session_state.brand_name_input = brand_name # Sync input
                        
                        # Clear previous brand health to force recalculation
                        if "brand_health" in st.session_state:
                            del st.session_state.brand_health
                        
                        # Populate URLs from history - Ensure Homepage is First
                        all_urls = loaded_data.get('all_urls', [])
                        # Simple heuristic: If the brand homepage is known, put it first
                        home_url = loaded_data.get('url')
                        if home_url and home_url in all_urls:
                            all_urls.remove(home_url)
                            all_urls.insert(0, home_url)
                        
                        st.session_state.brand_urls = all_urls
                        st.session_state.url_ids = [str(uuid.uuid4()) for _ in all_urls]
                        
                        # Load Saved Competitor URL
                        comp_data = loaded_data.get('competitor', {})
                        if comp_data and 'url' in comp_data:
                            st.session_state.saved_competitor_url = comp_data['url']
                        else:
                             st.session_state.saved_competitor_url = ""
                        
                        st.toast(f"Loaded profile for {brand_name}", icon="📂")
                    else:
                        st.error("Failed to load brand data.")
            else:
                # Already loaded
                brand_name = st.session_state.brand_data['brand_name']

    # Delete actions moved to "Brand Management" tab

    # 2. Show existing URLs if brand exists (Refined UI)
    if brand_name and st.session_state.get("existing_brand_id"):
        existing_urls_db = get_brand_urls(st.session_state.existing_brand_id)
        if existing_urls_db:
             with st.expander(f"🗂️  Analyzed Pages ({len(existing_urls_db)})", expanded=False):
                for u in existing_urls_db:
                    ucol1, ucol2 = st.columns([9, 1])
                    with ucol1:
                        st.markdown(f"`{u['url']}` <span style='color:#888; font-size:0.8em'>({u['page_type']})</span>", unsafe_allow_html=True)
                    with ucol2:
                        if st.button("✕", key=f"del_url_{u['url']}", help=f"Remove {u['url']} from history"):
                            if delete_brand_url(st.session_state.existing_brand_id, u['url']):
                                st.toast("URL removed")
                                # Reload data to reflect change?
                                st.rerun()

    st.markdown("---")
    st.subheader("Analyze New URLs")
    st.caption("Add the homepage and other key pages (e.g., About, Pricing, Products) for a comprehensive analysis.")

    # Quick Add / Scan Feature
    col_scan, col_add = st.columns([3, 1])
    with col_scan:
        if st.button("🕵️ Scan Homepage for Key Links"):
            homepage = st.session_state.brand_urls[0]
            if not homepage:
                st.warning("Please enter the Homepage URL in the first box first.")
            else:
                with st.spinner(f"Scanning {homepage} and analyzing structure with Gemini 3 Flash..."):
                    import requests
                    from utils.scraper import extract_nav_links
                    
                    try:
                        resp = requests.get(homepage, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10, verify=True)
                        # 1. Raw Extraction
                        raw_links = extract_nav_links(homepage, resp.content)
                        
                        if raw_links:
                            # 2. AI Refinement (Gemini 3 Flash)
                            refined_links = ai_engine.refine_scanned_links(raw_links)
                            
                            st.session_state.suggested_links = refined_links
                            st.toast(f"Found {len(refined_links)} relevant links!", icon="✅")
                        else:
                            st.info("No obvious navigation links found. Try adding them manually.")
                    except Exception as e:
                        st.error(f"Could not scan homepage: {e}")

    # Display Suggested Links if any
    if "suggested_links" in st.session_state and st.session_state.suggested_links:
        
        # --- LOGIC TO MERGE & DEDUPLICATE LINKS ---
        # 1. Start with Scanned Links (High Priority)
        scanned_links = st.session_state.suggested_links
        
        # 2. Get Standard Suggestions
        homepage = st.session_state.brand_urls[0]
        standard_suggestions = suggest_common_urls(homepage)
        
        # 3. Deduplication Helper
        from urllib.parse import urlparse
        
        def normalize_for_comparison(url):
            try:
                parsed = urlparse(url)
                # Ignore scheme and www, clear trailing slash
                path = parsed.path.rstrip('/')
                return path
            except:
                return url
        
        # Create a set of existing paths from scanned links
        existing_paths = set()
        for l in scanned_links:
            existing_paths.add(normalize_for_comparison(l['url']))
            
        # Merge: Only add standard suggestion if path not already covered
        final_links = scanned_links.copy()
        
        for std in standard_suggestions:
            std_path = normalize_for_comparison(std['url'])
            # Check for path match OR exact label match (to avoid duplicate "About Us" pointing to slightly diff URLs)
            is_dup = False
            
            if std_path in existing_paths:
                is_dup = True
            
            # Label check (simple)
            if not is_dup:
                for l in final_links:
                    if l['label'].lower() == std['label'].lower():
                        is_dup = True
                        break
            
            if not is_dup:
                final_links.append(std)
                
        # --- END MERGE LOGIC ---

        st.markdown("##### 💡 Detected & Suggested Key Pages")
        st.caption("We found these pages (or think they might exist). Click to add them to your analysis.")
        
        # Group by category
        links_by_cat = {"Company": [], "Offerings": [], "Resources": [], "Other": []}
        for link in final_links:
            cat = link.get('category', 'Other')
            if cat in links_by_cat:
                links_by_cat[cat].append(link)
            else:
                links_by_cat["Other"].append(link)
        
        # Helper to add link
        def add_link_to_state(url):
            if url not in st.session_state.brand_urls:
                if "" in st.session_state.brand_urls:
                    idx = st.session_state.brand_urls.index("")
                    st.session_state.brand_urls[idx] = url
                    # ID already exists for this slot, no need to update
                else:
                    st.session_state.brand_urls.append(url)
                    st.session_state.url_ids.append(str(uuid.uuid4()))

        # "Add All Core" Button Logic
        core_links = []
        for cat in ["Company", "Offerings", "Resources"]:
            core_links.extend(links_by_cat[cat])
            
        if st.button("⚡ Bulk Add All Suggested", type="primary"):
            for l in core_links:
                add_link_to_state(l['url'])
            st.rerun()

        # Display Columns
        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        
        with c1:
            st.markdown("**🏢 Company**")
            for link in links_by_cat["Company"]:
                if st.button(f"➕ {link['label']}", key=f"add_{link['url']}"):
                    add_link_to_state(link['url'])
                    st.rerun()
                    
        with c2:
            st.markdown("**📦 Offerings**")
            for link in links_by_cat["Offerings"]:
                if st.button(f"➕ {link['label']}", key=f"add_{link['url']}"):
                    add_link_to_state(link['url'])
                    st.rerun()

        with c3:
            st.markdown("**📚 Resources & Other**")
            for link in links_by_cat["Resources"] + links_by_cat["Other"]:
                if st.button(f"➕ {link['label']}", key=f"add_{link['url']}"):
                    add_link_to_state(link['url'])
                    st.rerun()

    # Render Dynamic Inputs
    # Sync IDs safety check
    if "url_ids" not in st.session_state:
        st.session_state.url_ids = [str(uuid.uuid4()) for _ in st.session_state.brand_urls]
        
    while len(st.session_state.url_ids) < len(st.session_state.brand_urls):
        st.session_state.url_ids.append(str(uuid.uuid4()))
        
    # Trim if too many IDs
    if len(st.session_state.url_ids) > len(st.session_state.brand_urls):
        st.session_state.url_ids = st.session_state.url_ids[:len(st.session_state.brand_urls)]

    for i, (url, uid) in enumerate(zip(st.session_state.brand_urls, st.session_state.url_ids)):
        col1, col2 = st.columns([9, 1])
        with col1:
            st.session_state.brand_urls[i] = st.text_input(f"URL {i+1}", value=url, placeholder="https://example.com/page", key=f"url_input_{uid}")
        with col2:
            if i > 0: # Don't allow removing the first one easily to keep UI clean
                # Use UID for key to avoid button state collision
                if st.button("🗑️", key=f"remove_{uid}"):
                    remove_url(i)
                    st.rerun()
    
    if st.button("➕ Add Another URL"):
        add_url()
        st.rerun()

    # Competitor URL (Optional)
    comp_url_val = st.session_state.get("saved_competitor_url", "")
    competitor_url = st.text_input("Enter Competitor URL (Optional - for Battle Card)", value=comp_url_val, placeholder="e.g., https://www.competitor.com")

    st.markdown("---")

    if st.button("Analyze Brand", type="primary"):
        # Filter empty URLs
        valid_urls = [u for u in st.session_state.brand_urls if u.strip()]
        
        if not valid_urls:
            st.warning("Please enter at least one URL.")
        else:
            with st.spinner(f"🚀 Analyzing {len(valid_urls)} pages with Gemini 3 Pro (This might take ~30s for deep reasoning)..."):
                from utils.scraper import scrape_website
                import concurrent.futures
                
                aggregated_text = ""
                successful_scrapes = 0
                failed_urls = []
                scraped_texts = {} # Store individual texts
                competitor_text = None # Competitor content
                
                # Progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # 1. Parallel Scraping
                status_text.text("Scraping pages in parallel...")
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    # Map URLs to future objects
                    future_to_url = {executor.submit(scrape_website, url): url for url in valid_urls}
                    
                    # Add Competitor Scrape if provided
                    future_competitor = None
                    if competitor_url:
                        future_competitor = executor.submit(scrape_website, competitor_url)
                    
                    results = {}
                    for i, future in enumerate(concurrent.futures.as_completed(future_to_url)):
                        url = future_to_url[future]
                        try:
                            data = future.result()
                            results[url] = data
                        except Exception as exc:
                            results[url] = {"status": "error", "message": str(exc), "text": ""}
                        
                        progress_bar.progress((i + 1) / len(valid_urls) * 0.3)
                    
                    # Handle Competitor Result
                    if future_competitor:
                        try:
                            comp_data = future_competitor.result()
                            if comp_data.get("status") == "success":
                                competitor_text = f"COMPETITOR ({competitor_url}):\n{comp_data['text']}"
                            else:
                                st.warning(f"Could not scrape competitor: {comp_data.get('message')}")
                        except Exception as e:
                            st.warning(f"Competitor scrape failed: {e}")
                
                # Process Results
                main_scrape_data = None
                
                for url in valid_urls: # Maintain order
                    data = results.get(url, {})
                    if data.get("status") == "success":
                        successful_scrapes += 1
                        aggregated_text += f"\n\n--- CONTENT FROM: {url} ---\n{data['text']}\n"
                        scraped_texts[url] = data["text"]
                        
                        # Use first successful URL as main for metadata
                        if main_scrape_data is None:
                            main_scrape_data = data
                    else:
                        failed_urls.append(f"{url} ({data.get('message', 'Unknown error')})")
                        scraped_texts[url] = ""
                
                if successful_scrapes > 0:
                    if failed_urls:
                        st.warning(f"⚠️ Could not access the following URLs (skipped): {', '.join(failed_urls)}")
                    
                    if main_scrape_data is None:
                         main_scrape_data = {"url": valid_urls[0], "title": "Brand Analysis", "status": "success", "text": aggregated_text}

                    # 2. Analyze Aggregated Content (Single Shot)
                    status_text.text("Running Deep Brand Audit (Gemini 3 Pro)...")
                    progress_bar.progress(0.4)
                    
                    # Call the massive Combined Analysis
                    analysis_result_str = ai_engine.analyze_brand_complete(
                        aggregated_text, 
                        competitor_content=competitor_text,
                        raw_html=main_scrape_data.get("html_content", "")
                    )
                    progress_bar.progress(0.6)
                    status_text.text("Merging with existing brand intelligence...")
                    
                    # Parse the unified JSON
                    unified_data = parse_json_response(analysis_result_str)
                    
                    if not unified_data:
                        st.error("AI Analysis failed to return valid JSON. Please try again.")
                        # Fallback empty structure
                        unified_data = {"analysis": {}, "personas": [], "strategy": {}}
                    
                    # --- NEW: Cumulative Merge Logic ---
                    if st.session_state.get("existing_brand_id"):
                        try:
                            # Load existing data
                            existing_brand_data = load_brand_data(st.session_state.existing_brand_id)
                            if existing_brand_data:
                                existing_profile = {
                                    "analysis": existing_brand_data.get("analysis", {}),
                                    "personas": existing_brand_data.get("personas", []),
                                    "strategy": existing_brand_data.get("strategic", {})
                                }
                                
                                # Merge insights using AI
                                merged_profile_str = ai_engine.merge_brand_insights(
                                    existing_profile,
                                    unified_data,
                                    ", ".join(valid_urls)
                                )
                                unified_data = parse_json_response(merged_profile_str)
                                st.toast("Merged new insights with existing brand DNA!", icon="🧠")
                        except Exception as merge_err:
                            st.error(f"Merge Error: {merge_err}")
                    
                    analysis_json = unified_data.get("analysis", {})
                    personas_json = unified_data.get("personas", [])
                    strategic_json = unified_data.get("strategy", {})
                    competitor_json = unified_data.get("competitor_analysis", {})
                    
                    # Store Competitor URL in the JSON for future retrieval
                    if competitor_json and competitor_url:
                        competitor_json["url"] = competitor_url
                    
                    # 5. Extract Visual DNA (Hard Lock)
                    status_text.text("Extracting Design Tokens (Visual DNA)...")
                    design_tokens = {}
                    try:
                        from utils.design_extractor import extract_design_tokens
                        if main_scrape_data.get("html_content"):
                            design_tokens = extract_design_tokens(main_scrape_data["html_content"], main_scrape_data["url"])
                    except Exception as dt_err:
                        print(f"Design token extraction failed: {dt_err}")

                    # Store in Session State
                    st.session_state.brand_data = {
                        "brand_name": brand_name,
                        "url": main_scrape_data["url"], 
                        "all_urls": valid_urls,
                        "scrape": main_scrape_data,
                        "individual_scrapes": scraped_texts,
                        "individual_htmls": {u: results.get(u, {}).get("html_content", "") for u in valid_urls}, # New field
                        "analysis": analysis_json,
                        "personas": personas_json,
                        "strategic": strategic_json,
                        "competitor": competitor_json,
                        "competitor_content": competitor_text if competitor_text else None,  # Store for keyword gap
                        "knowledge_graph": {}, # Legacy placeholder
                        "design_tokens": design_tokens, # Hard Lock Tokens
                        "db_id": None
                    }
                    
                    # 3. Extract Detailed Knowledge Graph (Products, Features, Benefits)
                    status_text.text("Extracting Detailed Knowledge Graph...")
                    kg_raw = ai_engine.extract_brand_knowledge(aggregated_text)
                    kg_json = parse_json_response(kg_raw)
                    
                    if not kg_json:
                        # Fallback if KG extraction fails
                        kg_json = {
                            "products": [{"name": p, "features": [], "benefits": []} for p in analysis_json.get("primary_products", [])],
                            "key_terms": analysis_json.get("brand_values", [])
                        }

                    # 4. Extract Brand Imagery (New)
                    status_text.text("Capturing Brand Imagery (Logo/Hero)...")
                    brand_imagery = {}
                    if main_scrape_data.get("html_content"):
                        brand_imagery = extract_brand_images(main_scrape_data["html_content"], main_scrape_data["url"])


                    
                    # Save to DB (New Schema)
                    try:
                        urls_data = []
                        for url in valid_urls:
                            urls_data.append({
                                'url': url,
                                'text': scraped_texts.get(url, ""),
                                'html': results.get(url, {}).get("html_content", ""),
                                'page_type': 'homepage' if url == main_scrape_data["url"] else 'other'
                            })
                            
                        brand_id = save_or_update_brand(
                            brand_name,
                            urls_data,
                            unified_data,
                            design_tokens=design_tokens, # NOW ACTIVE: Hard Lock Tokens
                            knowledge_graph=kg_json,
                            competitor_analysis=competitor_json,
                            brand_imagery=brand_imagery # New field
                        )
                        st.session_state.brand_data["db_id"] = brand_id
                        st.session_state.brand_data["knowledge_graph"] = kg_json
                        st.session_state.brand_data["brand_imagery"] = brand_imagery
                        
                        # Generate Playbook for export
                        playbook_md = generate_brand_playbook(st.session_state.brand_data)
                        st.session_state.brand_data["playbook_md"] = playbook_md
                        
                        st.toast("Brand Intelligence updated!", icon="💾")
                    except Exception as e:
                        st.error(f"Failed to save to DB: {e}")
                    
                    progress_bar.progress(1.0)
                    status_text.text("Complete!")
                    st.success("Brand Audit Complete!")
                    
                    # Add Download Button for Playbook
                    if "playbook_md" in st.session_state.brand_data:
                        st.download_button(
                            "📥 Download Full Brand Playbook (Markdown)",
                            st.session_state.brand_data["playbook_md"],
                            f"{brand_name}_Playbook.md",
                            "text/markdown",
                            use_container_width=True
                        )
                        
                    st.session_state.scrape_error = None 
                else:
                    st.error("All URLs failed to scrape. Please check the URLs or try manual input.")
                    st.session_state.scrape_error = "All URLs failed."

    # Manual Fallback
    if "scrape_error" in st.session_state and st.session_state.scrape_error:
        st.warning("⚠️ The website seems to have strict anti-bot protection. Please copy and paste the text content manually below.")
        manual_text = st.text_area("Paste Website Content", height=300)
        
        if st.button("Analyze Manual Text"):
            if not manual_text:
                st.warning("Please paste some text.")
            else:
                with st.spinner("Analyzing manual content..."):
                    # Using global ai_engine
                    
                    # Mock scrape data
                    scrape_data = {
                        "url": "Manual Input",
                        "title": "Manual Input",
                        "text": manual_text,
                        "meta_description": "Manual input",
                        "og_image": None,
                        "status": "success"
                    }
                    
                    analysis_json = ai_engine.analyze_brand_content(manual_text)
                    personas_json = ai_engine.generate_personas(manual_text)
                    strategic_json = ai_engine.generate_strategic_insights(manual_text)
                    
                    st.session_state.brand_data = {
                        "url": "Manual Input",
                        "scrape": scrape_data,
                        "analysis": analysis_json,
                        "personas": personas_json,
                        "db_id": None
                    }
                    
                    # Save (optional, might skip saving manual input or save with flag)
                    try:
                        brand_id = save_brand_analysis("Manual Input", "Manual Input", analysis_json, personas_json, strategic_json)
                        st.session_state.brand_data["db_id"] = brand_id
                    except:
                        pass
                        
                    st.success("Analysis Complete!")
                    st.session_state.scrape_error = None
                    st.rerun()

    if "brand_data" in st.session_state and st.session_state.brand_data:
        data = st.session_state.brand_data
        
        # Display Logic
        import json
        import plotly.graph_objects as go
        import re
        
        # [Removed duplicate Brand Health rendering block]

        
        st.markdown("---")
        
        # Validation: Check for errors in the AI response
        if isinstance(data, dict) and "error" in data:
            st.error(f"Analysis Failed: {data['error']}")
            st.warning("Please try again later or check your API Key / Quota.")
            st.stop()
        elif "analysis" not in data or not data["analysis"]:
             st.error("Analysis returned empty results. This may be due to content length or AI model availability.")
             st.stop()

        # --- Brand DNA Section ---
        st.markdown('<p class="section-header">🧬 Brand DNA</p>', unsafe_allow_html=True)
        
        try:
            # data["analysis"] is already a dict from the main unified parse
            dna = data["analysis"]
            if isinstance(dna, str): # Fallback if it somehow remained a string
                dna = parse_json_response(dna)
            if not dna:
                dna = {}
                st.warning("Could not parse Brand DNA data.")
            
            # Top Row: Archetype & Voice with Consistent Styling (Matching Mission/Vision)
            col_dna_1, col_dna_2 = st.columns(2)
            with col_dna_1:
                 st.markdown(f"""
                <div class="metric-card">
                    <h4 style="color:#667eea; margin:0 0 0.5rem 0;">🎭 Brand Archetype</h4>
                    <p style="margin:0; font-style:italic;">{dna.get('brand_archetype', 'N/A')}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col_dna_2:
                st.markdown(f"""
                <div class="metric-card">
                    <h4 style="color:#667eea; margin:0 0 0.5rem 0;">🎤 Brand Voice</h4>
                    <p style="margin:0; font-style:italic;">{dna.get('brand_voice', 'N/A')}</p>
                </div>
                """, unsafe_allow_html=True)

            # Strategic Narrative cards (Row 2) - [NEW] Enemy & Cause
            col1, col2 = st.columns(2)
            with col1:
                # Fallback to Mission if Enemy not present (backward compatibility)
                enemy = dna.get('brand_enemy') or dna.get('brand_mission')
                title_enemy = "⚔️ The Enemy" if dna.get('brand_enemy') else "🎯 Mission"
                
                if enemy:
                    st.markdown(f"""
                    <div class="metric-card">
                        <h4 style="color:#e53e3e; margin:0 0 0.5rem 0;">{title_enemy}</h4>
                        <p style="margin:0; font-style:italic;">{enemy}</p>
                    </div>
                    """, unsafe_allow_html=True)
            with col2:
                # Fallback to Vision if Noble Cause not present
                cause = dna.get('brand_noble_cause') or dna.get('brand_vision')
                title_cause = "🚀 The Noble Cause" if dna.get('brand_noble_cause') else "🔮 Vision"
                
                if cause:
                    st.markdown(f"""
                    <div class="metric-card">
                        <h4 style="color:#38a169; margin:0 0 0.5rem 0;">{title_cause}</h4>
                        <p style="margin:0; font-style:italic;">{cause}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
            st.markdown("<br>", unsafe_allow_html=True)
            
            # --- Visual DNA (New) ---
            # --- Visual DNA (New) ---
            # --- Visual DNA (New) ---
            visual = dna.get("visual_identity", {})
            design_tokens = data.get("design_tokens", {})
            
            # Robust Merge: If AI failed to get palette but we have design tokens, use them
            if not visual.get("primary_palette") and design_tokens:
                if "primary_palette" not in visual: visual["primary_palette"] = []
                
                if design_tokens.get("primary_color"):
                    visual["primary_palette"].append(design_tokens["primary_color"])
                if design_tokens.get("secondary_color"):
                    visual["primary_palette"].append(design_tokens["secondary_color"])
                if design_tokens.get("accent_colors"):
                    visual["primary_palette"].extend(design_tokens["accent_colors"][:3])
            
            # Fallback for Vibe
            if not visual.get("visual_vibe"):
                 scheme = design_tokens.get('color_scheme', 'Modern')
                 visual["visual_vibe"] = f"{scheme.title()} Aesthetic"

            # Final Fallback to prevent empty section
            if not visual:
                 visual = {"visual_vibe": "Standard Professional", "primary_palette": ["#333333", "#555555"]}

            if visual:
                st.markdown("#### 🎨 Visual DNA")
                
                v_col1, v_col2 = st.columns([1, 2])
                
                with v_col1:
                    # Palette
                    st.caption("Primary Palette")
                    palette_html = '<div style="display:flex; gap:10px; margin-bottom:5px;">'
                    for color in visual.get("primary_palette", []):
                            palette_html += f'<div style="width:40px; height:40px; background-color:{color}; border-radius:50%; border:1px solid #ddd; box-shadow: 0 2px 4px rgba(0,0,0,0.1);" title="{color}"></div>'
                    palette_html += '</div>'
                    st.markdown(palette_html, unsafe_allow_html=True)
                    st.markdown(f"<span style='font-size:0.8rem; color:#666;'>{' '.join(visual.get('primary_palette', []))}</span>", unsafe_allow_html=True)
                    
                with v_col2:
                        st.info(f"**Visual Vibe:** {visual.get('visual_vibe', 'N/A')}")
                        st.caption(f"**Imagery Sentiment:** {visual.get('image_sentiment', 'N/A')}")

                # Brand Disconnect Check (Simple Heuristics)
                brand_voice = dna.get('brand_voice', '').lower()
                visual_vibe = visual.get('visual_vibe', '').lower()
                
                if ("playful" in brand_voice and "corporate" in visual_vibe) or \
                   ("modern" in brand_voice and "outdated" in visual_vibe):
                    st.error("⚠️ **Brand Disconnect Detected:** Your Visual Identity conflicts with your Brand Voice.")
                
                st.markdown("<br>", unsafe_allow_html=True)

                # Show Screenshot if available
                if "screenshot_data" in st.session_state and st.session_state.screenshot_data:
                     with st.expander("📸 View What the AI Saw", expanded=False):
                         st.image(st.session_state.screenshot_data, caption="Website Visual Analysis Source", use_container_width=True)
        except Exception as e:
             st.warning(f"Could not display complete Brand DNA: {e}")

        # --- Brand Health Dashboard (New Feature) ---
        st.markdown('<p class="section-header">📊 Brand Health Dashboard</p>', unsafe_allow_html=True)
        
        # Calculate brand health if not already done
        if "brand_health" not in st.session_state or not st.session_state.get("brand_health"):
            with st.spinner("Calculating brand health metrics..."):
                health_result = ai_engine.calculate_brand_health(
                    data["analysis"], 
                    data["personas"],
                    data.get("strategic", None)
                )
                st.session_state.brand_health = health_result
        
        try:
            if isinstance(st.session_state.brand_health, str):
                health_data = parse_json_response(st.session_state.brand_health)
            else:
                health_data = st.session_state.brand_health
            
            if not health_data:
                health_data = {} 
                
            # Check for API Error in the response
            if "error" in health_data:
                st.warning(f"⚠️ Brand Health could not be calculated: {health_data['error']}")
                if st.button("🔄 Retry Health Calculation"):
                    del st.session_state.brand_health
                    st.rerun()
            else:
                overall_score = health_data.get("overall_health_score", 0)
                
                st.markdown(f"""
                <div style="text-align:center; background:linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding:2rem; border-radius:15px; margin-bottom:2rem; color:white;">
                    <h3 style="margin:0; color:white;">Overall Brand Health</h3>
                    <div class="health-score">{overall_score}/100</div>
                    <div style="width:80%; margin:1rem auto; background:rgba(255,255,255,0.3); height:20px; border-radius:10px;">
                        <div style="width:{overall_score}%; background:white; height:100%; border-radius:10px;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("#### 📌 Key Metrics")
                metrics = health_data.get("metrics", {})
                
                if not metrics:
                     st.info("No detailed metrics available.")
                else:
                    cols = st.columns(4)
                    for idx, (metric_name, metric_info) in enumerate(metrics.items()):
                        with cols[idx]:
                            score = metric_info.get("score", 0)
                            desc = metric_info.get("description", "")
                            
                            if score >= 80: color = "#27ae60"
                            elif score >= 60: color = "#f39c12"
                            else: color = "#e74c3c"
                            
                            st.markdown(f"""
                            <div class="metric-card" style="border-left:4px solid {color}; min-height:150px;">
                                <h4 style="margin:0 0 0.5rem 0; color:{color}; text-transform:capitalize;">{metric_name.replace('_', ' ')}</h4>
                                <div style="font-size:2rem; font-weight:700; color:{color};">{score}</div>
                                <p style="font-size:0.85rem; color:#666; margin-top:0.5rem;">{desc}</p>
                            </div>
                            """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                st.markdown("""
                <div class="metric-card" style="border-left:4px solid #f39c12; background:linear-gradient(to right, #fff9e6 0%, white 100%);">
                    <h4 style="color:#f39c12; margin:0 0 1rem 0;">🚀 Strategic Recommendations</h4>
                </div>
                """, unsafe_allow_html=True)
                
                # Support "strategic_recommendations" (New) or fallback to merging "quick_wins" + "improvement_areas"
                recs = health_data.get("strategic_recommendations", [])
                if not recs:
                    # Fallback merge
                    recs = health_data.get("quick_wins", []) + health_data.get("improvement_areas", [])
                
                if recs:
                    for rec in recs:
                        st.markdown(f"""
                        <div style="padding:0.8rem; margin:0.5rem 0; background:white; border-radius:6px; border-left:3px solid #f39c12; box-shadow:0 1px 3px rgba(0,0,0,0.1);">
                            🚀 {rec}
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No specific recommendations generated.")
            
        except Exception as e:
            st.warning(f"Could not display brand health dashboard: {e}")
            if st.button("🔄 Force Retry", key="retry_health_except"):
                 if "brand_health" in st.session_state:
                     del st.session_state.brand_health
                 st.rerun()

        # --- Strategic Insights Section (New) ---
        if "strategic" in data:
            st.markdown("---")
            st.subheader("🧠 Strategic Insights")
            try:
                # data["strategic"] is already a dict
                strat = data["strategic"]
                if isinstance(strat, str):
                    strat = parse_json_response(strat)
                if not strat:
                    strat = {}
                
                st.markdown(f"**Market Positioning:** {strat.get('market_positioning', 'N/A')}")
                
                st.markdown("#### SWOT Analysis")
                swot = strat.get('swot_analysis', {})
                
                col1, col2 = st.columns(2)
                with col1:
                    st.success(f"**Strengths**\n\n" + "\n".join([f"- {s}" for s in swot.get('strengths', [])]))
                    st.warning(f"**Weaknesses**\n\n" + "\n".join([f"- {w}" for w in swot.get('weaknesses', [])]))
                with col2:
                    st.info(f"**Opportunities**\n\n" + "\n".join([f"- {o}" for o in swot.get('opportunities', [])]))
                    st.error(f"**Threats**\n\n" + "\n".join([f"- {t}" for t in swot.get('threats', [])]))
                    
                st.markdown("#### Competitor Differentiation")
                st.caption("ℹ️ These points are inferred by the AI based on your brand's unique value propositions compared to standard market expectations.")
                for diff in strat.get('competitor_differentiation', []):
                    st.markdown(f"🔹 {diff}")
                    
            except Exception as e:
                st.warning(f"Could not display strategic insights: {e}")
                st.text(data["strategic"])

        # --- Competitor Battle Card Section (New) ---
        # --- Competitor Battle Card Section (New) ---
        # Fixed: Check if competitor data exists, not just "the_wedge" which is now in strategic
        if "competitor" in data and data["competitor"]:
            st.markdown("---")
            st.markdown('<p class="section-header">⚔️ Competitor Battle Card</p>', unsafe_allow_html=True)
            comp = data["competitor"]
            strat = data.get("strategic", {})
            
            # 1. The Wedge (Hero Section) - Source from Strategic
            wedge_text = strat.get('the_wedge') or comp.get('the_wedge', 'N/A')
            
            wedge_html = f"""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 12px; color: white; margin-bottom: 2rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <h3 style="margin:0 0 0.5rem 0; color:white; font-size:1.5rem;">🗡️ The Wedge (Winning Strategy)</h3>
                <p style="font-size:1.2rem; font-weight:500; line-height:1.6; margin:0;">{wedge_text}</p>
            </div>
            """
            st.markdown(wedge_html, unsafe_allow_html=True)
            
            # 2. Head-to-Head Comparison
            if "comparison_table" in comp:
                st.markdown("#### 🆚 Head-to-Head Comparison")
                st.caption("Direct feature-by-feature comparison.")
                
                # Header
                h1, h2, h3 = st.columns([1.2, 1.5, 1.5])
                h1.markdown("**Feature**")
                h2.markdown(f"**✅ Your Brand**")
                h3.markdown(f"**❌ Competitor**")
                st.markdown("<hr style='margin: 0.5rem 0; border: 0; border-top: 1px solid #eee;'>", unsafe_allow_html=True)
                
                # Rows
                for row in comp.get("comparison_table", []):
                    c1, c2, c3 = st.columns([1.2, 1.5, 1.5])
                    c1.markdown(f"**{row.get('feature', 'N/A')}**")
                    c2.markdown(f"<span style='color:#27ae60'>{row.get('my_brand', 'N/A')}</span>", unsafe_allow_html=True)
                    c3.markdown(f"<span style='color:#c0392b'>{row.get('competitor', 'N/A')}</span>", unsafe_allow_html=True)
                    st.markdown("<div style='border-bottom:1px solid #f0f0f0; margin:0.5rem 0'></div>", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # 3. Gap Analysis & Tactics (Re-aligned to 3 Columns)
            
            cc_1, cc_2, cc_3 = st.columns(3)
            
            with cc_1:
                # Competitor Advantages (Risks)
                st.markdown("#### ⚠️ Competitor Advantages")
                # st.caption("Areas where they currently win.")
                
                # Support both new split keys and legacy 'gap_analysis'
                comp_strengths = comp.get('competitor_strengths', [])
                
                # Check legacy if new key is empty
                if not comp_strengths and 'gap_analysis' in comp:
                     # Heuristic: If it looks negative, put it here (hard to do perfectly without AI)
                     # For now, just dump legacy gap_analysis here if present
                     comp_strengths = comp.get('gap_analysis', [])

                if comp_strengths:
                    for item in comp_strengths:
                        # Fix bold formatting in HTML
                        formatted_item = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', item)
                        st.markdown(f"""
                        <div style="padding:0.8rem; margin:0.5rem 0; background:#fff5f5; border-radius:6px; border-left:3px solid #e74c3c; font-size:0.9rem;">
                            📉 {formatted_item}
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No clear competitor advantages detected.")

            with cc_2:
                 # Our Differentiators (Wins)
                 st.markdown("#### ✅ My Differentiators")
                 # st.caption("Where we beat them.")
                 
                 our_diffs = comp.get('our_differentiators', [])
                 
                 if our_diffs:
                     for item in our_diffs:
                        # Fix bold formatting in HTML
                        formatted_item = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', item)
                        st.markdown(f"""
                        <div style="padding:0.8rem; margin:0.5rem 0; background:#f0f9f4; border-radius:6px; border-left:3px solid #27ae60; font-size:0.9rem;">
                            🏆 {formatted_item}
                        </div>
                        """, unsafe_allow_html=True)
                 else:
                     st.info("No distinct differentiators listed.")

            with cc_3:
                 # Tactical Advantage (Keep as requested)
                 st.markdown("#### 🚀 Tactical Advantage")
                 # Logic: Use explicit 'tactical_advantage' if present (back compat), else use first strategic recommendation
                 tactics = comp.get('tactical_advantage')
                 if not tactics and data.get("analysis", {}).get("strategic_recommendations"):
                     tactics = data["analysis"]["strategic_recommendations"][0]
                 elif not tactics:
                     tactics = "Analyze competitor gaps to find your tactical advantage."

                 st.markdown(f"""
                 <div style="padding:1rem; background:#eff6ff; border-radius:8px; border:1px solid #bfdbfe; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                    <strong style="color:#1e40af; display:block; margin-bottom:0.5rem;">Execute This Move:</strong>
                    <span style="color:#1e3a8a;">{tactics}</span>
                 </div>
                 """, unsafe_allow_html=True)

        # --- Knowledge Graph Section (New) ---
        if "knowledge_graph" in data and data["knowledge_graph"]:
            st.markdown("---")
            st.subheader("🧠 Brand Knowledge Graph")
            kg = data["knowledge_graph"]
            
            # Products
            if "products" in kg and kg["products"]:
                st.markdown("#### 📦 Products & Offerings")
                for prod in kg["products"]:
                    with st.expander(f"**{prod.get('name', 'Product')}**"):
                        st.write(prod.get('description', ''))
                        c1, c2 = st.columns(2)
                        with c1:
                            st.markdown("**Features:**")
                            for f in prod.get('features', []):
                                st.markdown(f"- {f}")
                        with c2:
                            st.markdown("**Benefits:**")
                            for b in prod.get('benefits', []):
                                st.markdown(f"- {b}")

            # Key Terms
            if "key_terms" in kg and kg["key_terms"]:
                st.markdown("#### 🔑 Key Terminology")
                st.markdown(", ".join([f"`{term}`" for term in kg["key_terms"]]))
            
            # Brand Colors
            if "brand_colors" in kg and kg["brand_colors"]:
                st.markdown("#### 🎨 Brand Colors (Inferred)")
                cols = st.columns(len(kg["brand_colors"]))
                for i, color in enumerate(kg["brand_colors"]):
                    with cols[i]:
                        st.markdown(f"<div style='background-color:{color};height:50px;border-radius:5px;'></div>", unsafe_allow_html=True)
                        st.caption(color)

        # --- Buyer Personas Section ---
        st.markdown("---")
        st.markdown('<p class="section-header">👥 Buyer Personas</p>', unsafe_allow_html=True)
        try:
            # data["personas"] is already a list
            personas = data["personas"]
            if isinstance(personas, str):
                personas = parse_json_response(personas)
            if not personas or not isinstance(personas, list):
                st.warning("Could not parse Personas data or invalid format.")
                personas = []
            
            if not personas:
                st.info("No detailed personas generated.")
                tabs = []
            else:
                tabs = st.tabs([p.get('role', f'Persona {i+1}') for i, p in enumerate(personas)])
            
            for i, tab in enumerate(tabs):
                with tab:
                    p = personas[i]
                    
                    # Persona Header Card
                    st.markdown(f"""
                    <div class="persona-card">
                        <h2 style="margin:0 0 1rem 0; color:#d04444;">{p.get('role', 'Unknown Role')}</h2>
                        <div style="background:white; padding:1rem; border-radius:8px; margin-top:1rem;">
                            <h4 style="margin:0; color:#666;">💡 Marketing Hook</h4>
                            <p style="margin:0.5rem 0 0 0; font-size:1.1rem; font-weight:600; color:#333;">{p.get('marketing_hook', 'N/A')}</p>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Preferences in Full Width Card
                    channels = p.get('preferred_channels', [])
                    content_prefs = p.get('content_preferences', [])
                    
                    channel_badges = ' '.join([f'<span style="display:inline-block; background:#667eea; color:white; padding:0.3rem 0.8rem; border-radius:12px; margin:0.2rem; font-size:0.85rem;">{ch}</span>' for ch in channels])
                    content_badges = ' '.join([f'<span style="display:inline-block; background:#764ba2; color:white; padding:0.3rem 0.8rem; border-radius:12px; margin:0.2rem; font-size:0.85rem;">{ct}</span>' for ct in content_prefs])
                    
                    st.markdown(f"""
                    <div class="metric-card">
                        <h4 style="color:#667eea; margin:0 0 1rem 0;">🎯 Preferences</h4>
                        <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 2rem;">
                            <div>
                                <strong style="display:block; margin-bottom:0.5rem;">Channels:</strong>
                                {channel_badges if channel_badges else '<span style="color:#999;">N/A</span>'}
                            </div>
                            <div>
                                <strong style="display:block; margin-bottom:0.5rem;">Content:</strong>
                                {content_badges if content_badges else '<span style="color:#999;">N/A</span>'}
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Pain Points & Goals
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("""
                        <div class="metric-card" style="border-left:4px solid #e74c3c;">
                            <h4 style="color:#e74c3c; margin:0 0 1rem 0;">😣 Pain Points</h4>
                        </div>
                        """, unsafe_allow_html=True)
                        for pain in p.get('pain_points', []):
                            st.markdown(f"""
                            <div style="padding:0.8rem; margin:0.5rem 0; background:#fff5f5; border-radius:6px; border-left:3px solid #e74c3c;">
                                {pain}
                            </div>
                            """, unsafe_allow_html=True)
                            
                    with col2:
                        st.markdown("""
                        <div class="metric-card" style="border-left:4px solid #27ae60;">
                            <h4 style="color:#27ae60; margin:0 0 1rem 0;">🎯 Goals</h4>
                        </div>
                        """, unsafe_allow_html=True)
                        for goal in p.get('goals', []):
                            st.markdown(f"""
                            <div style="padding:0.8rem; margin:0.5rem 0; background:#f0f9f4; border-radius:6px; border-left:3px solid #27ae60;">
                                {goal}
                            </div>
                            """, unsafe_allow_html=True)
                    
                    # Download Persona Sheet
                    st.markdown("<br>", unsafe_allow_html=True)
                    persona_sheet = f"""# {p.get('role', 'Persona')} - Persona Sheet

## Marketing Hook
{p.get('marketing_hook', 'N/A')}

## Preferred Channels
{chr(10).join([f'- {ch}' for ch in p.get('preferred_channels', [])])}

## Content Preferences
{chr(10).join([f'- {ct}' for ct in p.get('content_preferences', [])])}

## Pain Points
{chr(10).join([f'- {pain}' for pain in p.get('pain_points', [])])}

## Goals
{chr(10).join([f'- {goal}' for goal in p.get('goals', [])])}
"""
                    st.download_button(
                        f"📥 Download {p.get('role', 'Persona')} Sheet",
                        persona_sheet,
                        file_name=f"{p.get('role', 'persona').lower().replace(' ', '_')}_sheet.md",
                        mime="text/markdown",
                        key=f"download_persona_{i}",
                        use_container_width=True
                    )
                            
        except json.JSONDecodeError:
            st.error("Could not parse Personas JSON. Showing raw output.")
            st.text(data["personas"])
        except Exception as e:
            st.error(f"Error displaying Personas: {e}")
            st.text(data["personas"])



    st.markdown("---")


elif selection == "Content Optimizer":
    import utils.content_optimizer as content_optimizer
    
    # Ensure brand data is loaded
    if "brand_data" in st.session_state and st.session_state.brand_data:
        content_optimizer.render_content_optimizer(st.session_state.brand_data)
    else:
        st.warning("Please select a Brand in the sidebar first.")
        # Optional: Render brand selector here too if needed, but keeping it simple as per plan
        current_brand_id = render_brand_selector("content_opt")
        if current_brand_id and "brand_data" in st.session_state:
             content_optimizer.render_content_optimizer(st.session_state.brand_data)


elif selection == "AEO Analysis":
    st.header("🤖 AEO Analysis Dashboard")
    st.caption("Optimize your presence on AI Search Engines like ChatGPT, Perplexity, and Claude.")
    

    
    st.markdown("Quantify your brand's visibility across AI Answer Engines.")
    
    # API Configuration
    with st.expander("⚙️ API Configuration", expanded=False):
        st.info("Enter API keys here if not set in environment variables. Keys are not stored permanently.")
        openai_key = st.text_input("OpenAI API Key (ChatGPT)", type="password")
        anthropic_key = st.text_input("Anthropic API Key (Claude)", type="password")
        perplexity_key = st.text_input("Perplexity API Key", type="password")
        gemini_key = st.text_input("Gemini API Key", type="password")
        
        api_keys = {
            "openai": openai_key,
            "anthropic": anthropic_key,
            "perplexity": perplexity_key,
            "gemini": gemini_key
        }

    # Select Brand for AEO
    # Select Brand for AEO
    current_brand_id = render_brand_selector("aeo")
    
    # Sub-Navigation (Tabs)
    aeo_mode = st.radio("Analysis Mode", ["🌍 Market Discovery (Non-Branded)", "🛡️ Brand Defense (Branded)"], horizontal=True, label_visibility="collapsed")
    
    # Common Inputs (Brand Name)
    col1, col2 = st.columns(2)
    with col1:
        if current_brand_id and "brand_data" in st.session_state:
            brand_name_val = st.session_state.brand_data.get("brand_name", "")
            brand_name = st.text_input("Brand Name", value=brand_name_val)
        else:
            brand_name = st.text_input("Brand Name", placeholder="e.g., Nike")
            
    # Input Logic Based on Tab
    if "Discovery" in aeo_mode:
        with col2:
            keywords_input = st.text_input("Target Keywords (comma separated)", placeholder="running shoes, athletic wear")
    elif "Defense" in aeo_mode:
        with col2:
             defense_keywords_input = st.text_input("Core Keywords (for context)", placeholder="SMS API, Verification", key="def_kw")
             keywords_input = defense_keywords_input # Logic re-use shim
             
        competitors_input = st.text_input("Specific Competitors to Watch (Optional)", placeholder="Twilio, Plivo", help="We will specifically look for these names in your branded search results.")

    # Advanced Settings
    
    # --- 1. Technical Prerequisite Check (Global Bot Access) - SHOW ALWAYS ---
    st.markdown("##### 🩺 Step 0: Global AI Bot Access")
    with st.expander("🛡️ Domain Gatekeeper Check (robots.txt)", expanded=False):
        st.info("ℹ️ **Global Impact:** This checks your `robots.txt` file, which controls AI access for **ALL** your webpages. If you block GPTBot here, your entire site is invisible to ChatGPT.")
        
        # Get URL from brand data or Allow manual override
        audit_url = ""
        if "brand_data" in st.session_state:
             audit_url = st.session_state.brand_data.get("url", "")
        
        audit_url_input = st.text_input("Root Domain to Check", value=audit_url, placeholder="https://example.com")
        
        if st.button("⚡ Check Bot Access"):
            if not audit_url_input:
                st.warning("Please enter a URL.")
            else:
                with st.spinner("Scanning robots.txt for AI blockers..."):
                    from utils.crawler_lite import audit_site_for_ai
                    
                    # We only care about functionality that impacts the WHOLE brand (Robots.txt)
                    # Page-level metrics (Schema, Readability) are removed as confirmed they are noise for brand-level AEO.
                    
                    audit_res = audit_site_for_ai(audit_url_input)
                    
                    # Display Results (Single Focus)
                    blocked_cnt = sum(1 for v in audit_res["robots_status"].values() if v == "Blocked")
                    
                    if blocked_cnt == 0:
                        st.success("✅ **All Systems Go:** Your domain allows all major AI crawlers (GPTBot, Claude, Google, Perplexity).")
                    else:
                        st.error(f"🛑 **Blocking Detected:** You are blocking {blocked_cnt} major AI bots. This creates a HARD CEILING on your visibility.")
                    
                    # Detailed Table
                    st.markdown("**Bot Access Status:**")
                    st.json(audit_res["robots_status"])
                    
                    st.caption("Note: This setting applies to every single page on your domain.")

    # --- 2. Configuration (Collapsible) ---
    with st.expander("⚙️ Simulation Configuration", expanded=False):
        st.info("Customize who is searching and where they are located to get the most accurate AI prediction.")
        
        # Row 1: Geography & Audience
        c_geo, c_aud = st.columns(2)
        
        with c_geo:
             # Region Selector
            target_region = st.selectbox("Geographic Market", [
                "Global / International",
                "North America: United States (US)",
                "North America: Canada (CA)",
                "EMEA: United Kingdom (UK)",
                "EMEA: Europe (Eurozone General)",
                "EMEA: Germany (DE)",
                "EMEA: France (FR)",
                "APAC: India (IN)",
                "APAC: Australia (AU)",
                "APAC: Singapore / SE Asia",
                "LATAM: Brazil (BR)"
            ], help="Simulates the search user's location. AEO answers often change based on region (e.g. pricing in GBP vs USD, local competitors).")
            
        with c_aud:
            target_context = st.selectbox("Target Audience / Context", [
                "General Audience", 
                "Enterprise / Large B2B", 
                "Mid-Market Business", 
                "Small Business / Startups", 
                "Technical / Developer", 
                "Consumer / B2C", 
                "Budget Conscious", 
                "Luxury / Premium"
            ])

        # Row 2: Intents
        selected_intents = st.multiselect("Search Intents", ["General", "Informational", "Commercial", "Transactional"], default=["General", "Informational"])
        
        # Inline Guide
        st.caption("ℹ️ **Intent Guide:** **General** (Broad awareness) | **Informational** (Definition/How-to) | **Commercial** (Comparisons/Rankings) | **Transactional** (Buying/Sign-up)")
        
        st.markdown("---")
        
        # Row 3: Advanced
        run_stability = st.checkbox("🔬 Deep Analysis (Multi-Sample)", value=False, help="Runs the query 3 times to ensure statistically significant results. Slightly slower but highly recommended for accuracy.")
        run_reputation = False
        if "Discovery" in aeo_mode:
            run_reputation = st.checkbox("🛡️ Run Brand Reputation/Safety Audit", value=True, help="Checks for negative sentiment by running queries like 'Worst X', 'Scam', 'Security Issues'. Warning: Can use more credits.")
        runs_count = 3 if run_stability else 1

    # --- 3. Run Analysis (Dual Mode) ---
    
    # Mode A: Market Discovery (Existing)
    if "Discovery" in aeo_mode:
        if st.button("🚀 Analyze Market Visibility", type="primary"):
            if not brand_name or not keywords_input:
                st.warning("Please enter both Brand Name and Keywords.")
            else:
                keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]
                
                with st.spinner(f"Simulating AI searches for {len(keywords)} keywords across {len(selected_intents)} intents in {target_region}..."):
                    from utils.aeo_engine import check_visibility, analyze_competitors
                    
                    # Save intents to session state for dynamic columns
                    st.session_state.last_run_intents = selected_intents
                    
                    # HARDCODED: Use the best Gemini model for AEO simulation by default (Flash 2.0 is fast & smart)
                    results = check_visibility(brand_name, keywords, api_keys, gemini_model="gemini-3-flash-preview", intents=selected_intents, context=target_context, region=target_region, runs=runs_count, include_risk_analysis=run_reputation)
                    st.session_state.aeo_results = results
                    
                    # --- HISTORICAL CONTEXT LOGIC ---
                    brand_id_u = None
                    if "brand_data" in st.session_state and st.session_state.brand_data:
                        brand_id_u = st.session_state.brand_data.get("db_id")
                    
                    history = get_aeo_history(brand_id=brand_id_u, brand_name=brand_name, limit=2)
                    
                    prev_lb = None
                    if history:
                        last_run = history[-1]
                        try:
                            prev_res = json.loads(last_run['analysis_json'])
                            prev_stats = analyze_competitors(prev_res, user_brand_name=brand_name)
                            prev_lb = prev_stats.get("leaderboard", [])
                        except:
                            pass

                    # Run Competitor Analysis
                    comp_stats = analyze_competitors(results, user_brand_name=brand_name, previous_leaderboard=prev_lb)
                    st.session_state.aeo_comp_stats = comp_stats
                    
                    # Intent Gap Analysis
                    intent_stats = {}
                    for intent in selected_intents:
                        intent_stats[intent] = {"mentions": 0, "total": 0, "sov": 0}
                        
                    for model, res in results.items():
                        if res.get("status") == "active":
                            for item in res.get("data", []):
                                if item["status"] == "success":
                                    it = item.get("intent", "General")
                                    if it in intent_stats:
                                        intent_stats[it]["total"] += 1
                                        if item["analysis"]["mentioned"]:
                                            intent_stats[it]["mentions"] += 1
                                            
                    for it, stats in intent_stats.items():
                        if stats["total"] > 0:
                            stats["sov"] = round((stats["mentions"] / stats["total"]) * 100, 1)
                            
                    st.session_state.aeo_intent_stats = intent_stats
                    
                    # Metadata & DB Save
                    query_string = ", ".join(keywords)
                    st.session_state.aeo_meta = {"brand": brand_name, "keywords": keywords, "intents": selected_intents, "risk_audit_enabled": run_reputation, "query_string": query_string}
                    
                    try:
                        import json
                        brand_id = None
                        if "brand_data" in st.session_state and st.session_state.brand_data:
                            brand_id = st.session_state.brand_data.get("db_id")
                        
                        save_aeo_analysis(
                            brand_id=brand_id,
                            query=query_string,
                            brand_url=brand_name,
                            analysis_json=json.dumps(results)
                        )
                        st.toast("Analysis saved!", icon="💾")
                    except Exception as e:
                        st.error(f"DB Save Error: {e}")

    # Mode B: Brand Defense (New)
    elif "Defense" in aeo_mode:
         if st.button("🛡️ Run Defense Audit", type="primary"):
             if not brand_name or not keywords_input:
                 st.warning("Please enter Brand Name and Core Keywords.")
             else:
                 keywords = [k.strip() for k in keywords_input.split(",")]
                 competitors = [c.strip() for c in competitors_input.split(",")] if competitors_input else []
                 
                 with st.spinner(f"Running defensive simulation on {len(keywords)} keyword clusters..."):
                     from utils.aeo_engine import run_branded_simulation
                     
                     # Pass Context (Region + Persona) for realistic simulation
                     def_results = run_branded_simulation(
                        brand_name, 
                        keywords, 
                        competitors, 
                        api_key=api_keys.get('gemini'), 
                        model_name="gemini-3-flash-preview",
                        region=target_region,      # From Sidebar
                        context=target_context     # From Sidebar
                     )
                     st.session_state.defense_results = def_results

    # Display Results (Discovery Mode)
    if "Discovery" in aeo_mode and "aeo_results" in st.session_state:
        results = st.session_state.aeo_results
        meta = st.session_state.aeo_meta
        comp_stats = st.session_state.get("aeo_comp_stats", {})
        
        st.markdown("---")
        st.subheader(f"Results for: {meta['brand']}")
        
        # --- NEW: Historical Trends ---
        # Fetch history fresh
        brand_id_hist = None
        if "brand_data" in st.session_state and st.session_state.brand_data:
            brand_id_hist = st.session_state.brand_data.get("db_id")
            
        # Use sanitized query string if available, else first keyword as fallback
        current_q = meta.get('query_string', meta.get('keywords', [''])[0])
        hist_data = get_aeo_history(brand_id=brand_id_hist, brand_name=meta['brand'], current_query=current_q, limit=20)
        
        if len(hist_data) >= 1:
            with st.expander("📈 Historical Trends", expanded=True):
                if len(hist_data) == 1:
                    st.info("ℹ️ First run recorded. Run again to see trends over time.")
                else:
                    st.caption("Tracking your visibility and rank over time.")
                
                chart_data = pd.DataFrame(hist_data)
                chart_data['date'] = pd.to_datetime(chart_data['date'])
                
                hc1, hc2, hc3 = st.columns(3)
                with hc1:
                    st.markdown("**Visibility Score (%)**")
                    st.line_chart(chart_data.set_index('date')['visibility_score'], color="#2563eb")
                with hc2:
                    st.markdown("**Rank Position (Lower is Better)**")
                    # Invert Rank for visualization? Or just raw. Raw is fine but 1 is top.
                    st.line_chart(chart_data.set_index('date')['rank_position'], color="#059669")
                with hc3:
                     st.markdown("**Risk Score (Lower is Better)**")
                     st.line_chart(chart_data.set_index('date')['risk_score'], color="#dc2626")
        
        # --- NEW: Volatility Warning ---
        stab_score = comp_stats.get("stability_score", 100)
        if stab_score < 70:
            st.warning(f"⚠️ **High Volatility Detected (Stability: {stab_score}%)**: Your brand appears inconsistently across identical queries. This indicates the AI is 'confused' or your authority is borderline.")
        else:
            st.success(f"✅ **Stable Ranking (Stability: {stab_score}%)**: Your visibility is consistent.")
        

        
        # [Removed Redundant SoV Explanation Card]
        
        # --- Metric Guide (Replaced SoV Card) ---
        with st.expander("ℹ️ Metric Guide: How to Read the Scores"):
             c_guide1, c_guide2 = st.columns(2)
             with c_guide1:
                 st.markdown("""
                 **The Funnel Stages:**
                 - **Awareness (Info):** % of "What is" queries where you appear. *Goal: Be the Definition.*
                 - **Consideration (Comm):** % of "Best of" queries where you appear. *Goal: Be a Top Contender.*
                 - **Conversion (Trans):** % of "Where to buy" queries where you appear. *Goal: Drive Action.*
                 """)
             with c_guide2:
                 st.markdown("""
                 **Scoring Logic:**
                 - **100%:** You own this intent completely.
                 - **Dominance:** Your weighted average across ALL stages (Rank #1 is worth more than Rank #10).
                 - **Risk Visibility:** (If visible) % of NEGATIVE queries where you appeared. **0% is ideal.**
                 """)
        
        # Aggregated Stats
        total_queries = 0
        total_mentions = 0
        model_scores = {}
        
        for model, data in results.items():
            if data["status"] == "active":
                model_mentions = 0
                model_queries = 0
                # Track unique queries per model
                seen_queries = set()
                
                for item in data["data"]:
                    if item["status"] == "success":
                        q_id = f"{item['keyword']}_{item['intent']}_{item.get('run_index', 1)}"
                        model_queries += 1
                        if item["analysis"]["mentioned"]:
                            model_mentions += 1
                            total_mentions += 1
                        total_queries += 1
                
                score = (model_mentions / model_queries * 100) if model_queries > 0 else 0
                model_scores[model] = score
        
        overall_visibility = (total_mentions / total_queries * 100) if total_queries > 0 else 0
        
        # Score Cards
        c1, c2, c3 = st.columns(3)
        c1.metric("Overall Visibility", f"{overall_visibility:.1f}%")
        c2.metric("Models Analyzed", len(model_scores))
        c3.metric("Keywords Tracked", len(meta["keywords"]))
        
        # --- NEW: Intent Breakdown ---
        if "aeo_intent_stats" in st.session_state:
            st.markdown("### 🎯 Intent Gap Analysis")
            st.caption("How your visibility changes across different user intents.")
            
            intent_stats = st.session_state.aeo_intent_stats
            
            # Prepare data for chart
            if intent_stats:
                safe_intent_data = [{"Intent": k, "Visibility": float(v["sov"])} for k, v in intent_stats.items() if v.get("sov") is not None]
                if not safe_intent_data:
                     safe_intent_data = [{"Intent": "No Data", "Visibility": 0.0}]
                intent_data = pd.DataFrame(safe_intent_data)
            else:
                intent_data = pd.DataFrame([{"Intent": "No Data", "Visibility": 0.0}])
            
            c_i1, c_i2 = st.columns([2, 1])
            with c_i1:
                st.bar_chart(intent_data.set_index("Intent"))
            
            with c_i2:
                # Strategic Advice based on Gaps
                st.markdown("**Strategic Insights:**")
                for k, v in intent_stats.items():
                    if v["sov"] < 30:
                        st.warning(f"**Low {k} Visibility:** Your brand is missing from '{k}' searches. Focus on content targeting this stage.")
                    elif v["sov"] > 70:
                        st.success(f"**Strong {k} Presence:** You dominate '{k}' searches!")
                    else:
                        st.info(f"**Moderate {k} Presence:** You are visible in primarily '{k}' searches, but there is room to improve your rank.")
            
            st.markdown("---")
        st.markdown("#### 📊 Visibility by Model")
        
        if model_scores:
            df_models = pd.DataFrame(list(model_scores.items()), columns=["Model", "Visibility"])
            st.bar_chart(df_models.set_index("Model"))
        else:
            st.info("No model data available.")
        
        # [Removed Redundant Brand Reputation & Risk Audit Section]
        # This data is now consolidated into the "AI Perception Audit" and "AEO Market Share Leaderboard" below.
        
        # --- NEW: Citation Battlefield ---
        st.markdown("---")
        st.subheader("⚔️ The Citation Battlefield")
        st.markdown("Where the winners are being cited vs. where you are missing.")
        
        cg1, cg2 = st.columns(2)
        
        with cg1:
             st.markdown("##### 🚀 Opportunity URLs (Missing Links)")
             st.caption("High-authority sources citing your competitors but NOT you.")
             
             # Support new key 'opportunity_urls' with fallback to 'source_gaps'
             opp_urls = comp_stats.get("opportunity_urls", comp_stats.get("source_gaps", []))
             
             if opp_urls:
                 for gap in opp_urls:
                     st.markdown(f"""
                     <div style="padding:10px; border-bottom:1px solid #eee;">
                        <span style="color:#e11d48; font-weight:bold;">{gap['domain']}</span> 
                        <span style="color:#666; font-size:0.9rem;">(Cited {gap['leader_count']} times for Leaders)</span>
                     </div>
                     """, unsafe_allow_html=True)
             else:
                 st.success("🎉 No major source gaps found! You are well-cited.")
                 
        with cg2:
             st.markdown("##### 💪 Strength URLs (Your Citations)")
             st.caption("Where you are currently winning citations.")
             
             # Support new key 'strength_urls' with fallback to 'citations'
             str_urls = comp_stats.get("strength_urls", comp_stats.get("citations", []))
             
             if str_urls:
                 # Convert to simple list/df
                 # str_urls structure might be [{'domain': 'x', 'count': 1}]
                 cit_df = pd.DataFrame(str_urls)
                 if not cit_df.empty:
                     st.dataframe(
                         cit_df.rename(columns={"domain": "Source", "count": "Citations"}), 
                         use_container_width=True, 
                         hide_index=True
                     )
             else:
                 st.info("No citations found for your brand yet.")

        # --- NEW: Competitor Leaderboard ---
        if "aeo_comp_stats" in st.session_state:
            # comp_stats already loaded above
            
            st.markdown("---")
            st.subheader("🏆 AEO Market Share Leaderboard")
            st.markdown("Who is winning the AI answers for these keywords?")
            
            leaderboard = comp_stats.get("leaderboard", [])
            if leaderboard:
                # Explainer
                with st.expander("ℹ️ Understanding the Matrix"):
                    st.markdown("""
                    - **Awareness (Info)**: Visibility in "What is..." queries. High score = Authority.
                    - **Consideration (Comm)**: Visibility in "Best of" comparisons. High score = Top Contender.
                    - **Conversion (Trans)**: Visibility in "Where to buy" queries. High score = Conversion Driver.
                    - **General Score**: Visibility in broad/unspecified queries.
                    - **Risk Visibility**: Visibility in negative/risk queries (e.g., "Worst...", "Scams"). **LOWER IS BETTER.**
                    - **Dominance**: Your weighted market share across all funnel stages.
                    - **Top 3rd Party Source**: The most frequent external site citing this brand.
                    """)

                # Custom HTML Table for Leaderboard
                # DYNAMIC COLUMN LOGIC
                # Only show columns if they are in 'selected_intents' OR default to showing all if specific scoping fails
                
                # Check what the user actually ran
                user_intents = st.session_state.get("last_run_intents", selected_intents) # Use session state if available, else current selection

                show_info = "Informational" in user_intents
                show_comm = "Commercial" in user_intents
                show_trans = "Transactional" in user_intents
                show_gen = "General" in user_intents
                
                # Risk Column Logic: Show if user REQUESTED risk audit OR if any risk data exists in leaderboard
                has_any_risk_data = any(r.get('risk_score', 0) > 0 for r in leaderboard)
                run_risk_requested = st.session_state.get("aeo_meta", {}).get("risk_audit_enabled", False)
                
                show_risk = run_risk_requested or has_any_risk_data

                lb_rows = ""
                for idx, row in enumerate(leaderboard):
                    color = "#e6fffa" if row['name'].lower() == brand_name.lower() else "white"
                    
                    # Rank Change Indicator
                    change = row.get("rank_change", 0)
                    change_html = ""
                    if change == "New":
                        change_html = '<span style="color:#2563eb; font-size:0.8rem; font-weight:bold;">(NEW)</span>'
                    elif isinstance(change, int) and change != 0:
                        if change > 0: # Improved (e.g. Rank 5 -> Rank 2 = +3)
                            change_html = f'<span style="color:#16a34a; font-size:0.8rem; font-weight:bold;">▲ {change}</span>'
                        else: # Declined (e.g. Rank 1 -> Rank 4 = -3)
                             change_html = f'<span style="color:#dc2626; font-size:0.8rem; font-weight:bold;">▼ {abs(change)}</span>'
                    
                    # Formatting scores
                    edu = f"{row.get('info_score', 0)}%"
                    comm = f"{row.get('comm_score', 0)}%"
                    trans = f"{row.get('trans_score', 0)}%"
                    gen = f"{row.get('general_score', 0)}%"
                    risk = f"{row.get('risk_score', 0)}%"
                    
                    # Visual cues
                    edu_style = "font-weight:bold; color:#059669;" if row.get('info_score', 0) > 50 else ""
                    comm_style = "font-weight:bold; color:#059669;" if row.get('comm_score', 0) > 50 else ""
                    trans_style = "font-weight:bold; color:#059669;" if row.get('trans_score', 0) > 50 else ""
                    gen_style = "font-weight:bold; color:#059669;" if row.get('general_score', 0) > 50 else ""
                    
                    # Risk Style: Negative is BAD (Red), Low/Zero is GOOD (Green)
                    risk_val = row.get('risk_score', 0)
                    if risk_val > 0:
                         risk_style = "font-weight:bold; color:#dc2626; background-color:#fef2f2;" 
                    else:
                         risk_style = "color:#059669;" # Zero risk is good

                    # Build Row Dynamically
                    row_html = f"""<tr style="border-bottom: 1px solid #eee; background-color: {color};">
<td style="padding:10px;">#{idx+1} {change_html}</td>
<td style="padding:10px; font-weight:bold;">{row['name']}</td>"""

                    if show_info:
                        row_html += f'<td style="padding:10px; text-align:center; {edu_style}">{edu}</td>'
                    if show_comm:
                        row_html += f'<td style="padding:10px; text-align:center; {comm_style}">{comm}</td>'
                    if show_trans:
                        row_html += f'<td style="padding:10px; text-align:center; {trans_style}">{trans}</td>'
                    if show_gen:
                        row_html += f'<td style="padding:10px; text-align:center; {gen_style}">{gen}</td>'
                    if show_risk:
                        row_html += f'<td style="padding:10px; text-align:center; {risk_style}">{risk}</td>'

                    row_html += f"""<td style="padding:10px; text-align:center; font-weight:bold;">{row['share_of_voice']}%</td>
<td style="padding:10px; font-size:0.85rem; color:#666;">{row.get('dominant_source', 'N/A')}</td>
</tr>"""
                    lb_rows += row_html

                # Build Header Dynamically
                header_html = """<tr style="border-bottom: 2px solid #ddd; background-color: #f8f9fa;">
<th style="padding:10px; text-align:left;">Rank</th>
<th style="padding:10px; text-align:left;">Brand</th>"""
                
                if show_info:
                    header_html += '<th style="padding:10px; text-align:center;" title="Informational Visibility (Awareness)">Awareness</th>'
                if show_comm:
                    header_html += '<th style="padding:10px; text-align:center;" title="Commercial Visibility (Consideration)">Consideration</th>'
                if show_trans:
                    header_html += '<th style="padding:10px; text-align:center;" title="Transactional Visibility (Conversion)">Conversion</th>'
                if show_gen:
                    header_html += '<th style="padding:10px; text-align:center;" title="General Visibility">General</th>'
                if show_risk:
                    header_html += '<th style="padding:10px; text-align:center; color:#dc2626;" title="Risk Visibility: Percentage of NEGATIVE queries (e.g. \'Worst..\') you appeared in. Lower is better.">Risk ⚠️</th>'

                header_html += """<th style="padding:10px; text-align:center;" title="Weighted Market Share: Agreggate score of your visibility x rank value across all selected intents.">Dominance</th>
<th style="padding:10px; text-align:left;">Top Source</th>
</tr>"""

                lb_html = f"""<table style="width:100%; border-collapse: collapse;">
<thead>
{header_html}
</thead>
<tbody>
{lb_rows}
</tbody>
</table>"""
                st.markdown(lb_html, unsafe_allow_html=True)
            else:
                st.info("No competitor data found.")

        st.markdown("---")
        
        # --- NEW: AI Brand Index ---
        st.markdown("---")
        st.subheader("5. AI Brand Index (Page-Level Verification)")
        st.markdown("Score how well your specific webpage URLs are cited and represented in AI answers.")
        
        # 1. Select Pages
        available_urls = []
        if "brand_data" in st.session_state and st.session_state.brand_data:
            available_urls = st.session_state.brand_data.get("all_urls", [])

        # Default to top 5 if available
        default_selection = available_urls[:5]
        
        selected_index_pages = st.multiselect("Select Pages to Grade", available_urls, default=default_selection, help="Select the specific pages you want to check for AI visibility.")
        
        if st.button("📊 Run Brand Index Analysis", type="primary"):
            if not selected_index_pages:
                st.warning("Please select at least one page.")
            else:
                 with st.spinner(f"Grading {len(selected_index_pages)} pages against AI models (Gemini 3 Flash)..."):
                     from utils.aeo_engine import evaluate_page_index
                     
                     index_results = []
                     total_score = 0
                     
                     # Progress bar
                     p_bar = st.progress(0)
                     
                     for i, url in enumerate(selected_index_pages):
                         # Guess page type from URL
                         p_type = "General"
                         u_lower = url.lower()
                         if "pricing" in u_lower: p_type = "Pricing"
                         elif "about" in u_lower: p_type = "About"
                         elif "blog" in u_lower: p_type = "Blog"
                         elif "contact" in u_lower: p_type = "Contact"
                         elif len(url) < 30: p_type = "Homepage" # Heuristic
                         
                         # Run Logic
                         # Use meta['brand'] from previous scope or fallback
                         b_name = meta['brand'] if 'meta' in locals() else brand_name
                         
                         res = evaluate_page_index(b_name, url, p_type, api_key=api_keys.get('gemini'), model_name="gemini-3-flash-preview")
                         index_results.append(res)
                         total_score += res.get("scores", {}).get("total", 0)
                         
                         p_bar.progress((i + 1) / len(selected_index_pages))
                         
                     # Calc Average
                     avg_index = total_score / len(selected_index_pages) if selected_index_pages else 0
                     
                     st.session_state.brand_index_results = index_results
                     st.session_state.brand_index_score = avg_index
                     
        # Display Results
        if "brand_index_results" in st.session_state:
            idx_score = st.session_state.brand_index_score
            
            # Big Metric
            c_idx1, c_idx2 = st.columns([1, 3])
            with c_idx1:
                 st.metric("AI Brand Index", f"{idx_score:.1f}/100")
            with c_idx2:
                if idx_score > 80:
                    st.success("🌟 **Excellent:** Your key pages are authoritative sources for AI.")
                elif idx_score > 50:
                    st.info("⚠️ **Moderate:** AI knows you, but often ignores your specific deep-link pages.")
                else:
                    st.error("🛑 **Low:** AI struggles to connect your brand name to your specific landing pages.")

            # Detailed Table
            st.markdown("##### 📄 Page Breakdown")
            
            # Create UI Table
            for res in st.session_state.brand_index_results:
                s = res.get("scores", {})
                
                # Status Icon
                icon = "🔴"
                if s['total'] > 80: icon = "🟢"
                elif s['total'] > 50: icon = "🟡"
                
                with st.expander(f"{icon} {res['page_type']}: {res['url']} (Score: {s['total']})"):
                    c_s1, c_s2, c_s3 = st.columns(3)
                    c_s1.metric("Citation", f"{s['citation']}/40", help="Did the AI link to this page?")
                    c_s2.metric("Relevance", f"{s['relevance']}/40", help="Did the answer match page content?")
                    c_s3.metric("Sentiment", f"{s['sentiment']}/20", help="Was it positive?")
                    
                    st.caption(f"**Query Used:** {res['query_used']}")
                    st.info(f"**AI Response Snippet:** {res['response_snippet']}")
                    
                    # New: Prompt Visibility
                    with st.expander("📝 View AI Input Prompt"):
                        st.markdown("**Exact Prompt Sent to LLM:**")
                        # Default prompt construction logic from evaluate_page_index if not returned (backward compatibility)
                        # But we updated backend to return 'prompt_used' if possible.
                        # Since we didn't change evaluate_page_index signature in plan, we might need to assume it or fetching it.
                        # Wait, I DO need to update evaluate_page_index to return prompt. I did that in previous step.
                        st.code(res.get('prompt_used', 'Prompt data not available for this run.'), language="markdown")

                    if s['citation'] == 0:
                        st.warning("👉 **Action:** Add Schema markup and internal links to this page to help AI find it.")
                        
                        # Show who WAS cited
                        found_cits = res.get("found_citations", [])
                        if found_cits:
                            st.markdown("##### 🕵️ Who did the AI cite instead?")
                            st.caption("These sources are stealing your traffic for this specific query.")
                            
                            unique_cits = list(set(found_cits))[:5] # Top 5 unique
                            
                            for c in unique_cits:
                                # Clean up for display
                                disp_c = c.replace("https://", "").replace("http://", "").rstrip("/")
                                st.markdown(f"- 🔗 [{disp_c}]({c})")
                        else:
                            st.markdown("##### 🤷 No citations found")
                            st.caption("The AI answered without citing specific sources (Knowledge Transfer).")
        


        st.markdown("---")
        
        # --- NEW: AI Perception Audit ---
        st.markdown("---")
        st.subheader("🧠 AI Perception Audit")
        st.markdown("Deep dive into *how* the AI sees your brand. This audit breaks down the specific context and associations.")
        
        # Tabs for Intents (Better organization than Models)
        # Group data by Intent first, then Model
        
        # Get all unique intents found
        found_intents = set()
        for m in results.values():
            if m["status"] == "active":
                for item in m["data"]:
                    found_intents.add(item.get("intent", "General"))
        
        if not found_intents:
            st.info("No data to audit.")
        else:
            # Custom Sort Order: Standard Intents First, then Risk
            standard_order = ["General", "Informational", "Commercial", "Transactional"]
            
            # 1. Identify Standard Intents present
            found_standard = [i for i in standard_order if i in found_intents]
            
            # 2. Identify Risk Intents (and any others)
            found_risk = sorted([i for i in found_intents if i not in standard_order])
            
            # 3. Combine
            sorted_intents = found_standard + found_risk
            
            intent_tabs = st.tabs(sorted_intents)
            
            for idx, intent_name in enumerate(sorted_intents):
                with intent_tabs[idx]:
                    st.markdown(f"**Audit text for: '{intent_name}' searches**", help="Review how different AI models responded to this specific intent.")
                    
                    for model_name, res_data in results.items():
                        if res_data["status"] != "active":
                            continue
                            
                        # Filter for this intent
                        intent_items = [x for x in res_data["data"] if x.get("intent", "General") == intent_name]
                        
                        if not intent_items:
                            continue
                            
                        st.markdown(f"##### 🤖 {model_name}")
                        
                        for item in intent_items:
                            # Skip failed runs
                            if item.get("status") != "success":
                                st.warning(f"Run failed for keyword: {item.get('keyword')}")
                                continue

                            with st.container():
                                # Card Style
                                st.markdown(f"""
                                <div style="border:1px solid #ddd; border-radius:8px; padding:15px; margin-bottom:15px; background-color:#f8f9fa;">
                                    <div style="font-weight:bold; font-size:1.1rem; margin-bottom:5px;">{item['keyword']}</div>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                c_score, c_context = st.columns([1, 3])
                                
                                analysis = item["analysis"]
                                
                                with c_score:
                                    # Scorecard
                                    rank_display = f"#{analysis['rank']}" if str(analysis['rank']).isdigit() else analysis['rank']
                                    
                                    # Default Ranking Logic
                                    rank_color = "black"
                                    
                                    # Check if this is a RISK intent (where being #1 is BAD, UNLESS sentiment is Safe)
                                    is_risk_intent = intent_name.startswith("Risk:")
                                    
                                    # [FIX] Visual Logic: Check sentiment
                                    sentiment_lower = analysis.get('sentiment', 'N/A').lower()
                                    is_safe = "safe" in sentiment_lower or "positive" in sentiment_lower or "neutral" in sentiment_lower
                                    
                                    if str(analysis['rank']).isdigit():
                                        rank_val = int(analysis['rank'])
                                        if is_risk_intent:
                                            if is_safe:
                                                 # It's a "Risk" query, but we are explicitly SAFE. This is GOOD.
                                                 # e.g. "Safe alternatives: Twilio"
                                                 rank_color = "#059669" # Green
                                            else:
                                                # Risk Logic: #1 is BAD (Red) because it matches the negative intent
                                                if rank_val == 1:
                                                    rank_color = "#dc2626" # Red
                                                elif rank_val <= 3:
                                                    rank_color = "#ea580c" # Orange/Red
                                                else:
                                                    rank_color = "#b91c1c" # Dark Red
                                        else:
                                            # Normal Logic: #1 is GOOD (Green)
                                            if rank_val == 1:
                                                rank_color = "#16a34a" # Green (consistent)
                                            elif rank_val <= 3:
                                                rank_color = "#eab308" # Yellow
                                    
                                    st.markdown(f"""
                                    <div style="text-align:center; padding:10px; background:white; border-radius:8px; box-shadow:0 1px 3px rgba(0,0,0,0.1);">
                                        <div style="font-size:0.8rem; color:#666; text-transform:uppercase; letter-spacing:1px;">Rank</div>
                                        <div style="font-size:2rem; font-weight:800; color:{rank_color};">{rank_display}</div>
                                        <div style="margin-top:5px; padding-top:5px; border-top:1px solid #eee; font-size:0.9rem;">
                                            {analysis['sentiment']}
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    
                                    # Show Adjectives (Brand Vibe)
                                    if "extracted_adjectives" in analysis and analysis["extracted_adjectives"]:
                                        st.caption("Brand Associations:")
                                        adj_html = ""
                                        for adj in analysis["extracted_adjectives"]:
                                            adj_html += f'<span style="background-color:#f1f5f9; color:#475569; padding:2px 6px; border-radius:4px; font-size:0.75rem; margin-right:3px; display:inline-block;">{adj}</span>'
                                        st.markdown(adj_html, unsafe_allow_html=True)
                                    
                                with c_context:
                                    # Prompt Visibility
                                    with st.expander("📝 View AI Prompt Used"):
                                        st.markdown(f"**Keyword:** `{item['keyword']}`")
                                        st.markdown("**Prompt Sent:**")
                                        st.code(item.get('prompt_used', 'N/A'), language="text")

                                    # snippet
                                    st.markdown("**AI Response Context:**")
                                    # Use info box but with markdown enabled for the bolding
                                    st.info(analysis["snippet"], icon="💬")
                                    
                                    # Who else mentioned?
                                    others = [c['name'] for c in analysis.get('competitors_found', []) if c['name'].lower() != brand_name.lower()]
                                    if others:
                                        st.caption(f"**Also mentioned in this answer:** {', '.join(others[:5])}")
                            
                            st.markdown("---")

        # --- NEW: Strategic Playbook (Moved to End) ---
        st.subheader("📚 AEO Strategic Playbook")
        st.markdown("Actionable steps to improve your AI Visibility.")
        
        if st.button("⚡ Generate AI Optimization Strategy", type="primary"):
            with st.spinner("Analyzing opportunity gaps and crafting strategy..."):
                opps = comp_stats.get("opportunity_urls", [])[:5]
                lb = comp_stats.get("leaderboard", [])[:5]
                
                strategy_json = generate_aeo_strategy(lb, opps, meta['brand'], focus_intents=meta.get('intents'))
                st.session_state.aeo_strategy = parse_json_response(strategy_json)
        
        if "aeo_strategy" in st.session_state and st.session_state.aeo_strategy:
            strat = st.session_state.aeo_strategy
            
            # Headline
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); padding:20px; border-radius:10px; color:white; margin-bottom:20px; text-align:center;">
                <h2 style="margin:0; color:white;">🏹 Strategy: {strat.get('headline_strategy', 'Optimization Plan')}</h2>
                <p style="font-size:1.1rem; margin-top:10px; opacity:0.9;">{strat.get('executive_summary', '')}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # 3 Columns for Actions
            ac1, ac2, ac3 = st.columns(3)
            actions = strat.get("top_3_actions", [])
            
            cols = [ac1, ac2, ac3]
            for i, action in enumerate(actions):
                if i < 3:
                     with cols[i]:
                        st.markdown(f"""
                        <div style="border:1px solid #e5e7eb; border-radius:8px; padding:15px; height:100%; background:#f9fafb;">
                            <div style="font-weight:bold; color:#1f2937; margin-bottom:5px;">{i+1}. {action.get('title')}</div>
                            <div style="font-size:0.9rem; color:#4b5563; margin-bottom:10px;">{action.get('description')}</div>
                            <span style="background:#dbeafe; color:#1e40af; padding:2px 6px; border-radius:4px; font-size:0.75rem;">Impact: {action.get('impact')}</span>
                        </div>
                        """, unsafe_allow_html=True)
            
            # Content Pivot
            st.info(f"💡 **Content Pivot:** {strat.get('content_pivot')}")
            
        # --- PDF Export Button ---
        st.markdown("---")
        if st.button("📥 Download Full AEO Report (PDF)", type="primary"):
            with st.spinner("Generating PDF Report..."):
                brand_n = meta['brand']
                # Gather data
                pdf_bytes = pdf_gen.generate_aeo_report(
                    brand_n,
                    results,
                    comp_stats,
                    st.session_state.get("aeo_intent_stats", {}),
                    strategy=st.session_state.get("aeo_strategy"),
                    brand_index=st.session_state.get("brand_index_results"),
                    defense_results=st.session_state.get("defense_results"), # Pass Defense Data
                    defense_strategy=st.session_state.get("defense_strategy") # Pass Defense Strat
                )
                
                st.download_button(
                    label="📄 Click to Save PDF",
                    data=pdf_bytes,
                    file_name=f"{brand_n}_AEO_Report.pdf",
                    mime="application/pdf"
                )
        
        st.markdown("---")

    # --- TAB 2: BRAND DEFENSE RESULTS (New Display) ---
    if "Defense" in aeo_mode and "defense_results" in st.session_state:
        d_res = st.session_state.defense_results
        
        st.markdown("---")
        st.subheader("🛡️ Brand Defense Report")
        st.caption(f"Analysis of Branded Searches for: {brand_name}")
        
        # Top Metrics
        dm1, dm2, dm3 = st.columns(3)
        
        moat_score = d_res.get("moat_score", 0)
        moat_delta = "Safe" if moat_score > 90 else "Leakage Detected"
        moat_color = "normal" if moat_score > 90 else "inverse"
        
        dm1.metric("Defensive Moat", f"{moat_score}%", delta=moat_delta, delta_color=moat_color, help="% of direct brand searches where NO competitors were suggested.")
        
        # Leakage Metric
        leak_count = sum(d_res.get("leakage_counts", {}).values())
        dm2.metric("Competitor Leaks", leak_count, delta="-Lower is better", delta_color="inverse")
        
        # Narrative Alignment (Simple Check)
        pos_sentiment = len([r for r in d_res.get("results", []) if r['sentiment'] == "Positive"])
        total_res = len(d_res.get("results", []))
        sentiment_score = int((pos_sentiment / total_res * 100)) if total_res > 0 else 0
        dm3.metric("Positive Sentiment", f"{sentiment_score}%")
        
        # Leakage Table
        if d_res.get("leakage_counts"):
            st.warning(f"🚨 **Leakage Alert:** The following competitors are appearing in your branded searches!")
            st.bar_chart(pd.DataFrame(list(d_res["leakage_counts"].items()), columns=["Competitor", "Appearances"]).set_index("Competitor"))
        else:
            st.success("✅ **Moat Secure:** No competitors detected in your branded signals.")
            
        # Detailed Drill Down (Upgraded UI)
        st.markdown("##### 🕵️ Query Audit Trail")
        st.caption("Detailed breakdown of every simulated brand query.")
        
        for res in d_res.get("results", []):
            # 1. Card Container (Upgraded to match Perception Audit)
            
            # Color Coded Banner
            border_color = "#22c55e" # Green
            status_icon = "🛡️"
            status_text = "Moat Secure"
            
            if res['is_moat_breach']:
                border_color = "#ef4444" # Red
                status_icon = "🚨"
                status_text = "Leakage Detected"
            elif res['type'] == 'Comparative':
                border_color = "#3b82f6" # Blue
                status_icon = "⚖️"
                status_text = "Competitive Zone"
            
            with st.container():
                st.markdown(f"""
                <div style="border:1px solid #e5e7eb; border-radius:8px; padding:0px; margin-bottom:20px; background:white; overflow:hidden; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                    <div style="background:{border_color}; padding:5px 15px; color:white; font-size:0.8rem; font-weight:bold; letter-spacing:0.5px; text-transform:uppercase;">
                        {status_icon} {status_text} | {res['type']}
                    </div>
                    <div style="padding:15px;">
                        <div style="font-weight:700; font-size:1.1rem; color:#1f2937; margin-bottom:5px;">"{res['query']}"</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                c_det1, c_det2 = st.columns([2, 1])
                
                with c_det1:
                     st.markdown("**🤖 AI Response Analysis**")
                     
                     # Narrative Summary (NEW)
                     narrative = res.get('narrative_summary', 'No summary available.')
                     st.markdown(f"""
                     <div style="background:#eef2ff; border-left:4px solid #6366f1; padding:12px; border-radius:4px; margin-bottom:10px; color:#312e81; font-weight:500;">
                        <span style="font-size:1.2rem;">💡</span> {narrative}
                     </div>
                     """, unsafe_allow_html=True)
                     
                     # Rich Snippet Box
                     st.caption("Raw Snippet:")
                     st.markdown(f"""
                     <div style="background:#f8fafc; border-left:4px solid {border_color}; padding:15px; border-radius:0 4px 4px 0; font-style:italic; color:#475569; margin-bottom:10px; font-size:0.9rem;">
                        "...{res['response_snippet']}..."
                     </div>
                     """, unsafe_allow_html=True)
                     
                     # Trusted Prompt View
                     with st.expander("📝 View Persona & Prompt"):
                        st.caption("This query simulated the following persona to test brand resilience:")
                        st.code(res.get('prompt_used', 'N/A'), language="markdown")
                
                with c_det2:
                    st.markdown("**🔍 risk Audit**")
                    
                    # Sentiment Badge
                    if res['sentiment'] == 'Positive':
                        st.markdown('<span style="background:#dcfce7; color:#166534; padding:2px 8px; border-radius:10px; font-size:0.8rem; font-weight:bold;">Positive Sentiment</span>', unsafe_allow_html=True)
                    elif res['sentiment'] == 'Negative':
                        st.markdown('<span style="background:#fee2e2; color:#991b1b; padding:2px 8px; border-radius:10px; font-size:0.8rem; font-weight:bold;">Negative Sentiment</span>', unsafe_allow_html=True)
                    else:
                        st.markdown('<span style="background:#f1f5f9; color:#475569; padding:2px 8px; border-radius:10px; font-size:0.8rem; font-weight:bold;">Neutral</span>', unsafe_allow_html=True)
                        
                    st.markdown("---")
                    
                    if res.get('leaked_to'):
                         st.markdown(f"**⚠️ Leaked To:**")
                         for lk in res['leaked_to']:
                             st.markdown(f"- 🔴 **{lk}**")
                    else:
                        if res['type'] != 'Comparative':
                            st.markdown(f"**✅ No leaks detected.**")
                        else:
                            st.caption("Comparison lists competitors by definition.")
                            
                    # Descriptors
                    if res['descriptors']:
                        st.markdown("---")
                        st.caption("Key Attributes:")
                        html_d = ""
                        for d in res['descriptors']:
                             html_d += f'<span style="border:1px solid #e2e8f0; color:#64748b; padding:1px 5px; border-radius:4px; font-size:0.75rem; margin:2px; display:inline-block;">{d}</span>'
                        st.markdown(html_d, unsafe_allow_html=True)

            st.markdown("---")

        st.markdown("---")
        
        # --- STRATEGIC PLAYBOOK (BRAND DEFENSE) ---
        st.subheader("🛡️ Defense Playbook")
        st.caption("AI-generated tactics to patch your leaks and secure your narrative.")
        
        if st.button("⚡ Generate Defense Strategy", type="primary", key="gen_def_strat"):
            with st.spinner("Consulting Crisis Management AI..."):
                from utils.aeo_engine import generate_defense_strategy
                strat_json = generate_defense_strategy(brand_name, d_res, api_key=api_keys.get('gemini'), model_name="gemini-3-flash-preview")
                st.session_state.defense_strategy = parse_json_response(strat_json)
        
        if "defense_strategy" in st.session_state and st.session_state.defense_strategy:
             strat = st.session_state.defense_strategy
             
             # Defense Header
             st.info(f"**Strategy:** {strat.get('headline_strategy', 'Custom Defense Plan')}\n\n{strat.get('executive_summary', '')}")
             
             # Tactics Cards
             cols = st.columns(3)
             tactics = strat.get("tactics", [])
             
             for i, tac in enumerate(tactics):
                 if i < 3:
                     with cols[i]:
                         st.markdown(f"""
                         <div style="border:1px solid #bbf7d0; background:#f0fdf4; padding:15px; border-radius:8px; height:100%;">
                            <div style="font-weight:bold; color:#166534; margin-bottom:5px;">{i+1}. {tac.get('title')}</div>
                            <div style="font-size:0.9rem; color:#333; margin-bottom:10px;">{tac.get('description')}</div>
                            <span style="font-size:0.8rem; background:#166534; color:white; padding:2px 6px; border-radius:4px;">{tac.get('impact')} Impact</span>
                         </div>
                         """, unsafe_allow_html=True)

elif selection == "Brand Studio":
    st.header("Brand Studio")
    st.caption("Generate high-converting marketing assets aligned with your Brand DNA.")
    
    # Model Selection for Assets
    # assets_model = render_model_selector("assets", default_model=ai_engine.GEMINI_3_PRO_PREVIEW)
    assets_model = ai_engine.GEMINI_3_PRO_PREVIEW

    st.markdown("---")

    # Select Brand for Assets
    current_brand_id = render_brand_selector("assets")
    
    if not current_brand_id or "brand_data" not in st.session_state:
        st.stop()
        
    data = st.session_state.brand_data
    from utils.db import save_campaign, get_campaigns, save_asset
    from utils.ai_engine import generate_campaign_asset, repurpose_content, generate_counter_messaging, extract_brand_knowledge, parse_json_response, generate_image_prompt, generate_image_asset, generate_viral_hooks, generate_visual_html_asset
    
    # Model Selection for Assets
    # st.markdown("### ⚙️ Generator Settings") 
    # assets_model = render_model_selector("marketing_assets", default_model=ai_engine.GEMINI_3_PRO_PREVIEW)
    assets_model = ai_engine.GEMINI_3_PRO_PREVIEW # Hardcoded Smart Auto-Switching
    
    st.markdown("---")

    # --- 1. Campaign Management ---

    st.subheader("📂 Campaign Context")
    with st.expander("ℹ️ What are Campaigns?", expanded=False):
        st.markdown("""
        **Campaigns** allow you to group multiple assets (blogs, emails, posts) under a single goal.
        - **Example:** "Black Friday Sale" or "Q3 Product Launch".
        - Assets created within a campaign will automatically share the same underlying context and goals.
        """)
    
    # Fetch existing campaigns
    campaigns = []
    if data.get("db_id"):
        campaigns = get_campaigns(data["db_id"])
    
    campaign_options = ["Start New Campaign"] + [f"{c['name']}" for c in campaigns]
    selected_campaign_name = st.selectbox("Select Active Campaign", campaign_options)
    
    active_campaign = None
    
    if selected_campaign_name == "Start New Campaign":
        with st.expander("✨ Create New Campaign", expanded=True):
            new_camp_name = st.text_input("Campaign Name", placeholder="e.g., Q4 Product Launch")
            new_camp_goal = st.text_input("Campaign Goal", placeholder="e.g., Drive signups for Feature X")
            new_camp_theme = st.text_input("Overall Campaign Theme", placeholder="e.g., Innovation, Speed, Security", help="The high-level vibe or message for ALL assets in this campaign.")
            
            if st.button("Create Campaign"):
                if new_camp_name and data.get("db_id"):
                    cid = save_campaign(data["db_id"], new_camp_name, new_camp_goal, new_camp_theme)
                    st.success(f"Campaign '{new_camp_name}' created!")
                    st.rerun()
                elif not data.get("db_id"):
                    st.error("Please save the brand analysis first (happens automatically when analyzing).")
                else:
                    st.warning("Please enter a campaign name.")
    else:
        # Find the selected campaign object
        active_campaign = next((c for c in campaigns if c['name'] == selected_campaign_name), None)
        if active_campaign:
            st.info(f"**Active Campaign:** {active_campaign['name']} | **Goal:** {active_campaign['goal']}")

    st.markdown("---")

    # --- 2. Knowledge Graph Sidebar (or Expandable) ---
    # Check if we have KG data, if not, try to extract it or use placeholder
    if "knowledge_graph" not in st.session_state:
        st.session_state.knowledge_graph = None
        
    with st.sidebar:
        st.markdown("### 🧠 Brand Knowledge")
        
        # Use KG from brand_data if available (preferred), else check session_state.knowledge_graph (legacy/fallback)
        kg_source = None
        if "knowledge_graph" in data and data["knowledge_graph"]:
            kg_source = data["knowledge_graph"]
        elif "knowledge_graph" in st.session_state and st.session_state.knowledge_graph:
            kg_source = st.session_state.knowledge_graph
            
        if not kg_source:
            if st.button("🔄 Generate Knowledge Graph"):
                with st.spinner("Extracting products & features..."):
                    kg_json = extract_brand_knowledge(data["scrape"]["text"], model_name=assets_model)
                    st.session_state.knowledge_graph = parse_json_response(kg_json)
                    st.rerun()
        
        selected_products = []
        if kg_source:
            st.caption("Select products to feature:")
            
            if "products" in kg_source:
                # [UX UPGRADE] - Dropdown + Bulk Actions
                all_product_names = [p["name"] for p in kg_source["products"]]
                
                # Session state for selection
                if "bk_selected_products" not in st.session_state:
                    st.session_state.bk_selected_products = all_product_names # Default Select All

                # The Dropdown
                selected_names = st.multiselect(
                    "Include Products:",
                    options=all_product_names,
                    default=st.session_state.bk_selected_products,
                    key="bk_multiselect", # Unique key to avoid conflicts
                    on_change=lambda: st.session_state.update({"bk_selected_products": st.session_state.bk_multiselect})
                )
                
                # Sync back to local var for downstream logic
                st.session_state.bk_selected_products = selected_names # Ensure sync
                
                # Reconstruct the object list for the generator
                for prod in kg_source["products"]:
                    if prod["name"] in selected_names:
                        selected_products.append(prod)
                        
            with st.expander("View Details"):
                st.json(kg_source)
        else:
            st.info("Click Generate to extract structured product data.")

    # --- 3. Asset Creation Workflow ---
    st.subheader("🛠️ Create Assets")
    
    # Humanizer Controls
    with st.expander("🎚️ Humanizer Settings (Tone & Creativity)", expanded=False):
        h_col1, h_col2 = st.columns(2)
        with h_col1:
            # Temperature Slider
            creativity = st.select_slider(
                "Creativity Level",
                options=["Safe & Corporate", "Balanced", "Creative", "Edgy & Viral"],
                value="Balanced"
            )
            # Map to temperature
            temp_map = {
                "Safe & Corporate": 0.3,
                "Balanced": 0.7,
                "Creative": 0.9,
                "Edgy & Viral": 1.0
            }
            selected_temp = temp_map[creativity]
            
        with h_col2:
            # Complexity Slider
            complexity = st.select_slider(
                "Complexity Level",
                options=["Jargon-Heavy (Technical)", "Professional", "Accessible", "Simple (ELI5)"],
                value="Professional"
            )
            # Map to instruction
            tone_instruction = f"Target Audience Complexity Level: {complexity}. Tone & Style: {creativity}."
            if complexity == "Jargon-Heavy (Technical)":
                tone_instruction += " Use industry-specific terminology, assume high expertise."
            elif complexity == "Simple (ELI5)":
                tone_instruction += " Explain like I'm 5. Use simple analogies, avoid jargon."
            
            # [NEW] Explicit Style Instructions based on map
            if creativity == "Edgy & Viral":
                tone_instruction += " BE EDGY. Use short punchy sentences. Don't be afraid to be polarizing."
            elif creativity == "Funky": # If user added this
                tone_instruction += " Be eccentric and fun."
            elif creativity == "Safe & Corporate":
                 tone_instruction += " Maintain strict professional decorum."
    
            
    # Persona Selection (Moved Up)
    st.markdown("#### 👥 Target Audience & Strategy")
    
    # 1. Smart Persona Selector
    available_personas = data.get("personas", [])
    persona_options = ["Custom (Type Manually)"] + [p['role'] for p in available_personas]
    
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        selected_p_role = st.selectbox("Select Target Persona", persona_options)
    
    selected_persona = None
    if selected_p_role == "Custom (Type Manually)":
        with col_p2:
            custom_role = st.text_input("Enter Persona Role", placeholder="e.g., Busy Mom", help="Leave empty to use the Brand's Core Audience automatically.")
            if custom_role:
                selected_persona = {"role": custom_role}
            else:
                # --- Smart Fallback Logic ---
                # If no custom role is entered, try to use the Brand Core Audience
                analysis_data = data.get("analysis") or {}
                core_audience = analysis_data.get("target_audience_summary")
                
                if core_audience:
                    # Create a lightweight persona object from the summary
                    selected_persona = {"role": core_audience}
                    st.info(f"🎯 **Auto-Targeting:** Keying off Brand Core Audience\n\n*'{core_audience}'*")
                else:
                    st.caption("ℹ️ No specific audience selected. Content will be written for a **General Audience**.")
    else:
        # Find the full persona object
        selected_persona = next((p for p in available_personas if p['role'] == selected_p_role), None)
        with col_p2:
            if selected_persona:
                st.info(f"**Pain Points:** {', '.join(selected_persona.get('pain_points', [])[:3])}...")

    st.markdown("---")



    # 2. SEO Keywords Integration
    # Consolidated into the main flow below.
    # Removed generic "Target Keywords (SEO Mode)" dropdown.

    
    # 3. Strict Brand Voice (Enforced by DNA Lock)
    strict_voice = True 
    # st.checkbox("🔒 Enforce Strict Brand Voice (DNA Lock)", value=True, help="Forces AI to strictly adhere to the identified Brand DNA, preventing generic output.")

    # [NEW] Visual DNA Badge
    design_tokens = data.get("design_tokens", {})
    if design_tokens and len(design_tokens) > 1:
        st.markdown(f"""
        <div style="background:#f0fdf4; border:1px solid #22c55e; padding:10px; border-radius:8px; margin-bottom:15px;">
            <span style="font-weight:bold; color:#15803d;">🧬 Visual DNA Locked:</span> 
            <span style="color:#166534;">Using extracted brand colors <span style="background:{design_tokens.get('primary_color', '#000')}; color:white; padding:2px 6px; border-radius:4px; font-size:0.8rem;">{design_tokens.get('primary_color', 'N/A')}</span> and fonts.</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.caption("⚠️ Visual DNA not extracted. Using AI inference for colors.")

    st.markdown("---")
    
    mode = st.radio("Select Mode", ["✨ New Asset", "♻️ Repurpose Asset"], horizontal=True)
    
    # Context Retrieval (The DNA Lock)
    brand_voice_profile = data.get("analysis", {}).get("brand_voice", "")
    if not brand_voice_profile:
        st.warning("⚠️ Brand Voice Profile missing. Please run 'Brand Analysis' first to unlock high-quality generation.")
        
    # AEO Keywords (The SEO Lock)
    aeo_keywords = data.get("key_terms", [])
    # Try to fetch from AEO Analysis session state if available for fresher data
    if "aeo_meta" in st.session_state:
        aeo_keywords = st.session_state.aeo_meta.get("keywords", []) + aeo_keywords
    
    # De-duplicate
    aeo_keywords = list(set(aeo_keywords))

    if mode == "✨ New Asset":
        col1, col2 = st.columns(2)
        with col1:
            asset_type = st.selectbox("Asset Type", [
                "Blog Post", 
                "Whitepaper", 
                "Case Study", 
                "Landing Page Copy", 
                "Email Newsletter", 
                "Cold Email (Outreach)", 
                "Instagram Post (Visual)", 
                "TikTok/Reels Script", 
                "LinkedIn Post (Professional)", 
                "LinkedIn Carousel (PDF/Images)",
                "Twitter/X Thread (Viral)", 
                "WhatsApp/SMS Message (Direct)", 
                "Video Script (Long Form)", 
                "Press Release"
            ])
        with col2:
            # Create from Scratch Logic
            camp_theme = active_campaign['theme'] if active_campaign else ""
            
            custom_theme = st.text_input("Topic / Theme", value=camp_theme, help="What is this specific piece of content about?")
            
        asset_goal = st.text_input("Asset Goal", placeholder="e.g., 'Rank for [Keyword]' (Search) or 'Challenge a belief about X' (Social)", help="What is the primary objective?")
        
        # [NEW] Funnel Stage Selection
        funnel_stage = st.selectbox(
            "Target Funnel Stage", 
            ["ToFU (Awareness)", "MoFU (Consideration)", "BoFU (Decision)"],
            index=0, # Default to ToFU
            help="ToFU: Educate & Entertain. MoFU: Prove & Compare. BoFU: Convert & Close."
        )

        # SEO Lock Integration
        if not aeo_keywords:
             col_seo_input, col_seo_btn = st.columns([4, 1])
             with col_seo_input:
                 aeo_keywords_input = st.text_input("🔒 Target Keywords & AEO/SEO Strategy (Required)", placeholder="keyword1, keyword2", help="These keywords ensure your content is optimized for both traditional Search Engines (SEO) and modern AI Answer Engines (AEO). If you don't have any, click 'Suggest' for AI-powered ideas.")
             with col_seo_btn:
                 st.write(" ") # Alignment
                 if st.button("🪄 Suggest"):
                     with st.spinner("Analyzing DNA..."):
                         suggested = ai_engine.suggest_aeo_keywords(data["scrape"]["text"], data["analysis"], data.get("personas"), model_name=assets_model)
                         if suggested:
                             if "aeo_meta" not in st.session_state:
                                 st.session_state.aeo_meta = {}
                             st.session_state.aeo_meta["keywords"] = suggested
                             st.rerun()
             
             if aeo_keywords_input:
                 aeo_keywords = [k.strip() for k in aeo_keywords_input.split(",")]
        else:
             # Allow user to refine
             brand_term = data.get("analysis", {}).get("brand_name", "Brand Term")
             # Ensure Brand Term is in defaults if it's in options (it is added to options below)
             # We take top 3 AI keywords + Brand Term as default
             default_keys = aeo_keywords[:3]
             if brand_term not in default_keys:
                 default_keys.append(brand_term)
                 
             aeo_keywords = st.multiselect("🔒 Target Keywords & AEO/SEO Strategy", options=aeo_keywords + [brand_term], default=default_keys, help="Selected keywords will be naturally integrated into key areas of the content (Headers, Intro) to boost both SEO and AEO visibility.")


        if st.button("Generate Asset", type="primary"):
            if not custom_theme or not asset_goal:
                st.warning("Please enter a Topic and Goal.")
            elif not aeo_keywords:
                 st.warning("⚠️ Visibility Lock Active: You MUST define target keywords to ensures AEO/SEO ranking.")
            else:
                with st.spinner("Generating asset with DNA & AEO/SEO Strategy Locks..."):
                    # Construct Context (Dual Layer: Asset + Campaign)
                    camp_ctx = {
                        "name": active_campaign['name'] if active_campaign else "General Brand Awareness",
                        "goal": asset_goal, # Specific Tactical Goal
                        "theme": custom_theme,
                        "parent_goal": active_campaign['goal'] if active_campaign else "Increase Brand Awareness", # Strategic Campaign Goal
                        "parent_theme": active_campaign['theme'] if active_campaign else "Professional & Engaging" # Strategic Vibe
                    }
                    
                    # Filter KG for context while preserving Vocabulary Lock
                    kg_context = {}
                    # 1. Always include Key Terms if available
                    if "knowledge_graph" in data and "key_terms" in data["knowledge_graph"]:
                        kg_context["key_terms"] = data["knowledge_graph"]["key_terms"]
                    
                    # 2. Include selected products
                    if selected_products:
                        kg_context["products"] = selected_products
                    
                    # Extract Visual Identity
                    visual_identity = data.get("analysis", {}).get("visual_identity", None)
                    
                    content = generate_campaign_asset(
                        data["scrape"]["text"], 
                        asset_type, 
                        custom_theme, 
                        camp_ctx, 
                        knowledge_graph=kg_context,
                        model_name=assets_model,
                        temperature=selected_temp,
                        tone_instruction=tone_instruction,
                        persona_details=selected_persona,
                        seo_keywords=aeo_keywords,
                        strict_voice=strict_voice,
                        brand_voice_desc=brand_voice_profile,
                        visual_identity=visual_identity,
                        design_tokens=data.get("design_tokens"),
                        brand_archetype=data.get("analysis", {}).get("brand_archetype"),
                        brand_dna=data.get("analysis"), # Passes full analysis dict (containing enemy/cause)
                        funnel_stage=funnel_stage # [NEW]
                    )
                    st.session_state.generated_asset = content
                    st.session_state.asset_meta = {"type": asset_type, "theme": custom_theme}
                    
                    # --- NEW: Generate Specialized Visual HTML ---
                    st.session_state.generated_visual_html = generate_visual_html_asset(asset_type, content, data, model_name=assets_model)
                    
                    # Image Generation Logic
                    img_url = None
                    # [UPDATED] check includes Repurpose formats ("LinkedIn Post", "Instagram Caption")
                    if asset_type in ["Instagram Post (Visual)", "Instagram Caption", "LinkedIn Post (Professional)", "LinkedIn Post", "Blog Post", "Press Release", "Case Study", "Whitepaper"]:
                        with st.status("🎨 Generating Visuals...", expanded=True):
                            st.write("Drafting image prompt with Visual DNA...")
                            img_prompt = generate_image_prompt(
                                custom_theme, 
                                asset_type, 
                                style="Modern", # Default, can be upgraded later
                                creativity=creativity, 
                                persona_details=selected_persona,
                                model_name=assets_model,
                                visual_identity=data.get("analysis", {}).get("visual_identity")
                            )
                            st.session_state.generated_image_prompt = img_prompt
                            st.write("Rendering image...")
                            
                            # Extract Brand Color
                            b_color = "667eea" # Default Blue
                            if "knowledge_graph" in data and data["knowledge_graph"] and "brand_colors" in data["knowledge_graph"]:
                                colors = data["knowledge_graph"]["brand_colors"]
                                if colors:
                                    b_color = colors[0]

                            api_key = os.getenv("OPENAI_API_KEY")
                            img_url = generate_image_asset(img_prompt, api_key=api_key, brand_color=b_color)
                            st.session_state.generated_image_url = img_url
                    
                            st.session_state.generated_image_url = img_url
                            
                            # [NEW] Auto-Switch to Visuals view if image generated (Except for Blog Post which shows it inline)
                            if img_url and "placehold" not in img_url and asset_type != "Blog Post":
                                st.session_state.campaign_board_view = "🎨 Visuals"
                    
                    # Save
                    cid = active_campaign['id'] if active_campaign else None
                    p_target = selected_persona.get('role') if selected_persona else None
                    save_asset(data["db_id"], asset_type, content, persona_target=p_target, image_url=img_url, campaign_id=cid, metadata_json={"theme": custom_theme})
                    st.toast("Saved to Campaign!", icon="💾")

                    # --- POWER MODE: Auto-Generate Bundle ---



    elif mode == "♻️ Repurpose Asset":
        st.info("ℹ️ Transform existing content into new formats while matching your Brand Voice.")
        
        # Input Source
        input_method = st.radio("Source Input", ["Paste Text", "File Upload"], horizontal=True, label_visibility="collapsed")
        
        source_text = ""
        if input_method == "Paste Text":
            source_text = st.text_area("Paste Source Content", height=200, placeholder="Paste blog post, case study, or notes here...")
        else:
            uploaded_file = st.file_uploader("Upload content (TXT, MD)", type=['txt', 'md'])
            if uploaded_file is not None:
                source_text = str(uploaded_file.read(), "utf-8")
                st.success(f"Loaded {len(source_text)} characters.")
        
        target_format = st.selectbox("Convert To", ["Twitter Thread", "LinkedIn Post", "Instagram Caption", "Email Summary", "TL;DR Bullet Points", "Blog Post"])
        
        # SEO Lock for Repurpose too?
        aeo_keywords = st.multiselect("🔒 SEO Lock: Inject Keywords (Optional for Repurpose)", options=aeo_keywords + ["Brand Term"], default=[])

        if st.button("♻️ Repurpose Content"):
            if not source_text:
                st.warning("Please provide source content.")
            else:
                with st.spinner("Remixing content with Brand DNA..."):
                    remixed = repurpose_content(
                        source_text, 
                        target_format, 
                        model_name=assets_model,
                        temperature=selected_temp,
                        tone_instruction=tone_instruction,
                        persona_details=selected_persona,
                        brand_voice_desc=brand_voice_profile if strict_voice else "",
                        seo_keywords=aeo_keywords
                    )
                    st.session_state.generated_asset = remixed
                    st.session_state.asset_meta = {"type": target_format, "theme": "Repurposed Asset"}

    # --- 4. Result Display & Visuals (The Campaign Board) ---
    if "generated_asset" in st.session_state:
        st.markdown("---")
        st.subheader("🚀 Campaign Board")
        
        # Navigation (Using Search params logic or Radio to prevent tab reset on button click)
        # Using horizontal radio as a stable tab replacement
        
        # Define the views based on context
        # Define the views based on context
        views = ["📄 Content"]
        
        # Context-Aware Tabs
        asset_type = st.session_state.asset_meta.get("type", "")
        
        # VISUALS TAB LOGIC:
        # Hide Visuals for purely text-based/script formats where an image generator isn't relevant
        visuals_excluded = [
            "Email Newsletter",
            "Cold Email (Outreach)",
            "WhatsApp/SMS Message (Direct)",
            "Video Script (Long Form)",
            # "Blog Post",     # REMOVED: Now supported
            # "Whitepaper",    # REMOVED: Now supported
            # "Case Study"     # REMOVED: Now supported
        ]
         # Show Visuals by default unless excluded
        if asset_type not in visuals_excluded:
             views.append("🎨 Visuals")

        # EMAIL TAB LOGIC:
        # Consolidated: Email is now just a format, not a separate view in the board unless explicitly generated as a draft.
        # Removing the radio button to declutter as per user request. 
        # email_excluded = ... (Removed)
        # if asset_type not in email_excluded:
        #      views.insert(1, "📧 Email")
        
        # CODE TAB LOGIC:
        # Hide Code for purely visual assets (User Request)
        if asset_type not in ["Instagram Post (Visual)"]:
             views.append("👨‍💻 Code")
        
        # Maintain state for the view
        if "campaign_board_view" not in st.session_state:
            st.session_state.campaign_board_view = "📄 Content"
            
        # Safety check if view no longer valid (switched asset types)
        if st.session_state.campaign_board_view not in views:
             st.session_state.campaign_board_view = "📄 Content"
            
        current_view = st.radio(
            "Campaign View", 
            views, 
            horizontal=True, 
            key="campaign_board_view", 
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        final_content = st.session_state.generated_asset
        
        # --- VIEW: CONTENT ---
        if current_view == "📄 Content":
            
            # [NEW] Dynamic Visual Integration for Blog Posts & Case Studies
            if asset_type in ["Blog Post", "Case Study", "Whitepaper"] and "generated_image_url" in st.session_state and st.session_state.generated_image_url:
                img_url = st.session_state.generated_image_url
                if "[INSERT_IMAGE_HERE]" in final_content:
                    parts = final_content.split("[INSERT_IMAGE_HERE]")
                    render_content_with_mermaid(parts[0])
                    st.image(img_url, caption="Hero Image (Smart Placement)", use_container_width=True)
                    if len(parts) > 1:
                         render_content_with_mermaid(parts[1])
                else:
                    # Fallback to Top
                    st.image(img_url, caption="Hero Image", use_container_width=True)
                    render_content_with_mermaid(final_content)
            else:
                # Standard Render (with Mermaid support)
                render_content_with_mermaid(final_content)
            
            st.download_button(
                "📥 Download Markdown", 
                final_content, 
                f"asset_{st.session_state.asset_meta.get('type', 'draft')}.md"
            )
            
            # PDF Download
            if st.button("📥 Download PDF"):
                with st.spinner("Generating PDF..."):
                    pdf_data = pdf_gen.generate_asset_report(
                        st.session_state.asset_meta.get('type', 'Asset'),
                        final_content,
                        {
                            "theme": st.session_state.asset_meta.get('theme'),
                            "goal": "Generated by AI", # Could track actual goal if in session state
                            "persona": "Target Audience",
                            "campaign": active_campaign['name'] if active_campaign else None
                        },
                        data.get("brand_name", "Brand")
                    )
                    st.download_button(
                        label="📄 Click to Save PDF",
                        data=pdf_data,
                        file_name=f"Asset_{st.session_state.asset_meta.get('type', 'draft')}.pdf",
                        mime="application/pdf"
                    )

        # --- VIEW: CODE ---
        elif current_view == "👨‍💻 Code":
            st.markdown("#### 👨‍💻 Deployment & Source Code")
            st.markdown("""
            This is the **raw Markdown source code** for your asset. 
            - **How to use:** Copy this and paste it into any Markdown-supported editor (Notion, Obsidian, WhatsApp, Slack, Ghost, Hugo, etc.).
            - **Formatting:** It contains all the bolding, headers, and structure hidden in the visual view.
            """)
            
            st.text_area("Raw Markdown (Copy from here)", value=final_content, height=300)
            
            # Keep the old code block for syntax highlighting reference
            with st.expander("View Syntax Highlighted Source"):
                 st.code(final_content, language="markdown")
            
            if "```" in final_content:
                st.info("💡 Pro Tip: Code snippets detected in the content above.")

        # --- VIEW: VISUALS ---
        elif current_view == "🎨 Visuals":
            
            st.markdown("#### 🎨 Asset Visuals")
            
            # 1. Render High-Fidelity HTML Visuals (Carousels/Cards) -> The "Stunning Visual" user requested
            if "generated_visual_html" in st.session_state and st.session_state.generated_visual_html:
                 st.success("✅ Smart-Visual Asset Generated")
                 # Use a larger height for carousel visibility
                 st.components.v1.html(st.session_state.generated_visual_html, height=600, scrolling=True)
                 st.download_button("📥 Download HTML Visuals", st.session_state.generated_visual_html, "visual_asset.html", "text/html")
                 st.markdown("---")
            
            # 2. Main Image (DALL-E / Placeholder)
            # 2. Main Image (DALL-E / Placeholder)
            if "generated_image_url" in st.session_state and st.session_state.generated_image_url:
                st.image(st.session_state.generated_image_url, caption="AI Generated Image Concept", use_container_width=True)
            else:
                if st.button("✨ Generate AI Image Concept"):
                     with st.spinner("Dreaming up a visual..."):
                         try:
                             # Generate Prompt
                             img_prompt = generate_image_prompt(
                                st.session_state.asset_meta.get('theme', 'Brand Theme'), 
                                st.session_state.asset_meta.get('type', 'General'), 
                                "Balanced",  # Default
                                persona_details=data.get('personas', [{}])[0],
                                model_name=assets_model
                             )
                             # Generate Image
                             api_key = os.getenv("OPENAI_API_KEY")
                             # Default color
                             b_color = "667eea"
                             if "knowledge_graph" in data and data["knowledge_graph"] and "brand_colors" in data["knowledge_graph"]:
                                 colors = data["knowledge_graph"]["brand_colors"]
                                 if colors: b_color = colors[0]

                             img_url = generate_image_asset(img_prompt, api_key=api_key, brand_color=b_color)
                             st.session_state.generated_image_url = img_url
                             st.rerun()
                         except Exception as e:
                             st.error(f"Image generation failed: {e}")

            st.markdown("---")
            st.markdown("#### 📇 Social Share Card (HTML)")
            
            # Social Card Generator (Legacy manual button)
            if st.button("🎨 Generate Social Card HTML", key="gen_card_2"):
                with st.spinner("Designing visual..."):
                    from utils.ai_engine import generate_social_card_html, clean_html_response
                    brand_style = "Modern, Professional"
                    if "knowledge_graph" in data and data["knowledge_graph"] and "brand_colors" in data["knowledge_graph"]:
                         colors = data["knowledge_graph"]["brand_colors"]
                         if colors:
                             brand_style += f". Brand Colors: {', '.join(colors)}"
                    
                    raw_html = generate_social_card_html(st.session_state.asset_meta.get('theme', 'Brand Update'), brand_style=brand_style, model_name=assets_model)
                    clean_html = clean_html_response(raw_html)
                    st.session_state.generated_card_html = clean_html
            
            if "generated_card_html" in st.session_state:
                 st.components.v1.html(st.session_state.generated_card_html, height=400, scrolling=True)
                 st.download_button("📥 Download HTML Card", st.session_state.generated_card_html, "social_card.html", "text/html")



        # --- VIEW: EMAIL (REMOVED as per user request to declutter) ---
        # Logic moved to asset generation types.



if selection == "Brand Management":
    # 1. Brand Selector (Reuse common logic but specific to management)
    st.header("⚙️ Brand Management")
    st.caption("Manage your saved brand profiles and account settings.")
    st.caption("Manage your brand data, delete unwanted reports, and keep your workspace clean.")

    # Fetch brands
    from utils.brand_manager import get_all_brands
    all_brands = get_all_brands()
    
    # Create simple dictionary for lookup
    brand_map = {f"{b['name']} ({b['last_updated_relative']})": b['id'] for b in all_brands}
    brand_options = ["Select a Brand..."] + list(brand_map.keys())
    
    selected_brand_opt = st.selectbox("Select Brand to Manage", brand_options)
    
    brand_id = None
    if selected_brand_opt != "Select a Brand...":
        brand_id = brand_map[selected_brand_opt]
    
    if brand_id:
        # Load Stats
        stats = get_brand_stats(brand_id)
        
        # Stats Cards
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Analyzed URLs", stats["urls"])
        col2.metric("AEO Reports", stats["aeo_reports"])
        col3.metric("Assets", stats["assets"])
        col4.metric("Campaigns", stats["campaigns"])
        
        st.markdown("---")
        
        # Tabs for different management aspects
        tab_gen, tab_urls, tab_aeo, tab_assets = st.tabs(["General", "URLs", "AEO Reports", "Marketing Assets"])
        
        with tab_gen:
            st.subheader("General Settings")
            st.info("Manage high-level brand settings here.")
            
            # Rename
            current_name = selected_brand_opt.split(" (")[0]
            new_name = st.text_input("Rename Brand", value=current_name)
            if st.button("Update Brand Name"):
                if new_name and new_name != current_name:
                    if rename_brand(brand_id, new_name):
                        st.success("Brand renamed successfully!")
                        st.rerun()
            
            st.divider()
            
            # Delete Brand
            st.error("Danger Zone")
            st.caption("Deleting a brand is irreversible and will remove ALL associated data.")
            if st.button("🗑️ Delete Entire Brand", type="primary"):
                 st.session_state.confirm_delete_all = True
            
            if st.session_state.get("confirm_delete_all"):
                st.warning(f"Are you sure you want to delete **{current_name}**? This cannot be undone.")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Yes, Delete Everything", type="primary", key="confirm_del_final"):
                        if delete_brand(brand_id):
                            st.success("Brand deleted.")
                            # Clear Session State
                            keys_to_clear = [
                                "brand_name_input", "brand_urls", "url_ids", "brand_data", 
                                "existing_brand_id", "saved_competitor_url", "suggested_links", 
                                "scrape_error", "brand_name_detected", "brand_health", "confirm_delete_all"
                            ]
                            for k in keys_to_clear:
                                if k in st.session_state:
                                    del st.session_state[k]
                                    
                            st.rerun()
                with c2:
                    if st.button("Cancel", key="cancel_del_final"):
                         st.session_state.confirm_delete_all = False
                         st.rerun()

        with tab_urls:
             # List URLs
             st.subheader("Managed URLs")
             urls = get_brand_urls(brand_id)
             if urls:
                 for u in urls:
                     with st.container():
                         c1, c2 = st.columns([5, 1])
                         c1.markdown(f"**{u['url']}**")
                         c1.caption(f"Type: {u['page_type']}")
                         if c2.button("🗑️", key=f"del_url_manage_{u['url']}", help="Delete URL"):
                             if delete_brand_url(brand_id, u['url']):
                                 st.success("Deleted")
                                 st.rerun()
                         st.divider()
             else:
                 st.info("No URLs found for this brand.")

        with tab_aeo:
            # List AEO Reports
            st.subheader("AEO Analysis History")
            reports = get_brand_aeo_reports(brand_id)
            if reports:
                for r in reports:
                    with st.expander(f"📅 {r['date']} - {r['query']} (Rank: {r['rank']})"):
                        st.json(r)
                        if st.button("Delete Report", key=f"del_aeo_{r['id']}"):
                            if delete_aeo_analysis(r['id']):
                                st.success("Report deleted")
                                st.rerun()
            else:
                st.info("No AEO reports found.")

        with tab_assets:
            # List Assets
            st.subheader("Marketing Assets Repository")
            assets = get_brand_assets(brand_id)
            if assets:
                for a in assets:
                    with st.expander(f"📄 {a['type']} - {a['date']}"):
                        st.caption(f"Campaign ID: {a['campaign_id']}")
                        st.markdown(f"**Preview:** {a['content_preview']}")
                        if st.button("Delete Asset", key=f"del_asset_{a['id']}"):
                            if delete_marketing_asset(a['id']):
                                st.success("Asset deleted")
                                st.rerun()
            else:
                st.info("No marketing assets found.")


# Footer
st.markdown("---")
st.markdown("Built with ❤️ using Streamlit & Gemini")
