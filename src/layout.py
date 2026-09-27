"""
Layout builders for AnkiDash.
Single-page dark Grafana-style grid layout.
"""

from dash import dcc, html

from .constants import COLORS
from .data_loader import get_deck_list
from .charts_card import create_sim_memorized_chart, create_sim_reviews_chart


CHART_HEIGHT = '280px'
DARK_BG = {'backgroundColor': '#111217'}

# Chart grid: 3 equal columns, fixed-height rows. Each entry is (chart id,
# default width in columns). Order and widths are adjusted in the browser by
# src/assets/grid.js and kept in localStorage.
DEFAULT_GRID = [
    ('chart-future-load', 2), ('chart-stability-dist', 1),
    ('chart-daily-reviews', 2), ('chart-retrievability-dist', 1),
    ('chart-recall-rate', 2), ('chart-difficulty-dist', 1),
    ('chart-review-speed', 2), ('chart-hourly', 1),
    ('chart-fatigue', 1), ('chart-load-intro', 1), ('chart-lapse-load', 1),
    ('chart-known-words', 2), ('chart-retention-workload', 1),
    ('chart-load-trend', 2), ('chart-calibration', 1),
]


def segmented_styles(left_active):
    """Styles for a two-button segmented toggle (left, right)."""
    base = {'padding': '4px 12px', 'cursor': 'pointer', 'fontSize': '12px',
            'fontWeight': '500', 'lineHeight': '1.4'}
    active = {**base, 'border': f'1px solid {COLORS["primary"]}',
              'backgroundColor': COLORS['primary'], 'color': '#fff'}
    inactive = {**base, 'border': f'1px solid {COLORS["border"]}',
                'backgroundColor': COLORS['bg_secondary'], 'color': COLORS['text_secondary']}
    left, right = (active, inactive) if left_active else (inactive, active)
    return ({**left, 'borderRadius': '3px 0 0 3px'},
            {**right, 'borderRadius': '0 3px 3px 0', 'borderLeft': 'none'})


def _grid_panel(chart_id, width):
    """One chart in the grid, with a move grip and a right-edge resize handle."""
    return html.Div([
        html.Div('⠿', className='grid-panel__grip', title='Drag to move'),
        dcc.Graph(id=chart_id, config={'displayModeBar': False}, responsive=True,
                  style={'height': '100%', **DARK_BG}),
        html.Div(className='grid-panel__resize', title='Drag to resize'),
    ], className='chart-panel grid-panel', **{'data-id': chart_id, 'data-w': str(width)})


def _sim_input(label, input_id, value, suffix=None, **input_kwargs):
    """A labelled numeric input for the forecast simulator control row."""
    return html.Div([
        html.Label(label, className='sim-input__label'),
        html.Div([
            dcc.Input(id=input_id, type='number', value=value,
                      className='sim-input__field', **input_kwargs),
            html.Span(suffix, className='sim-input__suffix') if suffix else None,
        ], className='sim-input__wrap'),
    ], className='sim-input')


def create_simulator_section():
    """Forecast simulator: controls + memorized/reviews projection charts."""
    return html.Div([
        html.Div([
            html.Div([
                html.H2('Forecast Simulator', className='section__title'),
                html.P('Anki’s FSRS simulator, seeded with your current cards and '
                       'this deck’s preset.', className='section__desc'),
            ]),
            html.Div([
                _sim_input('Days', 'sim-days', 365, min=30, max=1825, step=1),
                _sim_input('Desired retention', 'sim-retention', 90, suffix='%',
                           min=70, max=97, step=1),
                _sim_input('New cards/day', 'sim-new', 0, min=0, max=500, step=1),
                _sim_input('Max reviews/day', 'sim-maxrev', 200, min=10, max=9999, step=10),
                html.Button('Simulate', id='sim-run', n_clicks=0, className='sim-run-btn'),
            ], className='sim-controls'),
        ], className='sim-header'),
        dcc.Loading(
            type='default', color=COLORS['primary'],
            children=html.Div([
                html.Div(
                    dcc.Graph(id='chart-sim-memorized', config={'displayModeBar': False},
                              figure=create_sim_memorized_chart(None),
                              style={'height': CHART_HEIGHT, **DARK_BG}),
                    className='chart-panel', style={'flex': 2, 'minWidth': 0},
                ),
                html.Div(
                    dcc.Graph(id='chart-sim-reviews', config={'displayModeBar': False},
                              figure=create_sim_reviews_chart(None),
                              style={'height': CHART_HEIGHT, **DARK_BG}),
                    className='chart-panel', style={'flex': 1, 'minWidth': 0},
                ),
            ], className='sim-charts'),
        ),
    ], className='sim-section')


