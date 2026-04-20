# Design System Configuration

# Color Palette
PRIMARY_COLOR = "#2E86AB"
SECONDARY_COLOR = "#A63737"
SUCCESS_COLOR = "#4CAF50"
WARNING_COLOR = "#FF9800"
ERROR_COLOR = "#F44336"
BACKGROUND_COLOR = "#F5F5F5"
CARD_BACKGROUND = "#FFFFFF"
TEXT_COLOR = "#333333"

# Typography
FONT_FAMILY = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
HEADING_FONT_SIZE = "24px"
SUBHEADING_FONT_SIZE = "18px"
BODY_FONT_SIZE = "14px"

# Spacing
PADDING_SMALL = "8px"
PADDING_MEDIUM = "16px"
PADDING_LARGE = "24px"
MARGIN_SMALL = "8px"
MARGIN_MEDIUM = "16px"
MARGIN_LARGE = "24px"

# Border Radius
BORDER_RADIUS_SMALL = "4px"
BORDER_RADIUS_MEDIUM = "8px"
BORDER_RADIUS_LARGE = "12px"

# Shadows
SHADOW_SMALL = "0 2px 4px rgba(0,0,0,0.1)"
SHADOW_MEDIUM = "0 4px 8px rgba(0,0,0,0.15)"
SHADOW_LARGE = "0 8px 16px rgba(0,0,0,0.2)"

def get_css():
    """Return the complete CSS stylesheet for the application."""
    return f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: {FONT_FAMILY};
            background-color: {BACKGROUND_COLOR};
            color: {TEXT_COLOR};
            font-size: {BODY_FONT_SIZE};
        }}
        
        .main-header {{
            background-color: {PRIMARY_COLOR};
            color: white;
            padding: {PADDING_LARGE};
            border-radius: {BORDER_RADIUS_LARGE};
            margin-bottom: {MARGIN_LARGE};
            box-shadow: {SHADOW_MEDIUM};
        }}
        
        .card {{
            background-color: {CARD_BACKGROUND};
            border-radius: {BORDER_RADIUS_MEDIUM};
            padding: {PADDING_MEDIUM};
            margin-bottom: {MARGIN_MEDIUM};
            box-shadow: {SHADOW_SMALL};
        }}
        
        .stButton > button {{
            background-color: {PRIMARY_COLOR};
            color: white;
            border: none;
            padding: {PADDING_SMALL} {PADDING_MEDIUM};
            border-radius: {BORDER_RADIUS_SMALL};
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }}
        
        .stButton > button:hover {{
            opacity: 0.9;
            transform: translateY(-2px);
            box-shadow: {SHADOW_MEDIUM};
        }}
        
        .success-box {{
            background-color: #E8F5E9;
            border-left: 4px solid {SUCCESS_COLOR};
            padding: {PADDING_MEDIUM};
            margin: {MARGIN_MEDIUM} 0;
            border-radius: {BORDER_RADIUS_SMALL};
        }}
        
        .error-box {{
            background-color: #FFEBEE;
            border-left: 4px solid {ERROR_COLOR};
            padding: {PADDING_MEDIUM};
            margin: {MARGIN_MEDIUM} 0;
            border-radius: {BORDER_RADIUS_SMALL};
        }}
        
        .warning-box {{
            background-color: #FFF3E0;
            border-left: 4px solid {WARNING_COLOR};
            padding: {PADDING_MEDIUM};
            margin: {MARGIN_MEDIUM} 0;
            border-radius: {BORDER_RADIUS_SMALL};
        }}
        
        h1, h2, h3 {{
            font-weight: 600;
            margin-bottom: {MARGIN_MEDIUM};
        }}
        
        h1 {{
            font-size: {HEADING_FONT_SIZE};
        }}
        
        h2 {{
            font-size: {SUBHEADING_FONT_SIZE};
        }}
        
        .dataframe {{
            border-radius: {BORDER_RADIUS_MEDIUM};
            overflow: hidden;
            box-shadow: {SHADOW_SMALL};
        }}
        
        .sidebar-content {{
            background-color: {CARD_BACKGROUND};
            padding: {PADDING_MEDIUM};
            border-radius: {BORDER_RADIUS_MEDIUM};
            box-shadow: {SHADOW_SMALL};
        }}
    </style>
    """

def inject_css():
    """Inject CSS styles into the Streamlit app."""
    st.markdown(get_css(), unsafe_allow_html=True)
