"""
Dash callbacks for the Anki Learning Dashboard.
All @callback decorators register against the global Dash app instance.
"""

import base64
import time
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, callback, clientside_callback, ctx, no_update

from .config import DATA_DIR
from .constants import COLORS, DARK_CHART_LAYOUT
from .upload_handler import process_apkg_upload
from anki.errors import SyncError

from .anki_sync import sync_from_ankiweb, login, is_logged_in, get_last_sync_time
from .layout import create_stat_item, DEFAULT_GRID_LAYOUT, sanitize_grid_item, segmented_styles
from .charts_session import (
    create_daily_reviews_chart,
    create_hourly_chart,
    create_success_rate_chart,
    create_efficiency_chart,
    create_future_load_chart,
)
from .charts_card import (
    create_known_words_chart,
    create_calibration_chart,
    create_retention_workload_chart,
    create_load_timeseries_chart,
    create_load_by_introduction_chart,
    create_lapse_load_chart,
    create_fatigue_chart,
    create_sim_memorized_chart,
    create_sim_reviews_chart,
    create_retrievability_distribution_chart,
    create_stability_distribution_chart,
    create_difficulty_distribution_chart,
)
from .data_loader import (
    get_session_data,
    get_hourly_stats,
    get_daily_reviews,
    get_card_data,
    get_future_load_forecast,
    get_overview_stats,
    get_session_summary_stats,
    get_workload_summary,
    calculate_daily_load,
    get_load_timeseries,
    get_load_by_introduction,
    get_session_dates,
    get_lapse_load,
)
from .fsrs_engine import (
    get_known_words_timeseries,
    get_calibration_data,
    get_calibration_summary,
    get_retention_workload_curve,
    get_fatigue_curve,
    simulate_future,
    get_true_retention,
    get_deck_sim_defaults,
)


def parse_time_range(time_range):
    """Time-range dropdown value -> number of days (None = all time)."""
    return int(time_range) if time_range and time_range != 'all' else None


def parse_deck(deck_value):
    """Deck dropdown value -> deck id (None = all decks)."""
    return None if deck_value == 'all' else int(deck_value)


# Toast colours; position and shape come from the .toast-msg CSS class
def _toast(color, bg):
    return {'display': 'block', 'color': color, 'backgroundColor': bg,
            'border': f'1px solid {color}'}


_TOAST_SUCCESS = _toast(COLORS['success'], '#162312')
_TOAST_ERROR = _toast(COLORS['danger'], '#2a1215')


_EMPTY_FIG = go.Figure(layout=dict(
    plot_bgcolor=DARK_CHART_LAYOUT['plot_bgcolor'],
    paper_bgcolor=DARK_CHART_LAYOUT['paper_bgcolor'],
    xaxis=dict(visible=False), yaxis=dict(visible=False),
    annotations=[dict(text='No data', xref='paper', yref='paper', x=0.5, y=0.5,
                      showarrow=False, font=dict(size=14, color=COLORS['text_muted']))],
))


# ---------------------------------------------------------------------------
# Callback: Overview stats (stat strip)
# ---------------------------------------------------------------------------

