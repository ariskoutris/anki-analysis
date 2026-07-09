"""
Shared constants for the Anki Learning Dashboard.
"""

# Dark color palette
COLORS = {
    'bg_canvas': '#0b0c0e',
    'bg_primary': '#111217',
    'bg_secondary': '#181b23',
    'border': '#2a2d3a',
    'text_primary': '#e0e0e0',
    'text_secondary': '#8b8fa3',
    'text_muted': '#5a5e72',
    'primary': '#5b8dff',
    'secondary': '#b07aff',
    'success': '#2dd4a8',
    'warning': '#f0b429',
    'danger': '#f25f5c',
    'info': '#29b6f6',
    'critical': '#f25f5c',
    'at_risk': '#f0973a',
    'moderate': '#f0d264',
    'good': '#2dd4a8',
    'excellent': '#29b6f6',
}

# Memory state colors
MEMORY_COLORS = {
    'Critical (<50%)': COLORS['critical'],
    'At Risk (50-70%)': COLORS['at_risk'],
    'Moderate (70-85%)': COLORS['moderate'],
    'Good (85-95%)': COLORS['good'],
    'Excellent (95%+)': COLORS['excellent'],
}

# Shared dark chart layout
DARK_CHART_LAYOUT = dict(
    plot_bgcolor='#111217',
    paper_bgcolor='#111217',
    font=dict(color='#8b8fa3', size=11),
    margin=dict(l=40, r=32, t=36, b=32),
    legend=dict(
        orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1,
        font=dict(color='#8b8fa3', size=10),
    ),
)

DARK_CHART_AXIS = dict(
    showgrid=True, gridwidth=1, gridcolor='#2a2d3a',
    zeroline=False,
    tickfont=dict(color='#5a5e72', size=10),
    title_font=dict(color='#8b8fa3', size=11),
)

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
            *, *::before, *::after { box-sizing: border-box; }

            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                background: #0b0c0e;
                color: #e0e0e0;
                min-height: 100vh;
                margin: 0;
            }

            /* Dashboard container */
            .dashboard {
                max-width: 1800px;
                margin: 0 auto;
                padding: 8px 12px;
            }

            /* Top bar */
            .top-bar {
                display: flex;
                align-items: center;
                padding: 6px 12px;
                background: #181b23;
                border: 1px solid #2a2d3a;
                border-radius: 4px;
                margin-bottom: 8px;
                flex-wrap: wrap;
            }
            .top-bar__title {
                font-size: 15px;
                font-weight: 600;
                color: #e0e0e0;
                padding: 0 16px 0 4px;
                white-space: nowrap;
            }
            .top-bar__controls {
                display: flex;
                align-items: center;
                gap: 14px;
                padding: 6px 14px;
                flex-wrap: wrap;
                margin-left: auto;
            }
            .top-bar__separator {
                width: 1px;
                height: 24px;
                background: #2a2d3a;
            }
            .top-bar__group {
                display: flex;
                align-items: center;
                gap: 8px;
            }
            .top-bar__label {
                font-size: 11px;
                color: #5a5e72;
                white-space: nowrap;
            }
            .top-bar__actions {
                display: flex;
                align-items: center;
                gap: 6px;
            }

            /* Stat strip */
            .stat-strip {
                display: flex;
                align-items: center;
                gap: 6px;
                padding: 6px 12px;
                background: #111217;
                border: 1px solid #2a2d3a;
                border-radius: 4px;
                margin-bottom: 8px;
                flex-wrap: wrap;
            }
            .stat-strip__separator {
                width: 1px;
                height: 28px;
                background: #2a2d3a;
                margin: 0 4px;
            }
            .stat-item {
                display: flex;
                flex-direction: column;
                align-items: center;
                padding: 2px 10px;
                min-width: 80px;
            }
            .stat-item__value {
                font-size: 18px;
                font-weight: 700;
                line-height: 1.2;
            }
            .stat-item__label {
                font-size: 10px;
                color: #5a5e72;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                line-height: 1.3;
            }
            .stat-item--secondary .stat-item__value {
                font-size: 14px;
                font-weight: 600;
            }
            .stat-item--secondary .stat-item__label {
                font-size: 9px;
            }

            /* Chart grid */
            .chart-grid {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 8px;
            }
            .chart-panel {
                background: #111217;
                border: 1px solid #2a2d3a;
                border-radius: 4px;
                padding: 4px;
                min-height: 0;
            }
            .chart-panel--wide {
                grid-column: span 2;
            }
            .chart-panel--full {
                grid-column: 1 / -1;
            }

            /* Toast message */
            .toast-msg {
                position: fixed;
                top: 12px;
                right: 12px;
                z-index: 1000;
                padding: 8px 14px;
                border-radius: 4px;
                font-size: 12px;
                max-width: 360px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.5);
            }

            /* ---- Dash component dark overrides ---- */

            /* Dropdown button */
            button.dash-dropdown {
                background-color: #181b23 !important;
                border: 1px solid #2a2d3a !important;
                color: #e0e0e0 !important;
                border-radius: 3px !important;
            }
            button.dash-dropdown:hover {
                border-color: #5b8dff !important;
            }
            .dash-dropdown-trigger-icon {
                color: #5a5e72 !important;
            }
            .dash-dropdown-value,
            .dash-dropdown-value-item {
                color: #e0e0e0 !important;
            }

            /* Dropdown menu (popover content) */
            .dash-dropdown-content {
                background-color: #181b23 !important;
                border: 1px solid #2a2d3a !important;
                box-shadow: 0 4px 12px rgba(0,0,0,0.5) !important;
            }
            .dash-dropdown-search-container {
                background-color: #111217 !important;
                border-color: #2a2d3a !important;
            }
            .dash-dropdown-search {
                background-color: #111217 !important;
                border-color: #2a2d3a !important;
                color: #e0e0e0 !important;
            }
            .dash-dropdown-search::placeholder {
                color: #5a5e72 !important;
            }
            .dash-dropdown-search-icon {
                color: #5a5e72 !important;
            }
            .dash-dropdown-option {
                background-color: #181b23 !important;
                color: #e0e0e0 !important;
            }
            .dash-dropdown-option:hover,
            .dash-dropdown-option[data-highlighted] {
                background-color: #2a2d3a !important;
            }
            .dash-dropdown-option[data-state="checked"] {
                color: #5b8dff !important;
            }

            /* Responsive breakpoints */
            @media (max-width: 1200px) {
                .chart-grid {
                    grid-template-columns: repeat(2, 1fr);
                }
                .chart-panel--wide {
                    grid-column: span 2;
                }
            }
            @media (max-width: 768px) {
                .chart-grid {
                    grid-template-columns: 1fr;
                }
                .chart-panel--wide {
                    grid-column: span 1;
                }
                .top-bar {
                    flex-direction: column;
                    align-items: flex-start;
                }
                .top-bar__title {
                    margin-right: 0;
                }
                .stat-strip {
                    justify-content: center;
                }
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
