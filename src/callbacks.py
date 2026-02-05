"""
Dash callbacks for the Anki Learning Dashboard.
All @callback decorators register against the global Dash app instance.
"""

import base64
import os
from dash import dcc, html, Input, Output, State, callback, ctx

from .constants import COLORS
from .upload_handler import process_apkg_upload
from .layout import create_stat_card
from .charts_session import (
    create_daily_reviews_chart,
    create_hourly_chart,
    create_success_rate_chart,
    create_efficiency_chart,
    create_memory_decay_chart,
    create_future_load_chart,
)
from .charts_card import (
    create_memory_state_chart,
    create_retrievability_distribution_chart,
    create_stability_distribution_chart,
    create_difficulty_distribution_chart,
    create_lapses_chart,
    create_reviews_stability_chart,
    create_leech_chart,
)
from .data_loader import (
    get_session_data,
    get_hourly_stats,
    get_daily_reviews,
    get_review_intervals,
    get_card_data,
    get_overview_stats,
    get_memory_state_summary,
    get_session_summary_stats,
    get_workload_summary,
    get_knowledge_health_stats,
    get_leech_candidates,
)
from src.config import (
    get_active_date,
    get_available_dates as get_config_available_dates,
    set_active_date,
)


def parse_time_range(time_range):
    """Parse time range value into review_days and year_filter."""
    if time_range == 'all':
        return None, None
    elif isinstance(time_range, str) and time_range.startswith('year_'):
        return None, int(time_range.split('_')[1])
    else:
        return int(time_range) if time_range else None, None


# ---------------------------------------------------------------------------
# Callback: Overview stats
# ---------------------------------------------------------------------------

@callback(
    [Output('overview-container', 'children'), Output('active-date-banner', 'children')],
    [Input('data-folder-dropdown', 'value')],
    [State('ui-store', 'data')],
    prevent_initial_call=False
)
def update_overview_container(selected_date, ui_store):
    """Dynamically populate the overview statistics section when the selected data folder changes."""
    banner = ''
    if selected_date:
        set_active_date(selected_date)
        banner = f"Active backup: {selected_date}"
    elif not get_active_date():
        dates = get_config_available_dates()
        if dates:
            set_active_date(dates[0])
            banner = f"Active backup: {dates[0]}"

    stats = get_overview_stats()
    memory = get_memory_state_summary()

    overview_div = html.Div([
        html.Div([
            html.Div([
                create_stat_card(f"{stats['total_reviews']:,}", "Total Reviews")
            ], style={'flex': '1', 'padding': '0 10px'}),
            html.Div([
                create_stat_card(f"{stats['total_hours']:.1f}h", "Time Studied")
            ], style={'flex': '1', 'padding': '0 10px'}),
            html.Div([
                create_stat_card(f"{stats['review_cards']:,}", "Cards Learned")
            ], style={'flex': '1', 'padding': '0 10px'}),
            html.Div([
                create_stat_card(f"{stats['days_studied']}", "Days Active")
            ], style={'flex': '1', 'padding': '0 10px'}),
            html.Div([
                create_stat_card(f"{memory['mean_retrievability']:.0f}%", "Avg. Retrievability",
                               color=COLORS['success'] if memory['mean_retrievability'] >= 80 else COLORS['warning'])
            ], style={'flex': '1', 'padding': '0 10px'}),
        ], style={'display': 'flex', 'marginBottom': '20px'}),
    ])

    return overview_div, banner


# ---------------------------------------------------------------------------
# Callback: Load UI from localStorage
# ---------------------------------------------------------------------------

@callback(
    [
        Output('session-time-range', 'value'),
        Output('retrievability-filter', 'value'),
        Output('difficulty-filter', 'value')
    ],
    [Input('url', 'pathname')],
    [State('ui-store', 'data')],
    prevent_initial_call=False
)
def load_ui_from_store(_, ui_store):
    """Load UI preferences from local storage on page load or tab switch."""
    defaults = {
        'session_time_range': 'all',
        'retrievability_filter': [0, 100],
        'difficulty_filter': [0, 10]
    }

    if not ui_store:
        ui_store = defaults

    session = ui_store.get('session_time_range', defaults['session_time_range'])
    retr = ui_store.get('retrievability_filter', defaults['retrievability_filter'])
    diff = ui_store.get('difficulty_filter', defaults['difficulty_filter'])

    backup = ui_store.get('data_backup')
    if backup:
        set_active_date(backup)

    return session, retr, diff