@callback(
    [
        Output('stat-upcoming', 'children'),
        Output('stat-streak', 'children'),
        Output('stat-recall-rate', 'children'),
        Output('stat-true-retention', 'children'),
        Output('stat-overdue', 'children'),
        Output('stat-total-reviews', 'children'),
        Output('stat-total-hours', 'children'),
        Output('stat-days-active', 'children'),
        Output('stat-cards-learned', 'children'),
        Output('stat-avg-retrievability', 'children'),
        Output('stat-daily-load', 'children'),
    ],
    [Input('backup-refresh-token', 'data'),
     Input('url', 'pathname'),
     Input('deck-filter', 'value'),
     Input('load-basis', 'data')],
    prevent_initial_call=False
)
def update_overview_container(_refresh_token, _url, deck_value, load_basis):
    """Populate the stat strip with current metrics."""
    deck_id = parse_deck(deck_value)
    use_stability = (load_basis == 'stability')
    stats = get_overview_stats(deck_id=deck_id)
    ret = get_card_data(deck_id=deck_id)['retrievability']
    mean_ret = float(ret.mean()) if len(ret) else 0.0
    workload = get_workload_summary(deck_id=deck_id)
    session_stats = get_session_summary_stats(deck_id=deck_id)

    # Primary stats
    upcoming = create_stat_item(
        f"{workload['due_this_week']}", 'Due This Week', COLORS['primary'])
    streak = create_stat_item(
        f"{session_stats['current_streak']}d", 'Streak', COLORS['success'])
    recall = create_stat_item(
        f"{session_stats['avg_success_rate']:.0f}%", 'Recall Rate',
        COLORS['success'] if session_stats['avg_success_rate'] >= 85 else COLORS['warning'])
    true_ret = get_true_retention(deck_id=deck_id)
    fmt = lambda v: '—' if v is None else f"{v:.0f}%"
    true_retention = create_stat_item(
        fmt(true_ret['month']), 'True Ret. 30d',
        COLORS['text_muted'] if true_ret['month'] is None
        else COLORS['success'] if true_ret['month'] >= 85 else COLORS['warning'],
        title=(f"Anki's true retention (review cards, pass = Hard/Good/Easy)\n"
               f"Week {fmt(true_ret['week'])} · Month {fmt(true_ret['month'])} · "
               f"Year {fmt(true_ret['year'])}"))
    overdue = create_stat_item(
        f"{workload['overdue_cards']}", 'Overdue',
        COLORS['danger'] if workload['overdue_cards'] > 0 else COLORS['success'])

    # Secondary stats
    total_reviews = create_stat_item(
        f"{stats['total_reviews']:,}", 'Total Reviews', COLORS['text_secondary'], secondary=True)
    total_hours = create_stat_item(
        f"{stats['total_hours']:.1f}h", 'Hours', COLORS['text_secondary'], secondary=True)
    days_active = create_stat_item(
        f"{stats['days_studied']}", 'Days Active', COLORS['text_secondary'], secondary=True)
    cards_learned = create_stat_item(
        f"{stats['review_cards']:,}", 'Cards Learned', COLORS['text_secondary'], secondary=True)
    avg_ret = create_stat_item(
        f"{mean_ret:.0f}%", 'Avg Ret.',
        COLORS['success'] if mean_ret >= 80 else COLORS['warning'],
        secondary=True)
    daily_load = create_stat_item(
        f"{calculate_daily_load(deck_id=deck_id, use_stability=use_stability):.1f}",
        'Daily Load', COLORS['text_secondary'], secondary=True)

    return (upcoming, streak, recall, true_retention, overdue, total_reviews, total_hours,
            days_active, cards_learned, avg_ret, daily_load)


# ---------------------------------------------------------------------------
# Callbacks: Persist / restore the draggable chart grid layout
# ---------------------------------------------------------------------------

