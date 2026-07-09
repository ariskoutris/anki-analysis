"""
Layout builders for the Anki Learning Dashboard.
Single-page dark Grafana-style grid layout.
"""

import dash_dynamic_grid_layout as dgl
from dash import dcc, html

from .constants import COLORS
from .data_loader import get_deck_list


CHART_HEIGHT = '280px'
DARK_BG = {'backgroundColor': '#111217'}

# Default grid layout: 12 columns, h units of rowHeight=62px (h=4 ≈ 280px incl. margins)
DEFAULT_GRID_LAYOUT = [
    {'i': 'chart-daily-reviews',      'x': 0, 'y': 0,  'w': 8,  'h': 4},
    {'i': 'chart-hourly',             'x': 8, 'y': 0,  'w': 4,  'h': 4},
    {'i': 'chart-recall-rate',        'x': 0, 'y': 4,  'w': 8,  'h': 4},
    {'i': 'chart-review-speed',       'x': 8, 'y': 4,  'w': 4,  'h': 4},
    {'i': 'chart-known-words',        'x': 0, 'y': 8,  'w': 12, 'h': 4},
    {'i': 'chart-future-load',        'x': 0, 'y': 12, 'w': 8,  'h': 4},
    {'i': 'chart-calibration',        'x': 8, 'y': 12, 'w': 4,  'h': 4},
    {'i': 'chart-retrievability-dist', 'x': 0, 'y': 16, 'w': 4, 'h': 4},
    {'i': 'chart-stability-dist',     'x': 4, 'y': 16, 'w': 4,  'h': 4},
    {'i': 'chart-difficulty-dist',    'x': 8, 'y': 16, 'w': 4,  'h': 4},
    {'i': 'chart-completion',         'x': 0, 'y': 20, 'w': 8,  'h': 4},
    {'i': 'chart-retention-workload', 'x': 8, 'y': 20, 'w': 4,  'h': 4},
    {'i': 'chart-cohorts',            'x': 0, 'y': 24, 'w': 8,  'h': 4},
    {'i': 'chart-fatigue',            'x': 8, 'y': 24, 'w': 4,  'h': 4},
]


def _grid_chart(chart_id):
    """A draggable/resizable grid item wrapping one chart."""
    return dgl.DraggableWrapper(
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
        dcc.Store(id='grid-layout-store', storage_type='local'),
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

            # ── Chart Grid (draggable / resizable) ──
            dgl.DashGridLayout(
                id='chart-grid',
                items=[_grid_chart(item['i']) for item in DEFAULT_GRID_LAYOUT],
                itemLayout=DEFAULT_GRID_LAYOUT,
                rowHeight=62,
                cols={'lg': 12, 'md': 12, 'sm': 6, 'xs': 4, 'xxs': 2},
                compactType='vertical',
                showRemoveButton=False,
                showResizeHandles=True,
                style={'minHeight': '400px'},
            ),

        ], className='dashboard'),
    ])