# ---------------------------------------------------------------------------
# Callback: Toggle x-axis mode
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
    """Toggle between dates and sessions x-axis mode. Restores from ui-store on page load."""
    active_style = {
        'padding': '6px 16px',
        'border': '1px solid ' + COLORS['primary'],
        'backgroundColor': COLORS['primary'],
        'color': 'white',
        'cursor': 'pointer',
        'fontSize': '13px',
        'fontWeight': '500'
    }
    inactive_style = {
        'padding': '6px 16px',
        'border': '1px solid #ddd',
        'backgroundColor': 'white',
        'color': '#333',
        'cursor': 'pointer',
        'fontSize': '13px',
        'fontWeight': '500'
    }

    triggered = ctx.triggered_id

    if triggered == 'url' or not triggered:
        mode = (ui_store or {}).get('xaxis_mode', 'dates')
        if mode == 'dates':
            return 'dates', {**active_style, 'borderRadius': '4px 0 0 4px'}, {**inactive_style, 'borderRadius': '0 4px 4px 0', 'borderLeft': 'none'}
        else:
            return 'sessions', {**inactive_style, 'borderRadius': '4px 0 0 4px'}, {**active_style, 'borderRadius': '0 4px 4px 0', 'borderLeft': 'none'}

    if ctx.triggered_id == 'xaxis-dates-btn':
        return 'dates', {**active_style, 'borderRadius': '4px 0 0 4px'}, {**inactive_style, 'borderRadius': '0 4px 4px 0', 'borderLeft': 'none'}
    else:
        return 'sessions', {**inactive_style, 'borderRadius': '4px 0 0 4px'}, {**active_style, 'borderRadius': '0 4px 4px 0', 'borderLeft': 'none'}


# ---------------------------------------------------------------------------
# Callback: Refresh data folder dropdown
# ---------------------------------------------------------------------------

@callback(
    Output('data-folder-dropdown', 'options'),
    [Input('url', 'pathname')]
)
def refresh_data_folder_dropdown(_):
    """Refresh the dropdown options from the filesystem on page load."""
    dates = get_config_available_dates()
    return [{'label': d, 'value': d} for d in dates]


# ---------------------------------------------------------------------------
# Callback: Save UI preferences
# ---------------------------------------------------------------------------

@callback(
    Output('ui-store', 'data'),
    [
        Input('session-time-range', 'value'),
        Input('xaxis-mode', 'data'),
        Input('retrievability-filter', 'value'),
        Input('difficulty-filter', 'value')
    ],
    prevent_initial_call=False
)
def save_ui_to_store(session_value, xaxis_value, retr_value, diff_value):
    """Persist UI preferences to local storage whenever any preference changes."""
    current_store = ctx.states.get('ui-store.data', {}) if hasattr(ctx, 'states') else {}

    return {
        'session_time_range': session_value or 'all',
        'xaxis_mode': xaxis_value or 'dates',
        'retrievability_filter': retr_value or [0, 100],
        'difficulty_filter': diff_value or [0, 10],
        'data_backup': current_store.get('data_backup', get_active_date())
    }


# ---------------------------------------------------------------------------
# Callback: Save data backup selection
# ---------------------------------------------------------------------------

@callback(
    Output('ui-store', 'data', allow_duplicate=True),
    [Input('data-folder-dropdown', 'value')],
    prevent_initial_call=True
)
def save_data_backup_to_store(backup_value):
    """Persist data backup selection separately to avoid circular dependencies."""
    current_store = ctx.states.get('ui-store.data', {}) if hasattr(ctx, 'states') else {}

    return {
        'session_time_range': current_store.get('session_time_range', 'all'),
        'xaxis_mode': current_store.get('xaxis_mode', 'dates'),
        'retrievability_filter': current_store.get('retrievability_filter', [0, 100]),
        'difficulty_filter': current_store.get('difficulty_filter', [0, 10]),
        'data_backup': backup_value or get_active_date()
    }


# ---------------------------------------------------------------------------
# Callback: Handle backup file upload
# ---------------------------------------------------------------------------