# Save grid changes and normalize resizes, fully clientside (no server
# round-trip). When an item's width changed, row membership is restored
# from the previous stored layout and neighbours shrink so the row still
# sums to 3 units; the corrected layout is re-applied just after the
# component's own debounced itemLayout self-write (~50ms) has settled.
clientside_callback(
    """
    function(current, prev) {
        const nu = window.dash_clientside.no_update;
        if (!Array.isArray(current) || !current.length) { return nu; }
        const COLS = 3;
        const pick = it => ({i: it.i, x: it.x, y: it.y, w: it.w, h: 1});
        const canon = current.filter(it => it && typeof it.i === 'string').map(pick);

        let out = canon;
        if (Array.isArray(prev) && prev.length) {
            const prevBy = {}, curBy = {};
            prev.forEach(it => { if (it && it.i) { prevBy[it.i] = it; } });
            canon.forEach(it => { curBy[it.i] = it; });
            const pKeys = Object.keys(prevBy).sort(), cKeys = Object.keys(curBy).sort();
            if (JSON.stringify(pKeys) === JSON.stringify(cKeys)) {
                const resized = cKeys.filter(k => (curBy[k].w | 0) !== (prevBy[k].w | 0));
                if (resized.length) {
                    const target = resized[0];
                    const rows = {};
                    pKeys.forEach(k => {
                        const y = prevBy[k].y | 0;
                        (rows[y] = rows[y] || []).push(k);
                    });
                    const res = {};
                    Object.keys(rows).forEach(yk => {
                        const y = +yk;
                        const members = rows[yk].sort((a, b) => (prevBy[a].x | 0) - (prevBy[b].x | 0));
                        if (!members.includes(target)) {
                            members.forEach(k => { res[k] = pick(prevBy[k]); });
                            return;
                        }
                        const others = members.filter(k => k !== target);
                        const wT = Math.max(1, Math.min(curBy[target].w | 0, COLS - others.length));
                        const remaining = COLS - wT;
                        const widths = {}; widths[target] = wT;
                        if (others.length) {
                            const prevTotal = others.reduce((s, k) => s + (prevBy[k].w | 0), 0);
                            if (prevTotal <= remaining) {
                                others.forEach(k => { widths[k] = prevBy[k].w | 0; });
                                widths[others[others.length - 1]] += remaining - prevTotal;
                            } else {
                                others.forEach(k => { widths[k] = 1; });
                                let slack = remaining - others.length;
                                const order = others.slice().sort((a, b) => (prevBy[b].w | 0) - (prevBy[a].w | 0));
                                let idx = 0;
                                while (slack > 0) { widths[order[idx % order.length]] += 1; slack -= 1; idx += 1; }
                            }
                        }
                        let x = 0;
                        members.forEach(k => { res[k] = {i: k, x: x, y: y, w: widths[k], h: 1}; x += widths[k]; });
                    });
                    out = cKeys.map(k => res[k]).filter(Boolean);
                    // Snap the grid to the corrected layout once the
                    // component's internal debounced write has landed.
                    setTimeout(function() {
                        window.dash_clientside.set_props('chart-grid', {itemLayout: out});
                        setTimeout(function() { window.dispatchEvent(new Event('resize')); }, 120);
                    }, 150);
                }
            }
        }
        return out;
    }
    """,
    Output('grid-layout-store', 'data'),
    Input('chart-grid', 'currentLayout'),
    State('grid-layout-store', 'data'),
    prevent_initial_call=True,
)


@callback(
    Output('chart-grid', 'itemLayout'),
    Input('url', 'pathname'),
    State('grid-layout-store', 'data'),
    prevent_initial_call=False,
)
def restore_grid_layout(_, stored):
    """Restore the saved grid layout on page load. Stored items are clamped
    onto the discrete 3-column grid (also migrates stale layouts saved under
    older grid geometries); charts missing from the store get defaults."""
    if not stored:
        return DEFAULT_GRID_LAYOUT
    # Layouts saved under a different grid geometry (e.g. the old 12-column
    # grid) can't be meaningfully clamped — reset to defaults instead.
    if any(isinstance(i, dict) and (i.get('w') or 0) > 3 for i in stored):
        return DEFAULT_GRID_LAYOUT
    by_id = {item.get('i'): item for item in stored if isinstance(item, dict)}
    return [
        sanitize_grid_item(by_id[d['i']], d) if d['i'] in by_id else dict(d)
        for d in DEFAULT_GRID_LAYOUT
    ]


# Plotly only re-renders on window resize; the grid resizes containers
# without one, so dispatch a synthetic resize after every layout change.
clientside_callback(
    """
    function(_layout) {
        setTimeout(function() { window.dispatchEvent(new Event('resize')); }, 150);
        return window.dash_clientside.no_update;
    }
    """,
    Output('grid-resize-sync', 'data'),
    Input('chart-grid', 'currentLayout'),
    prevent_initial_call=False,
)


