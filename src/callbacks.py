"""
Dash callbacks for the Anki Learning Dashboard.
All @callback decorators register against the global Dash app instance.
"""

import base64
import os
import time
from dash import dcc, html, Input, Output, State, callback, ctx, no_update

from .constants import COLORS
from .upload_handler import process_apkg_upload
from .anki_sync import sync_from_anki, get_sync_info
from .layout import create_stat_item
from .charts_session import (
    create_daily_reviews_chart,
    create_hourly_chart,
    create_success_rate_chart,
    create_efficiency_chart,
    create_future_load_chart,
)
from .charts_card import (
    create_memory_state_chart,
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
    get_memory_state_summary,
    get_session_summary_stats,
    get_workload_summary,
    get_knowledge_health_stats,
)


def parse_time_range(time_range):
    """Parse time range value into review_days and year_filter."""
    if time_range == 'all':
        return None, None
    elif isinstance(time_range, str) and time_range.startswith('year_'):
        return None, int(time_range.split('_')[1])
    else:
        return int(time_range) if time_range else None, None


# Dark toast styles
_TOAST_SUCCESS = {
    'display': 'block',
    'padding': '8px 14px',
    'backgroundColor': '#162312',
    'color': COLORS['success'],
    'border': f'1px solid {COLORS["success"]}',
    'borderRadius': '4px',
    'fontSize': '12px',
    'position': 'fixed',
    'top': '12px',
    'right': '12px',
    'zIndex': '1000',
    'boxShadow': '0 4px 12px rgba(0,0,0,0.5)',
}
_TOAST_ERROR = {
    'display': 'block',
    'padding': '8px 14px',
    'backgroundColor': '#2a1215',
    'color': COLORS['danger'],
    'border': f'1px solid {COLORS["danger"]}',
    'borderRadius': '4px',
    'fontSize': '12px',
    'position': 'fixed',
    'top': '12px',
    'right': '12px',
    'zIndex': '1000',
    'boxShadow': '0 4px 12px rgba(0,0,0,0.5)',
}
_TOAST_WARN = {
    'display': 'block',
    'padding': '8px 14px',
    'backgroundColor': '#2a2010',
    'color': COLORS['warning'],
    'border': f'1px solid {COLORS["warning"]}',
    'borderRadius': '4px',
    'fontSize': '12px',
    'position': 'fixed',
    'top': '12px',
    'right': '12px',
    'zIndex': '1000',
    'boxShadow': '0 4px 12px rgba(0,0,0,0.5)',
}


# ---------------------------------------------------------------------------
# Callback: Overview stats (stat strip)
# ---------------------------------------------------------------------------

@callback(
    [
        Output('stat-upcoming', 'children'),
        Output('stat-streak', 'children'),
        Output('stat-recall-rate', 'children'),
        Output('stat-overdue', 'children'),
        Output('stat-total-reviews', 'children'),
        Output('stat-total-hours', 'children'),
        Output('stat-days-active', 'children'),
        Output('stat-cards-learned', 'children'),
        Output('stat-avg-retrievability', 'children'),
    ],
    [Input('backup-refresh-token', 'data'),
     Input('url', 'pathname'),
     Input('deck-filter', 'value')],
    prevent_initial_call=False
)
def update_overview_container(_refresh_token, _url, deck_value):
    """Populate the stat strip with current metrics."""
    deck_id = None if deck_value == 'all' else int(deck_value)
    stats = get_overview_stats(deck_id=deck_id)
    memory = get_memory_state_summary(deck_id=deck_id)
    workload = get_workload_summary(deck_id=deck_id)
    session_stats = get_session_summary_stats(deck_id=deck_id)
    health = get_knowledge_health_stats(deck_id=deck_id)

    # Primary stats
    upcoming = create_stat_item(
        f"{workload['due_this_week']}", 'Due This Week', COLORS['primary'])
    streak = create_stat_item(
        f"{session_stats['current_streak']}d", 'Streak', COLORS['success'])
    recall = create_stat_item(
        f"{session_stats['avg_success_rate']:.0f}%", 'Recall Rate',
        COLORS['success'] if session_stats['avg_success_rate'] >= 85 else COLORS['warning'])
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
        f"{memory['mean_retrievability']:.0f}%", 'Avg Ret.',
        COLORS['success'] if memory['mean_retrievability'] >= 80 else COLORS['warning'],
        secondary=True)

    return upcoming, streak, recall, overdue, total_reviews, total_hours, days_active, cards_learned, avg_ret


