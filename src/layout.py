"""
Layout builders for the Anki Learning Dashboard.
Single-page dark Grafana-style grid layout.
"""

from dash import dcc, html

from .constants import COLORS
from .data_loader import get_deck_list


CHART_HEIGHT = '280px'
DARK_BG = {'backgroundColor': '#111217'}

def create_stat_item(value, label, color=COLORS['text_primary'], secondary=False):
    """Create a compact stat indicator for the stat strip."""
    cls = 'stat-item stat-item--secondary' if secondary else 'stat-item'
    return html.Div([
        html.Div(value, className='stat-item__value', style={'color': color}),
        html.Div(label, className='stat-item__label'),
    ], className=cls)


def create_main_layout():
    """Assemble the full single-page grid layout."""

    return html.Div([
        # Hidden stores
        dcc.Location(id='url', refresh=True),
        dcc.Store(id='backup-refresh-token', data=0, storage_type='memory'),
        dcc.Store(id='xaxis-mode', data='dates', storage_type='local'),
        dcc.Store(id='ui-store', storage_type='local', data={
            'session_time_range': 'all',
            'xaxis_mode': 'dates',
            'deck_filter': 'all',
        }),

        html.Div([
            # TODO: Improve top bar styling and layout

            # ── Top Bar ──
            html.Div([
                html.Div('Anki Dashboard', className='top-bar__title'),

                html.Div([
                    # Time range dropdown
                    html.Div([
                        html.Span('Range', className='top-bar__label'),
                        dcc.Dropdown(
                            id='session-time-range',
                            options=[
                                {'label': '7d', 'value': '7'},
                                {'label': '30d', 'value': '30'},
                                {'label': '90d', 'value': '90'},
                                {'label': '180d', 'value': '180'},
                                {'label': '365d', 'value': '365'},
                                {'label': 'All', 'value': 'all'},
                            ],
                            value='all',
                            clearable=False,
                            searchable=False,
                            style={'width': '100px'},
                        ),
                    ], className='top-bar__group'),

                    # X-axis toggle
                    html.Div([
                        html.Button(
                            'Dates',
                            id='xaxis-dates-btn',
                            n_clicks=0,
                            style={
                                'padding': '4px 12px',
                                'border': f'1px solid {COLORS["border"]}',
                                'borderRadius': '3px 0 0 3px',
                                'backgroundColor': COLORS['primary'],
                                'color': '#fff',
                                'cursor': 'pointer',
                                'fontSize': '12px',
                                'fontWeight': '500',
                                'lineHeight': '1.4',
                            },
                        ),
                        html.Button(
                            'Sessions',
                            id='xaxis-sessions-btn',
                            n_clicks=0,
                            style={
                                'padding': '4px 12px',
                                'border': f'1px solid {COLORS["border"]}',
                                'borderLeft': 'none',
                                'borderRadius': '0 3px 3px 0',
                                'backgroundColor': COLORS['bg_secondary'],
                                'color': COLORS['text_secondary'],
                                'cursor': 'pointer',
                                'fontSize': '12px',
                                'fontWeight': '500',
                                'lineHeight': '1.4',
                            },
                        ),
                    ], style={'display': 'flex'}),

                    html.Div(className='top-bar__separator'),

                    # Deck filter
                    html.Div([
                        html.Span('Deck', className='top-bar__label'),
                        dcc.Dropdown(
                            id='deck-filter',
                            options=[{'label': 'All Decks', 'value': 'all'}] + [
                                {'label': d['name'], 'value': str(d['id'])}
                                for d in get_deck_list()
                            ],
                            value='all',
                            clearable=False,
                            style={'width': '200px'},
                        ),
                    ], className='top-bar__group'),

                    # Actions
                    html.Div([
                        html.Button(
                            'Sync',
                            id='sync-from-anki-button',
                            title='Sync from local Anki',
                            style={
                                'padding': '4px 12px',
                                'backgroundColor': COLORS['success'],
                                'color': '#fff',
                                'border': 'none',
                                'borderRadius': '3px',
                                'cursor': 'pointer',
                                'fontSize': '12px',
                                'fontWeight': '500',
                            },
                        ),
                        dcc.Upload(
                            id='upload-backup-button',
                            accept='.apkg',
                            children=html.Button(
                                'Upload',
                                title='Upload .apkg file',
                                style={
                                    'padding': '4px 12px',
                                    'backgroundColor': COLORS['primary'],
                                    'color': '#fff',
                                    'border': 'none',
                                    'borderRadius': '3px',
                                    'cursor': 'pointer',
                                    'fontSize': '12px',
                                    'fontWeight': '500',
                                },
                            ),
                        ),
                    ], className='top-bar__actions'),
                ], className='top-bar__controls'),

                # Toast status message
                html.Div(id='upload-status-message', style={'display': 'none'}),
                dcc.Interval(
                    id='upload-message-interval',
                    interval=2000, n_intervals=0, max_intervals=1, disabled=True,
                ),
            ], className='top-bar'),

            # ── Stat Strip ──

            html.Div([
                # Primary stats (populated by callback)
                html.Div(id='stat-upcoming'),
                html.Div(id='stat-streak'),
                html.Div(id='stat-recall-rate'),
                html.Div(id='stat-overdue'),

                html.Div(className='stat-strip__separator'),

                # Secondary stats
                html.Div(id='stat-total-reviews'),
                html.Div(id='stat-total-hours'),
                html.Div(id='stat-days-active'),
                html.Div(id='stat-cards-learned'),
                html.Div(id='stat-avg-retrievability'),
            ], className='stat-strip'),

            # ── Chart Grid ──
            html.Div([
                # Row 1
                html.Div(
                    dcc.Graph(id='chart-daily-reviews', config={'displayModeBar': False},
                              style={'height': CHART_HEIGHT, **DARK_BG}),
                    className='chart-panel chart-panel--wide',
                ),
                html.Div(
                    dcc.Graph(id='chart-hourly', config={'displayModeBar': False},
                              style={'height': CHART_HEIGHT, **DARK_BG}),
                    className='chart-panel',
                ),

                # Row 2
                html.Div(
                    dcc.Graph(id='chart-recall-rate', config={'displayModeBar': False},
                              style={'height': CHART_HEIGHT, **DARK_BG}),
                    className='chart-panel chart-panel--wide',
                ),
                html.Div(
                    dcc.Graph(id='chart-review-speed', config={'displayModeBar': False},
                              style={'height': CHART_HEIGHT, **DARK_BG}),
                    className='chart-panel',
                ),

                # Row 3 — hero: expected known cards over time
                html.Div(
                    dcc.Graph(id='chart-known-words', config={'displayModeBar': False},
                              style={'height': CHART_HEIGHT, **DARK_BG}),
                    className='chart-panel chart-panel--full',
                ),

                # Row 4
                html.Div(
                    dcc.Graph(id='chart-future-load', config={'displayModeBar': False},
                              style={'height': CHART_HEIGHT, **DARK_BG}),
                    className='chart-panel chart-panel--wide',
                ),
                html.Div(
                    dcc.Graph(id='chart-calibration', config={'displayModeBar': False},
                              style={'height': CHART_HEIGHT, **DARK_BG}),
                    className='chart-panel',
                ),

                # Row 5
                html.Div(
                    dcc.Graph(id='chart-retrievability-dist', config={'displayModeBar': False},
                              style={'height': CHART_HEIGHT, **DARK_BG}),
                    className='chart-panel',
                ),
                html.Div(
                    dcc.Graph(id='chart-stability-dist', config={'displayModeBar': False},
                              style={'height': CHART_HEIGHT, **DARK_BG}),
                    className='chart-panel',
                ),
                html.Div(
                    dcc.Graph(id='chart-difficulty-dist', config={'displayModeBar': False},
                              style={'height': CHART_HEIGHT, **DARK_BG}),
                    className='chart-panel',
                ),

                # Row 6 — planning
                html.Div(
                    dcc.Graph(id='chart-completion', config={'displayModeBar': False},
                              style={'height': CHART_HEIGHT, **DARK_BG}),
                    className='chart-panel chart-panel--wide',
                ),
                html.Div(
                    dcc.Graph(id='chart-retention-workload', config={'displayModeBar': False},
                              style={'height': CHART_HEIGHT, **DARK_BG}),
                    className='chart-panel',
                ),

                # Row 7 — learning dynamics
                html.Div(
                    dcc.Graph(id='chart-cohorts', config={'displayModeBar': False},
                              style={'height': CHART_HEIGHT, **DARK_BG}),
                    className='chart-panel chart-panel--wide',
                ),
                html.Div(
                    dcc.Graph(id='chart-fatigue', config={'displayModeBar': False},
                              style={'height': CHART_HEIGHT, **DARK_BG}),
                    className='chart-panel',
                ),
            ], className='chart-grid'),

        ], className='dashboard'),
    ])
