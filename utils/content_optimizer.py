import streamlit as st
import utils.ai_engine as ai_engine

def _build_voice_prompt(brand_data, content):
    """
    Constructs a robust prompt to rewrite content in the brand's voice.
    """
    voice = brand_data.get("analysis", {}).get("brand_voice", "Professional and clear")
    archetype = brand_data.get("analysis", {}).get("brand_archetype", "N/A")
    mission = brand_data.get("analysis", {}).get("brand_mission", "N/A")
    
    # Extract style tokens if available suitable for a prompt
    style_guide = ""
    personas = brand_data.get("personas", [])
    if personas:
        # Use the first persona's hook as a target audience hint
        target_audience = personas[0].get("role", "General Audience")
        style_guide += f"\n- **Target Audience**: {target_audience}"
        
    prompt = f"""
    You are an expert Content Strategist and Copywriter for a brand with the following DNA:
    
    **Brand Identity:**
    - **Voice**: {voice}
    - **Archetype**: {archetype}
    - **Mission**: {mission}
    {style_guide}
    
    **Task:**
    Rewrite the following content to perfectly match this brand identity. 
    
    **Guidelines:**
    1.  **Tone Match**: Ensure the tone is consistent with the Voice defined above.
    2.  **Vocabulary**: Use words that align with the Archetype (e.g., if 'Magician', use transformative language; if 'Sage', use knowledgeable language).
    3.  **Clarity**: Keep it engaging and easy to read.
    4.  **Format**: Maintain the original structure (headings, paragraphs) but improve the flow.
    
    **Original Content:**
    "{content}"
    
    **Rewritten Content (Refined & On-Brand):**
    """
    return prompt

def _build_authority_prompt(brand_data, content):
    """
    Constructs a prompt to inject authority markers (Knowledge Graph entities).
    """
    kg = brand_data.get("knowledge_graph", {})
    products = [p.get('name') for p in kg.get('products', [])]
    key_terms = kg.get('key_terms', [])
    
    # Format lists for the prompt
    products_str = ", ".join(products[:5]) if products else "N/A"
    terms_str = ", ".join(key_terms[:5]) if key_terms else "N/A"
    
    prompt = f"""
    You are an AEO (Answer Engine Optimization) Specialist. Your goal is to maximize the 'Information Gain' and 'Authority' of content.
    
    **Brand Authority Assets:**
    - **Core Products**: {products_str}
    - **Key Industry Terms**: {terms_str}
    
    **Task:**
    Enhance the text below by naturally weaving in the specific products and key terms listed above where relevant.
    
    **Rules:**
    1.  **No Stuffing**: Do NOT force keywords if they don't fit. Context is king.
    2.  **Specifics over Generics**: Replace generic words with our specific terminology (e.g., change "our tool" to "{products[0] if products else 'our specific solution'}").
    3.  **Fact-Based**: Make the content sound more authoritative and expert-driven.
    
    **Content to Enhance:**
    "{content}"
    
    **Authority-Boosted Version:**
    """
    return prompt

def _build_humanize_prompt(content):
    """
    Constructs a prompt to remove 'AI-sounding' patterns.
    """
    prompt = f"""
    You are a Senior Editor. A junior copywriter submitted the text below, but it sounds a bit too robotic or "AI-generated".
    
    **Task:**
    Humanize the text. Make it sound natural, conversational, and authentic.
    
    **Fixes Needed:**
    1.  **Vary Sentence Length**: Mix short punchy sentences with longer ones.
    2.  **Remove Fluff**: Cut unnecessary transition words like "Furthermore", "In conclusion", "It is important to note".
    3.  **Active Voice**: Switch passive voice to active where possible.
    4.  **Idioms**: Use natural phrasing, not stiff academic language.
    
    **Draft Text:**
    "{content}"
    
    **Humanized Polished Version:**
    """
    return prompt

