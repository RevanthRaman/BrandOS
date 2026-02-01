import streamlit as st

def setup_app_styling():
    """
    Injects global CSS to transform the Streamlit app into 'BrandOS' - a Premium Enterprise Experience.
    Theme: Midnight Executive (Dark Sidebar, Light Main, Indigo Accents)
    """
    st.markdown("""
    <style>
    /* IMPORTS */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Inter+Tight:wght@600;700&display=swap');
    
    /* GLOBAL VARIABLES - THEME: Midnight Executive */
    :root {
        --primary: #0f172a; /* Slate 900 (Obsidian) */
        --accent: #6366f1; /* Indigo 500 (Electric Indigo) */
        --accent-glow: rgba(99, 102, 241, 0.15);
        --bg-sidebar: #0f172a; /* Deep distinct dark */
        --bg-body: #f8fafc; /* Slate 50 (Platinum Mist) */
        --bg-card: #ffffff;
        --text-main: #0f172a; /* Ink Black for readability */
        --text-sidebar: #f1f5f9; /* White/Light for contrast in sidebar */
        --text-muted: #64748b;
        --border-light: #e2e8f0;
        --border-dark: #334155; /* For sidebar dividers */
        --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
        --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
    }

    /* TYPOGRAPHY */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
        color: var(--text-main);
        background-color: var(--bg-body);
    }
    
    h1, h2, h3 {
        font-family: 'Inter Tight', sans-serif !important;
        letter-spacing: -0.025em !important;
        color: var(--primary) !important;
    }
    
    /* 1. APP CONTAINER & MAIN AREA (Platinum) */
    .stApp {
        background-color: var(--bg-body);
    }
    .main .block-container {
        padding-top: 2rem;
        max-width: 950px !important;
    }

    /* 2. SIDEBAR (Obsidian) */
    [data-testid="stSidebar"] {
        background-color: var(--bg-sidebar);
        border-right: 1px solid var(--border-dark);
    }
    /* Sidebar Text Adjustments */
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: white !important;
    }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label {
        color: #cbd5e1 !important; /* Slate 300 for soft white text */
    }
    
    /* BRANDOS SIDEBAR LOGO */
    .brand-os-logo {
        font-family: 'Inter Tight', sans-serif;
        font-weight: 800;
        font-size: 2.2rem;
        /* Gradient suitable for Dark Background */
        background: linear-gradient(135deg, #ffffff 0%, #94a3b8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 2rem;
        letter-spacing: -0.02em;
        padding-left: 0.5rem;
        text-shadow: 0 2px 10px rgba(99, 102, 241, 0.2);
    }

    /* 3. NAVIGATION PILLS (Sidebar) */
    /* Hide Radio Button */
    .stRadio [role="radiogroup"] > label > div:first-child {
        display: none !important;
    }
    
    /* Unselected Tab */
    .stRadio [role="radiogroup"] > label {
        padding: 0.75rem 1rem !important;
        background-color: rgba(255,255,255,0.03) !important;
        border-radius: 8px !important;
        margin-bottom: 0.4rem !important;
        border: 1px solid transparent !important;
        color: #94a3b8 !important; /* Slate 400 */
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }
    
    /* Hover */
    .stRadio [role="radiogroup"] > label:hover {
        background-color: rgba(255,255,255,0.1) !important;
        color: white !important;
        transform: translateX(4px);
    }
    
    /* Active Tab */
    .stRadio [role="radiogroup"] > label:has(input:checked) {
        background: linear-gradient(90deg, rgba(99, 102, 241, 0.2) 0%, rgba(99, 102, 241, 0.05) 100%) !important;
        color: #818cf8 !important; /* Indigo 400 */
        font-weight: 600 !important;
        border: 1px solid rgba(99, 102, 241, 0.3) !important;
        border-left: 4px solid var(--accent) !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2) !important;
    }

    /* 4. CARDS & INSIGHTS (Light on Light Background) */
    .insight-card {
        background: white; /* Clean White */
        padding: 2rem;
        border-radius: 12px;
        box-shadow: var(--shadow-md);
        border: 1px solid var(--border-light);
        border-top: 4px solid var(--accent);
        margin-bottom: 2rem;
        color: var(--text-main); /* Force Dark Text */
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid var(--border-light);
        box-shadow: var(--shadow-sm);
        transition: all 0.2s;
        color: var(--text-main); /* Force Dark Text */
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-md);
        border-color: #cbd5e1;
    }

    /* 5. INPUTS & FORM ELEMENTS (High Readability) */
    /* Force white background and dark text for all inputs */
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
        background-color: #ffffff !important;
        color: #0f172a !important; /* Ink Black */
        -webkit-text-fill-color: #0f172a !important; /* Fix for Safari/Chrome */
        caret-color: #0f172a !important; /* Cursor color */
        border: 1px solid #cbd5e1 !important; /* Slate 300 */
        border-radius: 8px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
    }
    
    /* CRITICAL FIX: Ensure text inside Selectbox is visible */
    .stSelectbox div[data-baseweb="select"] div {
        color: #0f172a !important;
    }
    .stSelectbox div[data-baseweb="select"] span {
        color: #0f172a !important;
    }
    
    /* Hover/Focus states for inputs */
    .stTextInput input:focus, .stTextArea textarea:focus, .stSelectbox div[data-baseweb="select"]:focus-within {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px var(--accent-glow) !important;
    }

    /* Placeholders */
    ::placeholder {
        color: #94a3b8 !important;
        opacity: 1 !important;
    }
    
    /* 6. BUTTONS */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        border: 1px solid var(--border-light);
        color: var(--primary);
        background: white;
        padding: 0.6rem 1.25rem;
    }
    /* Primary Action */
    .stButton>button[kind="primary"] {
        background: var(--accent);
        color: white;
        border: 1px solid var(--accent);
        box-shadow: 0 4px 6px rgba(99, 102, 241, 0.25);
    }
    .stButton>button[kind="primary"]:hover {
        background: #4f46e5; /* Indigo 600 */
        box-shadow: 0 6px 10px rgba(99, 102, 241, 0.3);
    }

    /* 7. UTILITIES & BADGES */
    .section-header {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--primary);
        margin: 3rem 0 1.5rem 0;
        border-bottom: 2px solid #e2e8f0;
        padding-bottom: 0.5rem;
    }
    
    .brand-archetype {
        background: #f0fdf4; 
        color: #15803d;
        border: 1px solid #bbf7d0;
        padding: 0.3rem 0.8rem;
        border-radius: 100px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    
    .health-score {
        font-size: 4rem;
        font-weight: 800;
        letter-spacing: -0.05em;
        background: linear-gradient(135deg, #0f172a 0%, #475569 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin: 0;
    }
    
    /* Hide Streamlit Boilerplate */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    </style>
    """, unsafe_allow_html=True)
