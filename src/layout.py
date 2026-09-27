"""
Layout builders for AnkiDash.
Single-page dark Grafana-style grid layout.
"""

import dash_dynamic_grid_layout as dgl
from dash import dcc, html

from .constants import COLORS
from .data_loader import get_deck_list
from .charts_card import create_sim_memorized_chart, create_sim_reviews_chart


CHART_HEIGHT = '280px'
DARK_BG = {'backgroundColor': '#111217'}

# Grid discretization: 3 columns of equal thirds, so a row can only be
# 1-1-1, 2-1, 1-2, or 3. Height is fixed (minH = maxH = 1 row).
GRID_COLS = 3
GRID_ROW_HEIGHT = 300
_GRID_CONSTRAINTS = {'minW': 1, 'maxW': GRID_COLS, 'minH': 1, 'maxH': 1}

# NOTE: layout ids must match the DraggableWrapper ids ('w-' + chart id) —
# the component matches itemLayout entries against child keys, which Dash
# derives from the wrapper's id. The dcc.Graph inside keeps the bare chart id.
DEFAULT_GRID_LAYOUT = [
    {'i': 'w-chart-future-load',         'x': 0, 'y': 0, 'w': 2, 'h': 1, **_GRID_CONSTRAINTS},
    {'i': 'w-chart-stability-dist',      'x': 2, 'y': 0, 'w': 1, 'h': 1, **_GRID_CONSTRAINTS},
    {'i': 'w-chart-daily-reviews',       'x': 0, 'y': 1, 'w': 2, 'h': 1, **_GRID_CONSTRAINTS},
    {'i': 'w-chart-retrievability-dist', 'x': 2, 'y': 1, 'w': 1, 'h': 1, **_GRID_CONSTRAINTS},
    {'i': 'w-chart-recall-rate',         'x': 0, 'y': 2, 'w': 2, 'h': 1, **_GRID_CONSTRAINTS},
    {'i': 'w-chart-difficulty-dist',     'x': 2, 'y': 2, 'w': 1, 'h': 1, **_GRID_CONSTRAINTS},
    {'i': 'w-chart-review-speed',        'x': 0, 'y': 3, 'w': 2, 'h': 1, **_GRID_CONSTRAINTS},
    {'i': 'w-chart-hourly',              'x': 2, 'y': 3, 'w': 1, 'h': 1, **_GRID_CONSTRAINTS},
    {'i': 'w-chart-fatigue',             'x': 0, 'y': 4, 'w': 1, 'h': 1, **_GRID_CONSTRAINTS},
    {'i': 'w-chart-load-intro',          'x': 1, 'y': 4, 'w': 1, 'h': 1, **_GRID_CONSTRAINTS},
    {'i': 'w-chart-lapse-load',          'x': 2, 'y': 4, 'w': 1, 'h': 1, **_GRID_CONSTRAINTS},
    {'i': 'w-chart-known-words',         'x': 0, 'y': 5, 'w': 2, 'h': 1, **_GRID_CONSTRAINTS},
    {'i': 'w-chart-retention-workload',  'x': 2, 'y': 5, 'w': 1, 'h': 1, **_GRID_CONSTRAINTS},
    {'i': 'w-chart-load-trend',          'x': 0, 'y': 6, 'w': 2, 'h': 1, **_GRID_CONSTRAINTS},
    {'i': 'w-chart-calibration',         'x': 2, 'y': 6, 'w': 1, 'h': 1, **_GRID_CONSTRAINTS},
]


def sanitize_grid_item(stored: dict, default: dict) -> dict:
    """Clamp a stored grid item onto the discrete 3-column grid."""
    try:
        w = min(max(int(stored.get('w', default['w'])), 1), GRID_COLS)
        x = min(max(int(stored.get('x', default['x'])), 0), GRID_COLS - w)
        y = max(int(stored.get('y', default['y'])), 0)
    except (TypeError, ValueError):
        return dict(default)
    return {'i': default['i'], 'x': x, 'y': y, 'w': w, 'h': 1, **_GRID_CONSTRAINTS}


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


def _grid_chart(wrapper_id):
    """A draggable/resizable grid item wrapping one chart."""
    chart_id = wrapper_id.removeprefix('w-')
    return dgl.DraggableWrapper(
        id=wrapper_id,
        children=[
            html.Div(
                dcc.Graph(
                    id=chart_id,
                    config={'displayModeBar': False},
                    responsive=True,
                    style={'height': '100%', **DARK_BG},
                ),
                className='chart-panel',
                style={'height': '100%'},
            ),
        ],
        handleText='⠿',
        handleBackground='#181b23',
        handleColor='#5a5e72',
    )

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
        dcc.Store(id='grid-layout-store', storage_type='local'),
        dcc.Store(id='grid-resize-sync', storage_type='memory'),
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

            # ── Chart Grid (draggable / resizable) ──
            dgl.DashGridLayout(
                id='chart-grid',
                items=[_grid_chart(item['i']) for item in DEFAULT_GRID_LAYOUT],
                itemLayout=DEFAULT_GRID_LAYOUT,
                rowHeight=GRID_ROW_HEIGHT,
                cols={'lg': GRID_COLS, 'md': GRID_COLS, 'sm': 1, 'xs': 1, 'xxs': 1},
                compactType='vertical',
                showRemoveButton=False,
                showResizeHandles=True,
                # Override the component default (padding:10px, maxHeight:95%),
                # which ignores the drag-handle height and overflows the graph.
                draggableChildStyle={'height': '100%', 'padding': 0, 'overflow': 'hidden'},
                margin=[8, 8],
                style={'minHeight': '400px'},
            ),

            # ── Forecast Simulator ──
            create_simulator_section(),

        ], className='dashboard'),
    ])