# ---------------------------------------------------------------------------
# Callback: Load UI from localStorage
# ---------------------------------------------------------------------------

@callback(
    [
        Output('session-time-range', 'value'),
        Output('deck-filter', 'value')
    ],
    [Input('url', 'pathname')],
    [State('ui-store', 'data')],
    prevent_initial_call=False
)
def load_ui_from_store(_, ui_store):
    """Load UI preferences from local storage on page load."""
    ui_store = ui_store or {}
    return ui_store.get('session_time_range', 'all'), ui_store.get('deck_filter', 'all')


# ---------------------------------------------------------------------------
# Callback: Toggle x-axis mode (dark button styles)
# ---------------------------------------------------------------------------

@callback(
    [Output('xaxis-mode', 'data'),
     Output('xaxis-dates-btn', 'style'),
     Output('xaxis-sessions-btn', 'style')],
    [Input('xaxis-dates-btn', 'n_clicks'),
     Input('xaxis-sessions-btn', 'n_clicks'),
     Input('url', 'pathname')],
    [State('ui-store', 'data')],
    prevent_initial_call=False
)
def toggle_xaxis_mode(dates_clicks, sessions_clicks, _, ui_store):
    """Toggle between dates and sessions x-axis mode."""
    triggered = ctx.triggered_id

    if triggered == 'url' or not triggered:
        mode = (ui_store or {}).get('xaxis_mode', 'dates')
    elif triggered == 'xaxis-dates-btn':
        mode = 'dates'
    else:
        mode = 'sessions'

    return (mode, *segmented_styles(mode == 'dates'))


@callback(
    [Output('load-basis', 'data'),
     Output('load-interval-btn', 'style'),
     Output('load-stability-btn', 'style')],
    [Input('load-interval-btn', 'n_clicks'),
     Input('load-stability-btn', 'n_clicks'),
     Input('url', 'pathname')],
    [State('ui-store', 'data')],
    prevent_initial_call=False
)
def toggle_load_basis(_interval_clicks, _stability_clicks, _, ui_store):
    """Toggle load computations between stored intervals and stability."""
    triggered = ctx.triggered_id
    if triggered == 'url' or not triggered:
        basis = (ui_store or {}).get('load_basis', 'interval')
    elif triggered == 'load-stability-btn':
        basis = 'stability'
    else:
        basis = 'interval'

    return (basis, *segmented_styles(basis == 'interval'))


# ---------------------------------------------------------------------------
# Callback: Save UI preferences
# ---------------------------------------------------------------------------

@callback(
    Output('ui-store', 'data'),
    [
        Input('session-time-range', 'value'),
        Input('xaxis-mode', 'data'),
        Input('deck-filter', 'value'),
        Input('load-basis', 'data')
    ],
    prevent_initial_call=False
)
def save_ui_to_store(session_value, xaxis_value, deck_value, load_basis):
    """Persist UI preferences to local storage."""
    return {
        'session_time_range': session_value or 'all',
        'xaxis_mode': xaxis_value or 'dates',
        'deck_filter': deck_value or 'all',
        'load_basis': load_basis or 'interval',
    }


# ---------------------------------------------------------------------------
# Callback: Handle backup file upload
# ---------------------------------------------------------------------------

@callback(
    [
        Output('upload-status-message', 'children'),
        Output('upload-status-message', 'style'),
        Output('upload-message-interval', 'disabled'),
        Output('upload-message-interval', 'n_intervals'),
        Output('backup-refresh-token', 'data', allow_duplicate=True),
    ],
    [Input('upload-backup-button', 'contents')],
    [State('upload-backup-button', 'filename')],
    prevent_initial_call=True
)
def handle_backup_upload(contents, filename):
    """Process uploaded .apkg file."""
    if not contents:
        return "", {'display': 'none'}, False, 0, no_update

    if not filename or not filename.lower().endswith('.apkg'):
        return "Invalid file format. Upload an .apkg file.", _TOAST_ERROR, False, 0, no_update

    try:
        content_type, content_string = contents.split(',')
        file_bytes = base64.b64decode(content_string)

        success, message = process_apkg_upload(file_bytes, DATA_DIR)

        if success:
            return message, _TOAST_SUCCESS, False, 0, time.time()
        else:
            return message, _TOAST_ERROR, False, 0, no_update

    except Exception as e:
        return f"Upload error: {str(e)}", _TOAST_ERROR, False, 0, no_update