def create_stat_item(value, label, color=COLORS['text_primary'], secondary=False, title=None):
    """Create a compact stat indicator for the stat strip."""
    cls = 'stat-item stat-item--secondary' if secondary else 'stat-item'
    return html.Div([
        html.Div(value, className='stat-item__value', style={'color': color}),
        html.Div(label, className='stat-item__label'),
    ], className=cls, title=title)


def create_main_layout():
    """Assemble the full single-page grid layout."""

    return html.Div([
        # Hidden stores
        dcc.Location(id='url', refresh=True),
        dcc.Store(id='backup-refresh-token', data=0, storage_type='memory'),
        dcc.Store(id='xaxis-mode', data='dates', storage_type='local'),
        dcc.Store(id='load-basis', data='interval', storage_type='local'),
        dcc.Store(id='ui-store', storage_type='local', data={
            'session_time_range': 'all',
            'xaxis_mode': 'dates',
            'deck_filter': 'all',
        }),

        html.Div([
            # ── Top Bar ──
            html.Div([
                html.Div('AnkiDash', className='top-bar__title'),

                html.Div([
                    # Time range toggle
                    html.Div([
                        html.Span('Range', className='top-bar__label'),
                        dcc.RadioItems(
                            id='session-time-range',
                            options=[{'label': lbl, 'value': v} for lbl, v in [
                                ('7d', '7'), ('30d', '30'), ('90d', '90'),
                                ('180d', '180'), ('1y', '365'), ('All', 'all'),
                            ]],
                            value='all',
                            className='segmented',
                        ),
                    ], className='top-bar__group'),

                    # X-axis toggle
                    html.Div([
                        html.Button('Dates', id='xaxis-dates-btn', n_clicks=0, style=segmented_styles(True)[0]),
                        html.Button('Sessions', id='xaxis-sessions-btn', n_clicks=0, style=segmented_styles(True)[1]),
                    ], style={'display': 'flex'}),

                    html.Div(className='top-bar__separator'),

                    # Load basis toggle (interval vs stability)
                    html.Div([
                        html.Span('Load', className='top-bar__label'),
                        html.Div([
                            html.Button('Interval', id='load-interval-btn', n_clicks=0, style=segmented_styles(True)[0]),
                            html.Button('Stability', id='load-stability-btn', n_clicks=0, style=segmented_styles(True)[1]),
                        ], style={'display': 'flex'}),
                    ], className='top-bar__group'),

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
                        # Last successful AnkiWeb sync (populated by callback)
                        html.Span(id='last-sync-indicator', className='top-bar__label'),
                        html.Button(
                            'Sync',
                            id='sync-from-anki-button',
                            title='Sync from AnkiWeb',
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

                # AnkiWeb login (shown by the Sync button when no sync key is stored)
                html.Div([
                    html.Div('Log in to AnkiWeb', className='login-panel__title'),
                    dcc.Input(id='ankiweb-email', type='email', placeholder='Email',
                              className='sim-input__field login-panel__field'),
                    dcc.Input(id='ankiweb-password', type='password', placeholder='Password',
                              className='sim-input__field login-panel__field'),
                    html.Button('Log in and sync', id='ankiweb-login-button', className='sim-run-btn'),
                    html.Div('Only a sync key is stored, never your password.',
                             className='login-panel__note'),
                ], id='ankiweb-login', className='login-panel', style={'display': 'none'}),

                # Toast status message
                html.Div(id='upload-status-message', className='toast-msg', style={'display': 'none'}),
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
                html.Div(id='stat-true-retention'),
                html.Div(id='stat-overdue'),

                html.Div(className='stat-strip__separator'),

                # Secondary stats
                html.Div(id='stat-total-reviews'),
                html.Div(id='stat-total-hours'),
                html.Div(id='stat-days-active'),
                html.Div(id='stat-cards-learned'),
                html.Div(id='stat-avg-retrievability'),
                html.Div(id='stat-daily-load'),
            ], className='stat-strip'),

            # ── Chart Grid (movable / resizable, see assets/grid.js) ──
            html.Div([_grid_panel(cid, w) for cid, w in DEFAULT_GRID],
                     id='chart-grid', className='chart-grid'),

            # ── Forecast Simulator ──
            create_simulator_section(),

        ], className='dashboard'),
    ])