# ---------------------------------------------------------------------------
# Callback: Load UI from localStorage
# ---------------------------------------------------------------------------

@callback(
    [
        Output('session-time-range', 'value'),
        Output('retrievability-filter', 'value'),
        Output('difficulty-filter', 'value'),
        Output('deck-filter', 'value')
    ],
    [Input('url', 'pathname')],
    [State('ui-store', 'data')],
    prevent_initial_call=False
)
def load_ui_from_store(_, ui_store):
    """Load UI preferences from local storage on page load."""
    defaults = {
        'session_time_range': 'all',
        'retrievability_filter': [0, 100],
        'difficulty_filter': [0, 10],
        'deck_filter': 'all'
    }

    if not ui_store:
        ui_store = defaults

    session = ui_store.get('session_time_range', defaults['session_time_range'])
    retr = ui_store.get('retrievability_filter', defaults['retrievability_filter'])
    diff = ui_store.get('difficulty_filter', defaults['difficulty_filter'])
    deck = ui_store.get('deck_filter', defaults['deck_filter'])

    return session, retr, diff, deck


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
    base = {
        'padding': '4px 12px',
        'cursor': 'pointer',
        'fontSize': '12px',
        'fontWeight': '500',
        'lineHeight': '1.4',
    }
    active_style = {
        **base,
        'border': f'1px solid {COLORS["primary"]}',
        'backgroundColor': COLORS['primary'],
        'color': '#fff',
    }
    inactive_style = {
        **base,
        'border': f'1px solid {COLORS["border"]}',
        'backgroundColor': COLORS['bg_secondary'],
        'color': COLORS['text_secondary'],
    }

    triggered = ctx.triggered_id

    if triggered == 'url' or not triggered:
        mode = (ui_store or {}).get('xaxis_mode', 'dates')
    elif triggered == 'xaxis-dates-btn':
        mode = 'dates'
    else:
        mode = 'sessions'

    if mode == 'dates':
        dates_s = {**active_style, 'borderRadius': '3px 0 0 3px'}
        sessions_s = {**inactive_style, 'borderRadius': '0 3px 3px 0', 'borderLeft': 'none'}
    else:
        dates_s = {**inactive_style, 'borderRadius': '3px 0 0 3px'}
        sessions_s = {**active_style, 'borderRadius': '0 3px 3px 0', 'borderLeft': 'none'}

    return mode, dates_s, sessions_s


# ---------------------------------------------------------------------------
# Callback: Save UI preferences
# ---------------------------------------------------------------------------

