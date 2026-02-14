"""
Layout builders for the Anki Learning Dashboard.
"""

from datetime import datetime
from dash import dcc, html

from .constants import COLORS


def create_stat_card(value, label, color=COLORS['primary']):
    """Create a statistic card component"""
    return html.Div([
        html.Div(value, className='stat-value', style={'color': color}),
        html.Div(label, className='stat-label')
    ], className='stat-card')


def create_section_container(title, description, content_id, summary_id=None):
    """
    Create a section container with header, optional summary stats area, and content area.

    Args:
        title: Section title
        description: Brief description of the section's purpose
        content_id: ID for the content div (where charts go)
        summary_id: Optional ID for summary stats div
    """
    children = [
        # Section header
        html.Div([
            html.H3(title, style={
                'margin': '0 0 4px 0',
                'fontSize': '1.1rem',
                'fontWeight': '600',
                'color': COLORS['dark']
            }),
            html.P(description, style={
                'margin': '0',
                'fontSize': '0.85rem',
                'color': '#666'
            })
        ], style={
            'marginBottom': '16px',
            'paddingBottom': '12px',
            'borderBottom': f"2px solid {COLORS['primary']}"
        }),
    ]

    # Optional summary stats container
    if summary_id:
        children.append(html.Div(id=summary_id, style={'marginBottom': '16px'}))

    # Content area for charts
    children.append(html.Div(id=content_id))

    return html.Div(children, style={
        'marginBottom': '32px',
        'padding': '20px',
        'backgroundColor': '#fafafa',
        'borderRadius': '8px'
    })


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
            }),
        ], style={'padding': '20px', 'borderBottom': '1px solid #eee', 'display': 'flex', 'alignItems': 'center'}),

        # Session sections with charts
        html.Div([
            # Section 1: Study Volume & Consistency
            create_section_container(
                "Study Volume & Consistency",
                "Track your daily study habits and identify patterns",
                content_id='session-volume-charts',
                summary_id='session-volume-summary'
            ),

            # Section 2: Learning Effectiveness
            create_section_container(
                "Learning Effectiveness",
                "Monitor your recall rate and review efficiency over time",
                content_id='session-effectiveness-charts',
                summary_id='session-effectiveness-summary'
            ),

            # Section 3: Workload Forecast
            create_section_container(
                "Workload Forecast",
                "Plan ahead with predictions of upcoming review load",
                content_id='session-workload-charts',
                summary_id='session-workload-summary'
            ),
        ], style={'padding': '20px'})
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

        # Card sections with charts
        html.Div([
            # Section 1: Current Knowledge State
            create_section_container(
                "Current Knowledge State",
                "Quick health check of your memory across all cards",
                content_id='card-knowledge-charts',
                summary_id='card-knowledge-summary'
            ),

            # Section 2: Collection Maturity
            create_section_container(
                "Collection Maturity",
                "Understand your deck composition and learning progress",
                content_id='card-maturity-charts',
                summary_id='card-maturity-summary'
            ),

            # Section 3: Problem Areas
            create_section_container(
                "Problem Areas",
                "Identify cards that need attention or reformulation",
                content_id='card-problem-charts',
                summary_id='card-problem-summary'
            ),
        ], style={'padding': '20px'})
    ])


def create_main_layout():
    """Assemble the full page layout (header, overview, tabs)."""
    return html.Div([
        html.Div([
            # Header
            html.Div([
                dcc.Location(id='url', refresh=True),
                dcc.Store(id='backup-refresh-token', data=0, storage_type='memory'),
                html.Div([
                    html.Div([
                        html.H1("📚 Anki Learning Dashboard"),
                        html.P("Interactive analysis of your learning journey and memory states")
                    ], style={'flex': '1', 'textAlign': 'center'}),
                    # Sync and Upload buttons
                    html.Div([
                        html.Div([
                            html.Button(
                                '🔄 Sync from Anki',
                                id='sync-from-anki-button',
                                title='Sync directly from your local Anki installation',
                                style={
                                    'padding': '8px 16px',
                                    'backgroundColor': COLORS['success'],
                                    'color': 'white',
                                    'border': 'none',
                                    'borderRadius': '6px',
                                    'cursor': 'pointer',
                                    'fontSize': '14px',
                                    'fontWeight': '500',
                                    'transition': 'background-color 0.2s',
                                    'marginRight': '10px'
                                }
                            ),
                            dcc.Upload(
                                id='upload-backup-button',
                                accept='.apkg',
                                children=html.Button(
                                    '📤 Upload Backup',
                                    title='Upload an .apkg file',
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
                        ], style={'display': 'flex', 'alignItems': 'center'}),
                        html.Div(
                            id='upload-status-message',
                            style={'display': 'none'}
                        ),
                        dcc.Interval(
                            id='upload-message-interval',
                            interval=3000,
                            n_intervals=0,
                            max_intervals=1,
                            disabled=True
                        ),
                    ], style={'display': 'flex', 'flexDirection': 'column', 'alignItems': 'flex-end', 'position': 'absolute', 'right': '20px', 'top': '50%', 'transform': 'translateY(-50%)'}),
                ], style={'position': 'relative', 'display': 'flex', 'alignItems': 'center'})
            ], className='header'),

            # Overview stats
            html.Div(id='overview-container'),

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
