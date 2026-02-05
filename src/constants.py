"""
Shared constants for the Anki Learning Dashboard.
"""

# Color palette
COLORS = {
    'primary': '#667eea',
    'secondary': '#764ba2',
    'success': '#06d6a0',
    'warning': '#ffd166',
    'danger': '#ef476f',
    'info': '#118ab2',
    'dark': '#073b4c',
    'light': '#f8f9fa',
    'critical': '#C73E1D',
    'at_risk': '#F18F01',
    'moderate': '#FFD23F',
    'good': '#06A77D',
    'excellent': '#0FA3B1',
}

# Memory state colors
MEMORY_COLORS = {
    'Critical (<50%)': COLORS['critical'],
    'At Risk (50-70%)': COLORS['at_risk'],
    'Moderate (70-85%)': COLORS['moderate'],
    'Good (85-95%)': COLORS['good'],
    'Excellent (95%+)': COLORS['excellent'],
}

# Custom HTML/CSS template for the Dash app
INDEX_STRING = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                margin: 0;
            }
            .main-container {
                max-width: 1600px;
                margin: 0 auto;
                padding: 20px;
            }
            .header {
                text-align: center;
                color: white;
                padding: 20px 0;
            }
            .header h1 {
                margin: 0;
                font-size: 2.5rem;
                font-weight: 700;
            }
            .header p {
                margin: 10px 0 0;
                opacity: 0.9;
            }
            .stat-card {
                background: white;
                border-radius: 12px;
                padding: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                text-align: center;
            }
            .stat-value {
                font-size: 2rem;
                font-weight: 700;
                color: #667eea;
            }
            .stat-label {
                color: #666;
                font-size: 0.9rem;
                margin-top: 5px;
            }
            .card {
                background: white;
                border-radius: 12px;
                padding: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }
            .tabs-container {
                background: white;
                border-radius: 12px;
                padding: 0;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                overflow: hidden;
            }
            .custom-tabs {
                border-bottom: 2px solid #eee;
            }
            .custom-tab {
                padding: 15px 30px !important;
                font-weight: 600 !important;
            }
            .custom-tab--selected {
                border-top: none !important;
                border-left: none !important;
                border-right: none !important;
                border-bottom: 3px solid #667eea !important;
                color: #667eea !important;
            }
            .backup-controls {
                background: white;
                border-radius: 12px;
                padding: 16px 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.08);
                margin-bottom: 20px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 20px;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''