@callback(
    Output('ui-store', 'data'),
    [
        Input('session-time-range', 'value'),
        Input('xaxis-mode', 'data'),
        Input('retrievability-filter', 'value'),
        Input('difficulty-filter', 'value'),
        Input('deck-filter', 'value')
    ],
    prevent_initial_call=False
)
def save_ui_to_store(session_value, xaxis_value, retr_value, diff_value, deck_value):
    """Persist UI preferences to local storage."""
    return {
        'session_time_range': session_value or 'all',
        'xaxis_mode': xaxis_value or 'dates',
        'retrievability_filter': retr_value or [0, 100],
        'difficulty_filter': diff_value or [0, 10],
        'deck_filter': deck_value or 'all',
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

        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(script_dir)
        data_dir = os.path.join(project_dir, 'data')

        success, message = process_apkg_upload(file_bytes, data_dir)

        if success:
            return message, _TOAST_SUCCESS, False, 0, time.time()
        else:
            return message, _TOAST_ERROR, False, 0, no_update

    except Exception as e:
        return f"Upload error: {str(e)}", _TOAST_ERROR, False, 0, no_update


# ---------------------------------------------------------------------------
# Callback: Sync from Anki
# ---------------------------------------------------------------------------

@callback(
    [
        Output('upload-status-message', 'children', allow_duplicate=True),
        Output('upload-status-message', 'style', allow_duplicate=True),
        Output('upload-message-interval', 'disabled', allow_duplicate=True),
        Output('upload-message-interval', 'n_intervals', allow_duplicate=True),
        Output('backup-refresh-token', 'data', allow_duplicate=True),
    ],
    [Input('sync-from-anki-button', 'n_clicks')],
    prevent_initial_call=True
)
def handle_anki_sync(n_clicks):
    """Sync Anki collection from local installation."""
    if not n_clicks:
        return "", {'display': 'none'}, False, 0, no_update

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    data_dir = os.path.join(project_dir, 'data')

    sync_info = get_sync_info()

    if not sync_info['anki_installed']:
        return "Anki installation not found.", _TOAST_WARN, False, 0, no_update

    if sync_info['profiles_found'] == 0:
        return f"No Anki profiles found in {sync_info['anki_path']}", _TOAST_WARN, False, 0, no_update

    if sync_info['anki_running']:
        return "Anki is running. Close it before syncing.", _TOAST_ERROR, False, 0, no_update

    try:
        success, message = sync_from_anki(None, data_dir)
        if success:
            return message, _TOAST_SUCCESS, False, 0, time.time()
        else:
            return message, _TOAST_ERROR, False, 0, no_update
    except Exception as e:
        return f"Sync error: {str(e)}", _TOAST_ERROR, False, 0, no_update


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
    [State('ui-store', 'data')],
    prevent_initial_call=False
)
def update_session_charts(time_range, xaxis_mode, _refresh_token, deck_value, ui_store):
    """Update session charts based on time range and x-axis mode."""
    use_sessions = (xaxis_mode == 'sessions')
    review_days, year_filter = parse_time_range(time_range)
    deck_id = None if deck_value == 'all' else int(deck_value)
    forecast_days = 60

    session_df = get_session_data(review_days, year_filter, deck_id=deck_id)
    hourly_df = get_hourly_stats(review_days, year_filter, deck_id=deck_id)
    daily_df = get_daily_reviews(review_days, year_filter, deck_id=deck_id)
    forecast_df = get_future_load_forecast(forecast_days, deck_id=deck_id)

    import plotly.graph_objects as go
    empty = go.Figure()
    empty.update_layout(
        plot_bgcolor='#111217', paper_bgcolor='#111217',
        font=dict(color='#5a5e72'),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        annotations=[dict(text='No data', xref='paper', yref='paper',
                          x=0.5, y=0.5, showarrow=False,
                          font=dict(size=14, color='#5a5e72'))]
    )

    if session_df.empty:
        return empty, empty, empty, empty, empty

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
        Output('chart-memory-state', 'figure'),
        Output('chart-retrievability-dist', 'figure'),
        Output('chart-stability-dist', 'figure'),
        Output('chart-difficulty-dist', 'figure'),
    ],
    [Input('retrievability-filter', 'value'),
     Input('difficulty-filter', 'value'),
     Input('backup-refresh-token', 'data'),
     Input('deck-filter', 'value')],
    [State('ui-store', 'data')],
    prevent_initial_call=False
)
def update_card_charts(ret_range, diff_range, _refresh_token, deck_value, ui_store):
    """Update card charts based on filters."""
    deck_id = None if deck_value == 'all' else int(deck_value)
    cards_df = get_card_data(deck_id=deck_id)

    import plotly.graph_objects as go
    empty = go.Figure()
    empty.update_layout(
        plot_bgcolor='#111217', paper_bgcolor='#111217',
        font=dict(color='#5a5e72'),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        annotations=[dict(text='No data', xref='paper', yref='paper',
                          x=0.5, y=0.5, showarrow=False,
                          font=dict(size=14, color='#5a5e72'))]
    )

    if cards_df.empty:
        return empty, empty, empty, empty

    # Filter for distribution charts
    mask = (
        (cards_df['retrievability'] >= ret_range[0]) &
        (cards_df['retrievability'] <= ret_range[1]) &
        (cards_df['difficulty'] >= diff_range[0]) &
        (cards_df['difficulty'] <= diff_range[1])
    )
    filtered_df = cards_df[mask]

    # Memory state uses unfiltered data; distributions use filtered
    fig_memory = create_memory_state_chart(cards_df)
    fig_ret = create_retrievability_distribution_chart(filtered_df)
    fig_stab = create_stability_distribution_chart(filtered_df)
    fig_diff = create_difficulty_distribution_chart(filtered_df)

    return fig_memory, fig_ret, fig_stab, fig_diff