@callback(
    [
        Output('upload-status-message', 'children'),
        Output('upload-status-message', 'style'),
        Output('data-folder-dropdown', 'options', allow_duplicate=True),
        Output('data-folder-dropdown', 'value', allow_duplicate=True),
        Output('upload-message-interval', 'disabled'),
        Output('upload-message-interval', 'n_intervals'),
    ],
    [Input('upload-backup-button', 'contents')],
    [
        State('upload-backup-button', 'filename'),
    ],
    prevent_initial_call=True
)
def handle_backup_upload(contents, filename):
    """
    Process uploaded .apkg file: validate, extract, decompress, and add to backups.
    """
    if not contents:
        return "", {'display': 'none'}, [], None, True, 0

    # Validate file extension
    if not filename or not filename.lower().endswith('.apkg'):
        error_style = {
            'display': 'block',
            'padding': '8px 12px',
            'backgroundColor': '#f8d7da',
            'color': '#721c24',
            'borderRadius': '4px',
            'fontSize': '13px',
            'marginTop': '10px'
        }
        return "❌ Invalid file format. Please upload an .apkg file.", error_style, [], None, False, 0

    try:
        # Decode base64 contents
        content_type, content_string = contents.split(',')
        file_bytes = base64.b64decode(content_string)

        # Get project root and data directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(script_dir)
        data_dir = os.path.join(project_dir, 'data')

        # Process upload
        success, message, folder_name = process_apkg_upload(file_bytes, data_dir)

        if success:
            # Update active date
            set_active_date(folder_name)

            # Refresh dropdown options
            dates = get_config_available_dates()
            options = [{'label': d, 'value': d} for d in dates]

            success_style = {
                'display': 'block',
                'padding': '8px 12px',
                'backgroundColor': '#d4edda',
                'color': '#155724',
                'borderRadius': '4px',
                'fontSize': '13px',
                'marginTop': '10px'
            }
            return f"✅ {message}", success_style, options, folder_name, False, 0
        else:
            error_style = {
                'display': 'block',
                'padding': '8px 12px',
                'backgroundColor': '#f8d7da',
                'color': '#721c24',
                'borderRadius': '4px',
                'fontSize': '13px',
                'marginTop': '10px'
            }
            return f"❌ {message}", error_style, [], None, False, 0

    except Exception as e:
        error_style = {
            'display': 'block',
            'padding': '8px 12px',
            'backgroundColor': '#f8d7da',
            'color': '#721c24',
            'borderRadius': '4px',
            'fontSize': '13px',
            'marginTop': '10px'
        }
        return f"❌ Upload error: {str(e)}", error_style, [], None, False, 0


# ---------------------------------------------------------------------------# Callback: Auto-dismiss upload message
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
    return {'display': 'none'}, True


# ---------------------------------------------------------------------------# Callback: Update session charts
# ---------------------------------------------------------------------------