# ---------------------------------------------------------------------------
# Callbacks: Sync from AnkiWeb + login
# ---------------------------------------------------------------------------

_LOGIN_SHOWN = {'display': 'flex'}
_LOGIN_HIDDEN = {'display': 'none'}


def _sync_outputs():
    """Run a sync; returns (toast text, toast style, interval disabled, n_intervals, refresh, login style)."""
    success, message = sync_from_ankiweb(DATA_DIR)
    login_style = _LOGIN_HIDDEN if is_logged_in(DATA_DIR) else _LOGIN_SHOWN
    if success:
        return message, _TOAST_SUCCESS, False, 0, time.time(), login_style
    return message, _TOAST_ERROR, False, 0, no_update, login_style


_SYNC_OUTPUTS = [
    Output('upload-status-message', 'children', allow_duplicate=True),
    Output('upload-status-message', 'style', allow_duplicate=True),
    Output('upload-message-interval', 'disabled', allow_duplicate=True),
    Output('upload-message-interval', 'n_intervals', allow_duplicate=True),
    Output('backup-refresh-token', 'data', allow_duplicate=True),
    Output('ankiweb-login', 'style'),
]


@callback(
    _SYNC_OUTPUTS,
    [Input('sync-from-anki-button', 'n_clicks')],
    [State('ankiweb-login', 'style')],
    prevent_initial_call=True
)
def handle_anki_sync(n_clicks, login_style):
    """Sync from AnkiWeb, or toggle the login panel when no sync key is stored."""
    if not n_clicks:
        return (no_update,) * 6
    if not is_logged_in(DATA_DIR):
        shown = (login_style or {}).get('display') != 'none'
        return (no_update,) * 5 + (_LOGIN_HIDDEN if shown else _LOGIN_SHOWN,)
    return _sync_outputs()


@callback(
    _SYNC_OUTPUTS + [Output('ankiweb-password', 'value')],
    [Input('ankiweb-login-button', 'n_clicks'),
     Input('ankiweb-password', 'n_submit')],
    [State('ankiweb-email', 'value'),
     State('ankiweb-password', 'value')],
    prevent_initial_call=True
)
def handle_ankiweb_login(_clicks, _submits, email, password):
    """Log in to AnkiWeb (stores only the sync key), then sync."""
    if not email or not password:
        return "Enter your AnkiWeb email and password.", _TOAST_ERROR, False, 0, no_update, no_update, no_update
    try:
        login(DATA_DIR, email.strip(), password)
    except SyncError as e:
        return f"AnkiWeb login failed: {e}", _TOAST_ERROR, False, 0, no_update, no_update, ''
    return _sync_outputs() + ('',)


# ---------------------------------------------------------------------------
# Callback: Last sync indicator
# ---------------------------------------------------------------------------

@callback(
    [Output('last-sync-indicator', 'children'),
     Output('last-sync-indicator', 'title')],
    [Input('backup-refresh-token', 'data'),
     Input('url', 'pathname')],
)
def update_last_sync_indicator(_refresh_token, _url):
    """Show when the last successful AnkiWeb sync happened (uploads don't count)."""
    ts = get_last_sync_time(DATA_DIR)
    if ts is None:
        return 'Never synced', 'No successful sync from AnkiWeb recorded'

    synced = datetime.fromtimestamp(ts)
    days_ago = (datetime.now().date() - synced.date()).days
    if days_ago == 0:
        when = f"today {synced:%H:%M}"
    elif days_ago == 1:
        when = f"yesterday {synced:%H:%M}"
    else:
        when = f"{synced:%b} {synced.day}"
    return f"Synced {when}", f"Last successful sync from AnkiWeb: {synced:%Y-%m-%d %H:%M}"


