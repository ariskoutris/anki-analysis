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


def _segmented(component_id, options, value=None):
    """A segmented toggle (radio items styled as joined buttons); remembers its value."""
    return dcc.RadioItems(
        id=component_id,
        options=[{'label': label, 'value': v} for label, v in options],
        value=value or options[0][1],
        persistence=True, persistence_type='local',
        className='segmented',
    )


# Charts the Range filter doesn't apply to, with the period they show instead
_RANGE_EXEMPT = {
    'chart-future-load': 'Next 365d',
    'chart-retrievability-dist': 'Now',
    'chart-stability-dist': 'Now',
    'chart-difficulty-dist': 'Now',
    'chart-lapse-load': 'Now',
    'chart-retention-workload': 'Now',
    'chart-calibration': 'All time',
    'chart-fatigue': 'All time',
}


def _grid_panel(chart_id, width):
    """One chart in the grid, with a move grip and a right-edge resize handle."""
    tag = _RANGE_EXEMPT.get(chart_id)
    return html.Div([
        html.Div([
            tag and html.Span(tag, className='grid-panel__tag', **{
                'data-hint': 'The Range filter doesn’t apply to this chart'}),
            html.Span('⠿', className='grid-panel__grip', title='Drag to move'),
        ], className='grid-panel__corner'),
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
        # Background sync and day rollover: poll for new data every minute
        dcc.Store(id='data-version', storage_type='memory'),
        dcc.Interval(id='data-poll', interval=60_000),

        html.Div([
            # ── Top Bar ──
            html.Div([
                html.Div('AnkiDash', className='top-bar__title'),

                html.Div([
                    # Time range toggle
                    html.Div([
                        html.Span('Range', className='top-bar__label'),
                        _segmented('session-time-range', [
                            ('7d', '7'), ('30d', '30'), ('90d', '90'),
                            ('180d', '180'), ('1y', '365'), ('All', 'all'),
                        ], value='all'),
                    ], className='top-bar__group'),

                    html.Div(className='top-bar__separator'),

                    # X-axis toggle
                    html.Div([
                        html.Span('X-axis', className='top-bar__label'),
                        _segmented('xaxis-mode', [('Dates', 'dates'), ('Sessions', 'sessions')]),
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
                            persistence=True, persistence_type='local',
                            clearable=False,
                            style={'width': '200px'},
                        ),
                    ], className='top-bar__group'),

                    html.Div(className='top-bar__separator'),

                    # Actions
                    html.Div([
                        # Last successful AnkiWeb sync (populated by callback)
                        html.Span(id='last-sync-indicator', className='top-bar__label'),
                        html.Button('Sync', id='sync-from-anki-button', title='Sync from AnkiWeb',
                                    className='top-bar__btn top-bar__btn--sync'),
                        dcc.Upload(
                            id='upload-backup-button',
                            accept='.apkg',
                            children=html.Button('Upload', title='Upload .apkg file',
                                                 className='top-bar__btn top-bar__btn--upload'),
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
                html.Div(id='upload-status-message', className='toast-msg', style={'display': 'none'},
                         title='Click to dismiss'),
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
            # Shown by grid.js once the layout differs from the default
            html.Button('Reset chart layout', id='grid-reset', className='grid-reset', hidden=True),

            # ── Forecast Simulator ──
            create_simulator_section(),

        ], className='dashboard'),
    ])
