"""
Layout builders for the Anki Learning Dashboard.
"""

from datetime import datetime
from dash import dcc, html

from .constants import COLORS

# Import anki_config via the sys.path already set up by app.py
from anki_config import get_active_date


def create_stat_card(value, label, color=COLORS['primary']):
    """Create a statistic card component"""
    return html.Div([
        html.Div(value, className='stat-value', style={'color': color}),
        html.Div(label, className='stat-label')
    ], className='stat-card')


def create_session_tab():
    """Create the session analytics tab content"""
    # Generate year options dynamically based on current date
    current_year = datetime.now().year
    # Include years from 2020 to last year (current year is covered by recent options)
    year_options = [
        {'label': f'Year {year}', 'value': f'year_{year}'}
        for year in range(current_year - 1, 2019, -1)
    ]

    return html.Div([
        # Controls
        html.Div([
            html.Div([
                html.Label("Time Range:", style={'fontWeight': '600', 'marginRight': '10px'}),
                dcc.Dropdown(
                    id='session-time-range',
                    options=[
                        {'label': 'Last 7 days', 'value': '7'},
                        {'label': 'Last 30 days', 'value': '30'},
                        {'label': 'Last 90 days', 'value': '90'},
                        {'label': 'Last 180 days', 'value': '180'},
                        {'label': 'All time', 'value': 'all'},
                    ] + year_options,
                    value='all',
                    clearable=False,
                    style={'width': '180px'}
                ),
            ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '40px'}),
            html.Div([
                html.Label("X-Axis:", style={'fontWeight': '600', 'marginRight': '10px'}),
                html.Div([
                    html.Button(
                        "Dates",
                        id='xaxis-dates-btn',
                        n_clicks=0,
                        style={
                            'padding': '6px 16px',
                            'border': '1px solid #ddd',
                            'borderRadius': '4px 0 0 4px',
                            'backgroundColor': COLORS['primary'],
                            'color': 'white',
                            'cursor': 'pointer',
                            'fontSize': '13px',
                            'fontWeight': '500'
                        }
                    ),
                    html.Button(
                        "Sessions",
                        id='xaxis-sessions-btn',
                        n_clicks=0,
                        style={
                            'padding': '6px 16px',
                            'border': '1px solid #ddd',
                            'borderLeft': 'none',
                            'borderRadius': '0 4px 4px 0',
                            'backgroundColor': 'white',
                            'color': '#333',
                            'cursor': 'pointer',
                            'fontSize': '13px',
                            'fontWeight': '500'
                        }
                    ),
                ], style={'display': 'flex'}),
            ], style={'display': 'flex', 'alignItems': 'center'}),
            # Hidden store for xaxis mode (persistent)
            dcc.Store(id='xaxis-mode', data='dates', storage_type='local'),
            # Store to persist ALL UI preferences across reloads and tab switches
            dcc.Store(id='ui-store', storage_type='local', data={
                'session_time_range': 'all',
                'xaxis_mode': 'dates',
                'retrievability_filter': [0, 100],
                'difficulty_filter': [0, 10],
                'data_backup': get_active_date()
            }),
        ], style={'padding': '20px', 'borderBottom': '1px solid #eee', 'display': 'flex', 'alignItems': 'center'}),

        # Session charts
        html.Div(id='session-charts', style={'padding': '20px'})
    ])


def create_cards_tab():
    """Create the card knowledge tab content"""
    return html.Div([
        # Controls
        html.Div([
            html.Div([
                html.Label("Filter by Retrievability:", style={'fontWeight': '600', 'marginRight': '10px'}),
                dcc.RangeSlider(
                    id='retrievability-filter',
                    min=0,
                    max=100,
                    step=5,
                    value=[0, 100],
                    marks={i: f'{i}%' for i in range(0, 101, 20)},
                    tooltip={"placement": "bottom", "always_visible": False}
                ),
            ], style={'flex': '2', 'marginRight': '30px'}),
            html.Div([
                html.Label("Difficulty:", style={'fontWeight': '600', 'marginRight': '10px'}),
                dcc.RangeSlider(
                    id='difficulty-filter',
                    min=0,
                    max=10,
                    step=0.5,
                    value=[0, 10],
                    marks={i: str(i) for i in range(0, 11, 2)},
                    tooltip={"placement": "bottom", "always_visible": False}
                ),
            ], style={'flex': '1'}),
        ], style={'padding': '20px', 'borderBottom': '1px solid #eee', 'display': 'flex', 'alignItems': 'center'}),

        # Card charts
        html.Div(id='card-charts', style={'padding': '20px'})
    ])


def create_main_layout(date_options, active_date):
    """Assemble the full page layout (header, overview, tabs)."""
    return html.Div([
        html.Div([
            # Header
            html.Div([
                dcc.Location(id='url', refresh=True),
                html.Div([
                    html.H1("📚 Anki Learning Dashboard"),
                    html.P("Interactive analysis of your learning journey and memory states")
                ], style={'textAlign': 'center'})
            ], className='header'),

            # Overview stats
            html.Div(id='overview-container'),

            # Data backup controls
            html.Div([
                html.Div([
                    html.Label("Data Backup:", style={'fontWeight': '600', 'marginRight': '10px', 'color': '#333'}),
                    dcc.Dropdown(
                        id='data-folder-dropdown',
                        options=date_options,
                        value=active_date,
                        clearable=False,
                        style={'width': '220px'}
                    ),
                    html.Div(id='active-date-banner', style={'color': '#666', 'marginLeft': '12px', 'fontWeight': '500', 'fontSize': '0.9rem'}),
                ], style={'display': 'flex', 'alignItems': 'center', 'flex': '1'}),

                # Upload button
                html.Div([
                    dcc.Upload(
                        id='upload-backup-button',
                        accept='.apkg',
                        children=html.Button(
                            '📤 Upload New Backup',
                            title='Upload an .apkg file to add a new backup',
                            style={
                                'padding': '8px 16px',
                                'backgroundColor': COLORS['primary'],
                                'color': 'white',
                                'border': 'none',
                                'borderRadius': '6px',
                                'cursor': 'pointer',
                                'fontSize': '14px',
                                'fontWeight': '500',
                                'transition': 'background-color 0.2s'
                            }
                        )
                    ),
                    # Status message
                    html.Div(
                        id='upload-status-message',
                        style={'display': 'none'}
                    ),
                    # Auto-dismiss interval (triggers 3 seconds after message shown)
                    dcc.Interval(
                        id='upload-message-interval',
                        interval=3000,  # 3 seconds
                        n_intervals=0,
                        max_intervals=1,  # Only fire once
                        disabled=True  # Start disabled
                    ),
                ], style={'display': 'flex', 'flexDirection': 'column', 'alignItems': 'flex-end'}),
            ], className='backup-controls'),

            # Tabs
            html.Div([
                dcc.Tabs([
                    dcc.Tab(
                        label='📊 Study Sessions',
                        children=create_session_tab(),
                        className='custom-tab',
                        selected_className='custom-tab--selected'
                    ),
                    dcc.Tab(
                        label='🧠 Card Knowledge',
                        children=create_cards_tab(),
                        className='custom-tab',
                        selected_className='custom-tab--selected'
                    ),
                ], className='custom-tabs')
            ], className='tabs-container'),

        ], className='main-container')
    ])