def optimize_content(content, mode, brand_data):
    """
    Main function to optimize content based on the selected mode.
    
    Args:
        content (str): The raw text to optimize.
        mode (str): 'voice', 'authority', or 'humanize'.
        brand_data (dict): The loaded brand data from session state.
        
    Returns:
        str: The rewritten content.
    """
    if not content or not content.strip():
        return "Please enter some content to optimize."
        
    prompt = ""
    
    if mode == "voice":
        prompt = _build_voice_prompt(brand_data, content)
    elif mode == "authority":
        prompt = _build_authority_prompt(brand_data, content)
    elif mode == "humanize":
        prompt = _build_humanize_prompt(content)
    else:
        return content
        
    try:
        # Use the highest reasoning model for best rewriting results
        response = ai_engine.generate_gemini_response(prompt, model_name=ai_engine.GEMINI_3_PRO_PREVIEW)
        return response
    except Exception as e:
        return f"Error optimizing content: {str(e)}"

def render_content_optimizer(brand_data):
    """
    Renders the UI for the Content Optimizer feature.
    """
    st.header("✨ Content Optimizer")
    st.caption("AI-Assisted Editor to align content with your Brand DNA and boost AEO Authority.")
    
    if not brand_data or not brand_data.get("analysis"):
        st.warning("Please select a valid Brand from the sidebar to load its DNA.")
        return

    # --- Top Bar: Context ---
    # Show what "Voice" we are optimizing for
    voice = brand_data.get("analysis", {}).get("brand_voice", "N/A")
    archetype = brand_data.get("analysis", {}).get("brand_archetype", "N/A")
    
    st.markdown(f"""
    <div style="background-color:#f8f9fa; padding:1rem; border-radius:8px; border:1px solid #e9ecef; margin-bottom:1rem; display:flex; gap:2rem; align-items:center;">
        <div><strong>Target Voice:</strong> <span style="color:#667eea;">{voice}</span></div>
        <div><strong>Archetype:</strong> <span style="color:#667eea;">{archetype}</span></div>
    </div>
    """, unsafe_allow_html=True)

    # --- Editor Layout ---
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("📝 Original Draft")
        
        # Initialize session state for the input text if not present
        if "optimizer_input_text" not in st.session_state:
            # Default to scraped text if available to help user start
            st.session_state.optimizer_input_text = brand_data.get("scrape", {}).get("text", "")[:1000] # Limit default load
            
        input_text = st.text_area("Paste your content here...", 
                                  value=st.session_state.optimizer_input_text,
                                  height=500,
                                  key="opt_input")
        st.session_state.optimizer_input_text = input_text

    with col_right:
        st.subheader("✨ Optimized Result")
        
        # Output Area
        if "optimized_output" not in st.session_state:
            st.session_state.optimized_output = ""
            
        st.text_area("AI Output", value=st.session_state.optimized_output, height=500, disabled=True)

    # --- Control Bar (Bottom or Middle) ---
    st.markdown("---")
    st.subheader("⚡ Optimization Actions")
    
    c1, c2, c3 = st.columns(3)
    
    with c1:
        if st.button("🎭 Apply Brand Voice", use_container_width=True, type="primary"):
            with st.spinner("Rewriting in brand voice..."):
                res = optimize_content(input_text, "voice", brand_data)
                st.session_state.optimized_output = res
                st.rerun()
                
    with c2:
        if st.button("🧠 Inject Authority (AEO)", use_container_width=True):
            with st.spinner("Injecting Knowledge Graph entities..."):
                res = optimize_content(input_text, "authority", brand_data)
                st.session_state.optimized_output = res
                st.rerun()
                
    with c3:
        if st.button("😊 Humaize & Polish", use_container_width=True):
            with st.spinner("Smoothing out robotic phrasing..."):
                res = optimize_content(input_text, "humanize", brand_data)
                st.session_state.optimized_output = res
                st.rerun()

    # --- Diff Viewer (Optional Enhancement) ---
    if st.session_state.optimized_output and st.session_state.optimized_output != input_text:
        with st.expander("👀 View Changes (Diff)", expanded=False):
            # Simple Diff visualization
            import difflib
            
            # Using standard streamlit columns to show simple side-by-side or just text
            # For a proper diff we'd need a component, but let's stick to standard widgets for reliability
            st.caption("Copy the optimized text above to use it.")