# ---------------------------------------------------------------------------
# Callback: Auto-dismiss upload message
# ---------------------------------------------------------------------------

@callback(
    [
        Output('upload-status-message', 'style', allow_duplicate=True),
        Output('upload-message-interval', 'disabled', allow_duplicate=True),
    ],
    [Input('upload-message-interval', 'n_intervals')],
    prevent_initial_call=True
)
def auto_dismiss_upload_message(n):
    """Hide the upload status message after 3 seconds."""
    if not n:
        return no_update, no_update
    return {'display': 'none'}, True


# ---------------------------------------------------------------------------
# Callback: Forecast simulator
# ---------------------------------------------------------------------------

@callback(
    [Output('sim-retention', 'value'),
     Output('sim-new', 'value'),
     Output('sim-maxrev', 'value')],
    [Input('deck-filter', 'value'),
     Input('url', 'pathname')],
    prevent_initial_call=False,
)
def sync_sim_defaults_from_preset(deck_value, _url):
    """Auto-fill the simulator inputs from the selected deck's Anki preset."""
    deck_id = parse_deck(deck_value)
    d = get_deck_sim_defaults(deck_id)
    return d['retention'], d['new_per_day'], d['rev_per_day']


@callback(
    [Output('chart-sim-memorized', 'figure'),
     Output('chart-sim-reviews', 'figure')],
    [Input('sim-run', 'n_clicks')],
    [State('sim-days', 'value'),
     State('sim-retention', 'value'),
     State('sim-new', 'value'),
     State('sim-maxrev', 'value'),
     State('deck-filter', 'value')],
    prevent_initial_call=True,
)
def run_forecast_simulation(_n, days, retention, new_per_day, max_reviews, deck_value):
    """Run the FSRS forward simulation and render the projection charts."""
    deck_id = parse_deck(deck_value)
    days = int(days or 365)
    retention = min(max(float(retention or 90) / 100.0, 0.70), 0.97)
    new_per_day = max(int(new_per_day or 0), 0)
    max_reviews = max(int(max_reviews or 200), 1)

    sim = simulate_future(
        deck_id=deck_id, days=days, desired_retention=retention,
        new_per_day=new_per_day, max_reviews=max_reviews,
    )
    return create_sim_memorized_chart(sim), create_sim_reviews_chart(sim)


# ---------------------------------------------------------------------------
# Callback: Update session charts (5 figures)
# ---------------------------------------------------------------------------

@callback(
    [
        Output('chart-daily-reviews', 'figure'),
        Output('chart-hourly', 'figure'),
        Output('chart-recall-rate', 'figure'),
        Output('chart-review-speed', 'figure'),
        Output('chart-future-load', 'figure'),
    ],
    [Input('session-time-range', 'value'),
     Input('xaxis-mode', 'data'),
     Input('backup-refresh-token', 'data'),
     Input('deck-filter', 'value')],
    prevent_initial_call=False
)
def update_session_charts(time_range, xaxis_mode, _refresh_token, deck_value):
    """Update session charts based on time range and x-axis mode."""
    use_sessions = (xaxis_mode == 'sessions')
    review_days = parse_time_range(time_range)
    deck_id = parse_deck(deck_value)
    forecast_days = 365

    session_df = get_session_data(review_days, deck_id=deck_id)
    hourly_df = get_hourly_stats(review_days, deck_id=deck_id)
    daily_df = get_daily_reviews(review_days, deck_id=deck_id)
    forecast_df = get_future_load_forecast(forecast_days, deck_id=deck_id)

    if session_df.empty:
        return (_EMPTY_FIG,) * 5

    fig_daily = create_daily_reviews_chart(daily_df, use_sessions=use_sessions)
    fig_hourly = create_hourly_chart(hourly_df)
    fig_recall = create_success_rate_chart(session_df, use_sessions=use_sessions)
    fig_speed = create_efficiency_chart(session_df, use_sessions=use_sessions)
    fig_forecast = create_future_load_chart(forecast_df, days_ahead=forecast_days)

    return fig_daily, fig_hourly, fig_recall, fig_speed, fig_forecast


