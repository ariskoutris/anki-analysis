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

# Grid discretization: 3 columns of equal thirds, so a row can only be
# 1-1-1, 2-1, 1-2, or 3. Height is fixed (minH = maxH = 1 row).
GRID_COLS = 3
GRID_ROW_HEIGHT = 300
_GRID_CONSTRAINTS = {'minW': 1, 'maxW': GRID_COLS, 'minH': 1, 'maxH': 1}

# NOTE: layout ids must match the DraggableWrapper ids ('w-' + chart id) —
# the component matches itemLayout entries against child keys, which Dash
# derives from the wrapper's id. The dcc.Graph inside keeps the bare chart id.
DEFAULT_GRID_LAYOUT = [
    {'i': 'w-chart-daily-reviews',       'x': 0, 'y': 0, 'w': 2, 'h': 1, **_GRID_CONSTRAINTS},
    {'i': 'w-chart-hourly',              'x': 2, 'y': 0, 'w': 1, 'h': 1, **_GRID_CONSTRAINTS},
    {'i': 'w-chart-recall-rate',         'x': 0, 'y': 1, 'w': 2, 'h': 1, **_GRID_CONSTRAINTS},
    {'i': 'w-chart-review-speed',        'x': 2, 'y': 1, 'w': 1, 'h': 1, **_GRID_CONSTRAINTS},
    {'i': 'w-chart-known-words',         'x': 0, 'y': 2, 'w': 3, 'h': 1, **_GRID_CONSTRAINTS},
    {'i': 'w-chart-future-load',         'x': 0, 'y': 3, 'w': 2, 'h': 1, **_GRID_CONSTRAINTS},
    {'i': 'w-chart-calibration',         'x': 2, 'y': 3, 'w': 1, 'h': 1, **_GRID_CONSTRAINTS},
    {'i': 'w-chart-retrievability-dist', 'x': 0, 'y': 4, 'w': 1, 'h': 1, **_GRID_CONSTRAINTS},
    {'i': 'w-chart-stability-dist',      'x': 1, 'y': 4, 'w': 1, 'h': 1, **_GRID_CONSTRAINTS},
    {'i': 'w-chart-difficulty-dist',     'x': 2, 'y': 4, 'w': 1, 'h': 1, **_GRID_CONSTRAINTS},
    {'i': 'w-chart-completion',          'x': 0, 'y': 5, 'w': 2, 'h': 1, **_GRID_CONSTRAINTS},
    {'i': 'w-chart-retention-workload',  'x': 2, 'y': 5, 'w': 1, 'h': 1, **_GRID_CONSTRAINTS},
    {'i': 'w-chart-cohorts',             'x': 0, 'y': 6, 'w': 2, 'h': 1, **_GRID_CONSTRAINTS},
    {'i': 'w-chart-fatigue',             'x': 2, 'y': 6, 'w': 1, 'h': 1, **_GRID_CONSTRAINTS},
]


def normalize_grid_resize(current: list, prev: list) -> list | None:
    """
    Keep resizes within their row: when an item's width changes, restore
    every item's row membership from the previous layout and shrink the
    resized item's row-neighbours so the row still sums to exactly
    GRID_COLS units. Growing beyond what neighbours can absorb (each has
    minW=1) is clamped, so a resize can never push panels to another row.

    Returns the corrected layout, or None when no correction is needed
    (not a resize, or layouts don't line up).
    """
    if not prev or not current:
        return None
    prev_by = {i['i']: i for i in prev if isinstance(i, dict) and 'i' in i}
    cur_by = {i['i']: i for i in current if isinstance(i, dict) and 'i' in i}
    if set(prev_by) != set(cur_by):
        return None

    resized = [k for k in cur_by if int(cur_by[k].get('w', 0)) != int(prev_by[k].get('w', 0))]
    if not resized:
        return None
    target = resized[0]

    # Rows from the *previous* layout: membership never changes on resize
    rows: dict[int, list[str]] = {}
    for k, item in prev_by.items():
        rows.setdefault(int(item['y']), []).append(k)

    out = {}
    for y, members in rows.items():
        members.sort(key=lambda k: int(prev_by[k]['x']))
        if target not in members:
            for k in members:
                out[k] = dict(prev_by[k])
            continue

        others = [k for k in members if k != target]
        w_target = max(1, min(int(cur_by[target]['w']), GRID_COLS - len(others)))
        remaining = GRID_COLS - w_target

        widths = {target: w_target}
        if others:
            prev_total = sum(int(prev_by[k]['w']) for k in others)
            if prev_total <= remaining:
                # Neighbours keep their widths; last one absorbs any slack
                for k in others:
                    widths[k] = int(prev_by[k]['w'])
                widths[others[-1]] += remaining - prev_total
            else:
                # Shrink neighbours toward minW=1, widest-first gets leftover
                widths.update({k: 1 for k in others})
                slack = remaining - len(others)
                order = sorted(others, key=lambda k: -int(prev_by[k]['w']))
                idx = 0
                while slack > 0:
                    widths[order[idx % len(order)]] += 1
                    slack -= 1
                    idx += 1

        x = 0
        for k in members:
            out[k] = {**prev_by[k], 'x': x, 'y': y, 'w': widths[k], 'h': 1}
            x += widths[k]

    return [out[d['i']] for d in DEFAULT_GRID_LAYOUT if d['i'] in out]


def sanitize_grid_item(stored: dict, default: dict) -> dict:
    """Clamp a stored grid item onto the discrete 3-column grid."""
    try:
        w = min(max(int(stored.get('w', default['w'])), 1), GRID_COLS)
        x = min(max(int(stored.get('x', default['x'])), 0), GRID_COLS - w)
        y = max(int(stored.get('y', default['y'])), 0)
    except (TypeError, ValueError):
        return dict(default)
    return {'i': default['i'], 'x': x, 'y': y, 'w': w, 'h': 1, **_GRID_CONSTRAINTS}


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
        dcc.Store(id='grid-resize-sync', storage_type='memory'),
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
                rowHeight=GRID_ROW_HEIGHT,
                cols={'lg': GRID_COLS, 'md': GRID_COLS, 'sm': 1, 'xs': 1, 'xxs': 1},
                compactType='vertical',
                showRemoveButton=False,
                showResizeHandles=True,
                style={'minHeight': '400px'},
            ),

        ], className='dashboard'),
    ])