@callback(
    [
        Output('session-volume-summary', 'children'),
        Output('session-volume-charts', 'children'),
        Output('session-effectiveness-summary', 'children'),
        Output('session-effectiveness-charts', 'children'),
        Output('session-workload-summary', 'children'),
        Output('session-workload-charts', 'children'),
    ],
    [Input('session-time-range', 'value'),
     Input('xaxis-mode', 'data'),
     Input('data-folder-dropdown', 'value')],
    [State('ui-store', 'data')],
    prevent_initial_call=False
)
def update_session_charts(time_range, xaxis_mode, selected_date, ui_store):
    """Update session charts based on time range selection, x-axis mode, and selected data folder"""
    if selected_date:
        set_active_date(selected_date)
    elif not get_active_date():
        dates = get_config_available_dates()
        if dates:
            set_active_date(dates[0])

    use_sessions = (xaxis_mode == 'sessions')
    review_days, year_filter = parse_time_range(time_range)

    session_df = get_session_data(review_days, year_filter)
    hourly_df = get_hourly_stats(review_days, year_filter)
    daily_df = get_daily_reviews(review_days, year_filter)
    interval_df = get_review_intervals(review_days, year_filter)

    empty_msg = html.Div("No session data available for the selected time range.",
                        style={'textAlign': 'center', 'padding': '30px', 'color': '#666'})

    if session_df.empty:
        return empty_msg, [], empty_msg, [], empty_msg, []

    # Get summary statistics
    session_stats = get_session_summary_stats(review_days, year_filter)
    workload_stats = get_workload_summary()

    # Section 1: Study Volume & Consistency
    volume_summary = html.Div([
        html.Div([
            create_stat_card(f"{session_stats['weekly_velocity']:.0f}", "Avg Daily Reviews", COLORS['primary']),
        ], style={'flex': '1', 'padding': '0 10px'}),
        html.Div([
            create_stat_card(f"{session_stats['current_streak']}", "Current Streak", COLORS['success']),
        ], style={'flex': '1', 'padding': '0 10px'}),
        html.Div([
            create_stat_card(
                f"{session_stats['best_hour']}:00" if session_stats['best_hour'] is not None else "N/A",
                "Best Study Hour",
                COLORS['info']
            ),
        ], style={'flex': '1', 'padding': '0 10px'}),
    ], style={'display': 'flex', 'marginBottom': '16px'})

    volume_charts = html.Div([
        html.Div([
            dcc.Graph(
                figure=create_daily_reviews_chart(daily_df, use_sessions=use_sessions),
                config={'displayModeBar': False}
            )
        ], style={'flex': '2', 'padding': '0 10px'}),
        html.Div([
            dcc.Graph(
                figure=create_hourly_chart(hourly_df),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),
    ], style={'display': 'flex'})

    # Section 2: Learning Effectiveness
    trend_indicator = "↑" if session_stats['trend'] == 'up' else ("↓" if session_stats['trend'] == 'down' else "→")
    trend_color = COLORS['success'] if session_stats['trend'] == 'up' else (COLORS['danger'] if session_stats['trend'] == 'down' else COLORS['info'])

    effectiveness_summary = html.Div([
        html.Div([
            create_stat_card(f"{session_stats['avg_success_rate']:.0f}%", "Avg Success Rate",
                           COLORS['success'] if session_stats['avg_success_rate'] >= 85 else COLORS['warning']),
        ], style={'flex': '1', 'padding': '0 10px'}),
        html.Div([
            create_stat_card(trend_indicator, "Trend (vs last week)", trend_color),
        ], style={'flex': '1', 'padding': '0 10px'}),
        html.Div([
            create_stat_card(f"{session_stats['avg_session_size']:.0f}", "Avg Session Size", COLORS['primary']),
        ], style={'flex': '1', 'padding': '0 10px'}),
    ], style={'display': 'flex', 'marginBottom': '16px'})

    effectiveness_charts = html.Div([
        html.Div([
            dcc.Graph(
                figure=create_success_rate_chart(session_df, use_sessions=use_sessions),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),
        html.Div([
            dcc.Graph(
                figure=create_efficiency_chart(session_df, use_sessions=use_sessions),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),
        html.Div([
            dcc.Graph(
                figure=create_memory_decay_chart(interval_df),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),
    ], style={'display': 'flex'})

    # Section 3: Workload Forecast
    peak_day_str = workload_stats['peak_day'].strftime('%b %d') if workload_stats['peak_day'] else "N/A"

    workload_summary = html.Div([
        html.Div([
            create_stat_card(f"{workload_stats['due_this_week']}", "Due This Week", COLORS['primary']),
        ], style={'flex': '1', 'padding': '0 10px'}),
        html.Div([
            create_stat_card(f"{workload_stats['overdue_cards']}", "Overdue Cards",
                           COLORS['danger'] if workload_stats['overdue_cards'] > 0 else COLORS['success']),
        ], style={'flex': '1', 'padding': '0 10px'}),
        html.Div([
            create_stat_card(f"{peak_day_str} ({workload_stats['peak_day_count']})", "Peak Day Ahead", COLORS['warning']),
        ], style={'flex': '1', 'padding': '0 10px'}),
    ], style={'display': 'flex', 'marginBottom': '16px'})

    workload_charts = html.Div([
        html.Div([
            dcc.Graph(
                figure=create_future_load_chart(60),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),
    ], style={'display': 'flex'})

    return (
        volume_summary, volume_charts,
        effectiveness_summary, effectiveness_charts,
        workload_summary, workload_charts
    )


# ---------------------------------------------------------------------------
# Callback: Update card charts
# ---------------------------------------------------------------------------

@callback(
    [
        Output('card-knowledge-summary', 'children'),
        Output('card-knowledge-charts', 'children'),
        Output('card-maturity-summary', 'children'),
        Output('card-maturity-charts', 'children'),
        Output('card-problem-summary', 'children'),
        Output('card-problem-charts', 'children'),
    ],
    [Input('retrievability-filter', 'value'),
     Input('difficulty-filter', 'value'),
     Input('data-folder-dropdown', 'value')],
    [State('ui-store', 'data')],
    prevent_initial_call=False
)
def update_card_charts(ret_range, diff_range, selected_date, ui_store):
    """Update card charts based on filters and selected data folder"""
    if selected_date:
        set_active_date(selected_date)
    elif not get_active_date():
        dates = get_config_available_dates()
        if dates:
            set_active_date(dates[0])

    cards_df = get_card_data()

    empty_msg = html.Div("No card data available.",
                        style={'textAlign': 'center', 'padding': '30px', 'color': '#666'})

    if cards_df.empty:
        return empty_msg, [], empty_msg, [], empty_msg, []

    # Apply filters
    mask = (
        (cards_df['retrievability'] >= ret_range[0]) &
        (cards_df['retrievability'] <= ret_range[1]) &
        (cards_df['difficulty'] >= diff_range[0]) &
        (cards_df['difficulty'] <= diff_range[1])
    )
    filtered_df = cards_df[mask]

    # Get summary statistics
    health_stats = get_knowledge_health_stats()
    leech_df = get_leech_candidates()

    # Section 1: Current Knowledge State
    knowledge_summary = html.Div([
        html.Div([
            create_stat_card(f"{health_stats['health_score']:.0f}%", "Health Score",
                           COLORS['success'] if health_stats['health_score'] >= 70 else COLORS['warning']),
        ], style={'flex': '1', 'padding': '0 10px'}),
        html.Div([
            create_stat_card(f"{health_stats['cards_needing_attention']}", "Need Attention",
                           COLORS['danger'] if health_stats['cards_needing_attention'] > 10 else COLORS['warning']),
        ], style={'flex': '1', 'padding': '0 10px'}),
        html.Div([
            create_stat_card(f"{health_stats['median_retrievability']:.0f}%", "Median Retrievability", COLORS['info']),
        ], style={'flex': '1', 'padding': '0 10px'}),
    ], style={'display': 'flex', 'marginBottom': '16px'})

    knowledge_charts = html.Div([
        html.Div([
            dcc.Graph(
                figure=create_memory_state_chart(cards_df),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),
        html.Div([
            dcc.Graph(
                figure=create_retrievability_distribution_chart(filtered_df),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),
    ], style={'display': 'flex'})

    # Section 2: Collection Maturity
    maturity_summary = html.Div([
        html.Div([
            create_stat_card(f"{health_stats['avg_stability']:.0f}d", "Avg Stability", COLORS['primary']),
        ], style={'flex': '1', 'padding': '0 10px'}),
        html.Div([
            create_stat_card(f"{health_stats['mature_cards_pct']:.0f}%", "Mature Cards (>30d)", COLORS['success']),
        ], style={'flex': '1', 'padding': '0 10px'}),
        html.Div([
            create_stat_card(f"{len(filtered_df):,}", "Cards Shown", COLORS['info']),
        ], style={'flex': '1', 'padding': '0 10px'}),
    ], style={'display': 'flex', 'marginBottom': '16px'})

    maturity_charts = html.Div([
        html.Div([
            dcc.Graph(
                figure=create_stability_distribution_chart(filtered_df),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),
        html.Div([
            dcc.Graph(
                figure=create_difficulty_distribution_chart(filtered_df),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),
        html.Div([
            dcc.Graph(
                figure=create_reviews_stability_chart(filtered_df),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),
    ], style={'display': 'flex'})

    # Section 3: Problem Areas
    problem_summary = html.Div([
        html.Div([
            create_stat_card(f"{health_stats['leech_count']}", "Leech Cards (3+ lapses)",
                           COLORS['danger'] if health_stats['leech_count'] > 10 else COLORS['warning']),
        ], style={'flex': '1', 'padding': '0 10px'}),
        html.Div([
            create_stat_card(f"{filtered_df['lapses'].sum():,}", "Total Lapses", COLORS['danger']),
        ], style={'flex': '1', 'padding': '0 10px'}),
        html.Div([
            create_stat_card(f"{filtered_df['difficulty'].mean():.1f}", "Avg Difficulty", COLORS['info']),
        ], style={'flex': '1', 'padding': '0 10px'}),
    ], style={'display': 'flex', 'marginBottom': '16px'})

    problem_charts = html.Div([
        html.Div([
            dcc.Graph(
                figure=create_lapses_chart(filtered_df),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),
        html.Div([
            dcc.Graph(
                figure=create_leech_chart(leech_df),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),
    ], style={'display': 'flex'})

    return (
        knowledge_summary, knowledge_charts,
        maturity_summary, maturity_charts,
        problem_summary, problem_charts
    )