# ---------------------------------------------------------------------------
# Callback: Update card charts (4 figures)
# ---------------------------------------------------------------------------

@callback(
    [
        Output('chart-known-words', 'figure'),
        Output('chart-calibration', 'figure'),
        Output('chart-retrievability-dist', 'figure'),
        Output('chart-stability-dist', 'figure'),
        Output('chart-difficulty-dist', 'figure'),
        Output('chart-retention-workload', 'figure'),
        Output('chart-load-intro', 'figure'),
        Output('chart-fatigue', 'figure'),
        Output('chart-load-trend', 'figure'),
        Output('chart-lapse-load', 'figure'),
    ],
    [Input('backup-refresh-token', 'data'),
     Input('deck-filter', 'value'),
     Input('session-time-range', 'value'),
     Input('xaxis-mode', 'data'),
     Input('load-basis', 'data')],
    prevent_initial_call=False
)
def update_card_charts(_refresh_token, deck_value, time_range, xaxis_mode, load_basis):
    """Update card charts based on filters, date range and x-axis mode."""
    deck_id = parse_deck(deck_value)
    use_sessions = (xaxis_mode == 'sessions')
    use_stability = (load_basis == 'stability')
    review_days = parse_time_range(time_range)
    cutoff = (None if review_days is None
              else pd.Timestamp(datetime.now().date()) - pd.Timedelta(days=review_days))
    cards_df = get_card_data(deck_id=deck_id)

    if cards_df.empty:
        return (_EMPTY_FIG,) * 10

    session_dates = get_session_dates(deck_id=deck_id)

    # Known Cards: obey the date range only (no session mode)
    known_df = get_known_words_timeseries(deck_id=deck_id)
    if cutoff is not None:
        known_df = known_df[known_df['date'] >= cutoff]
    fig_known = create_known_words_chart(known_df)

    fig_calib = create_calibration_chart(
        get_calibration_data(deck_id=deck_id),
        summary=get_calibration_summary(deck_id=deck_id),
    )
    fig_ret = create_retrievability_distribution_chart(cards_df)
    fig_stab = create_stability_distribution_chart(cards_df)
    fig_diff = create_difficulty_distribution_chart(cards_df)
    fig_retention = create_retention_workload_chart(get_retention_workload_curve(deck_id=deck_id))

    # Load by Introduction: date range + session bucketing
    intro_df = get_load_by_introduction(deck_id=deck_id, use_stability=use_stability)
    if cutoff is not None and not intro_df.empty:
        intro_df = intro_df[intro_df['intro_date'] >= cutoff]
    fig_load_intro = create_load_by_introduction_chart(
        intro_df, use_sessions=use_sessions, session_dates=session_dates)

    fig_fatigue = create_fatigue_chart(get_fatigue_curve(deck_id=deck_id))

    # Load Trend: date range + session numbering
    load_df = get_load_timeseries(deck_id=deck_id, use_stability=use_stability)
    if cutoff is not None and not load_df.empty:
        load_df = load_df[load_df['date'] >= cutoff]
    fig_load_trend = create_load_timeseries_chart(
        load_df, use_sessions=use_sessions, session_dates=session_dates)

    fig_lapse_load = create_lapse_load_chart(
        get_lapse_load(deck_id=deck_id, use_stability=use_stability))

    return (fig_known, fig_calib, fig_ret, fig_stab, fig_diff,
            fig_retention, fig_load_intro, fig_fatigue, fig_load_trend,
            fig_lapse_load)
