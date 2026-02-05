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
    create_time_per_card_chart,
    create_session_scatter_chart,
    create_memory_decay_chart,
    create_future_load_chart,
    create_daily_load_contribution_chart,
    create_load_contribution_distribution_chart,
)
from .charts_card import (
    create_memory_state_chart,
    create_retrievability_distribution_chart,
    create_stability_distribution_chart,
    create_difficulty_distribution_chart,
    create_stability_retrievability_chart,
    create_difficulty_retrievability_chart,
    create_lapses_chart,
    create_reviews_stability_chart,
    create_time_spent_chart,
    create_reviews_distribution_chart,
)
from .data_loader import (
    get_session_data,
    get_hourly_stats,
    get_daily_reviews,
    get_review_intervals,
    get_card_data,
    get_total_time_per_card,
    get_overview_stats,
    get_memory_state_summary,
)
from anki_config import (
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
    Output('session-charts', 'children'),
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

    if session_df.empty:
        return html.Div("No session data available for the selected time range.",
                       style={'textAlign': 'center', 'padding': '50px', 'color': '#666'})

    charts = []

    # Row 1: Session Overview
    charts.append(html.Div([
        html.Div([
            dcc.Graph(
                id='daily-reviews-graph',
                figure=create_daily_reviews_chart(daily_df, use_sessions=use_sessions),
                config={'displayModeBar': False}
            )
        ], style={'flex': '2', 'padding': '0 10px'}),
        html.Div([
            dcc.Graph(
                id='hourly-chart',
                figure=create_hourly_chart(hourly_df),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),
    ], style={'display': 'flex', 'marginBottom': '20px'}))

    # Row 2: Performance Metrics
    charts.append(html.Div([
        html.Div([
            dcc.Graph(
                id='success-rate-chart',
                figure=create_success_rate_chart(session_df, use_sessions=use_sessions),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),
        html.Div([
            dcc.Graph(
                id='efficiency-chart',
                figure=create_efficiency_chart(session_df, use_sessions=use_sessions),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),
    ], style={'display': 'flex', 'marginBottom': '20px'}))

    # Row 3: Time Analysis
    charts.append(html.Div([
        html.Div([
            dcc.Graph(
                figure=create_time_per_card_chart(session_df),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),
        html.Div([
            dcc.Graph(
                figure=create_session_scatter_chart(session_df),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),
        html.Div([
            dcc.Graph(
                figure=create_memory_decay_chart(interval_df),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),
    ], style={'display': 'flex', 'marginBottom': '20px'}))

    # Row 4: Load Analysis
    charts.append(html.Div([
        html.Div([
            dcc.Graph(
                figure=create_future_load_chart(60),
                config={'displayModeBar': False}
            )
        ], style={'flex': '2', 'padding': '0 10px'}),
        html.Div([
            dcc.Graph(
                figure=create_daily_load_contribution_chart(),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),
    ], style={'display': 'flex', 'marginBottom': '20px'}))

    # Row 5: Load Distribution & Performance
    charts.append(html.Div([
        html.Div([
            dcc.Graph(
                figure=create_load_contribution_distribution_chart(),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),
    ], style={'display': 'flex', 'marginBottom': '20px'}))

    return charts


# ---------------------------------------------------------------------------
# Callback: Update card charts
# ---------------------------------------------------------------------------

@callback(
    Output('card-charts', 'children'),
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
    time_df = get_total_time_per_card()

    if cards_df.empty:
        return html.Div("No card data available.",
                       style={'textAlign': 'center', 'padding': '50px', 'color': '#666'})

    # Apply filters
    mask = (
        (cards_df['retrievability'] >= ret_range[0]) &
        (cards_df['retrievability'] <= ret_range[1]) &
        (cards_df['difficulty'] >= diff_range[0]) &
        (cards_df['difficulty'] <= diff_range[1])
    )
    filtered_df = cards_df[mask]

    # Summary stats for filtered cards
    summary = html.Div([
        html.Div([
            create_stat_card(f"{len(filtered_df):,}", "Cards Shown", COLORS['primary']),
        ], style={'flex': '1', 'padding': '0 10px'}),
        html.Div([
            create_stat_card(f"{filtered_df['retrievability'].mean():.0f}%", "Avg Retrievability",
                           COLORS['success'] if filtered_df['retrievability'].mean() >= 80 else COLORS['warning']),
        ], style={'flex': '1', 'padding': '0 10px'}),
        html.Div([
            create_stat_card(f"{filtered_df['difficulty'].mean():.1f}", "Avg Difficulty"),
        ], style={'flex': '1', 'padding': '0 10px'}),
        html.Div([
            create_stat_card(f"{filtered_df['stability'].median():.0f}d", "Median Stability"),
        ], style={'flex': '1', 'padding': '0 10px'}),
        html.Div([
            create_stat_card(f"{filtered_df['lapses'].sum():,}", "Total Lapses", COLORS['danger']),
        ], style={'flex': '1', 'padding': '0 10px'}),
    ], style={'display': 'flex', 'marginBottom': '20px'})

    charts = [summary]

    # Row 1: Memory State & Distribution
    charts.append(html.Div([
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
    ], style={'display': 'flex', 'marginBottom': '20px'}))

    # Row 2: Correlations
    charts.append(html.Div([
        html.Div([
            dcc.Graph(
                figure=create_stability_retrievability_chart(filtered_df),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),
        html.Div([
            dcc.Graph(
                figure=create_difficulty_retrievability_chart(filtered_df),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),
        html.Div([
            dcc.Graph(
                figure=create_lapses_chart(filtered_df),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),
    ], style={'display': 'flex', 'marginBottom': '20px'}))

    # Row 3: Learning Progress
    charts.append(html.Div([
        html.Div([
            dcc.Graph(
                figure=create_reviews_stability_chart(filtered_df),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),
        html.Div([
            dcc.Graph(
                figure=create_time_spent_chart(time_df),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),
        html.Div([
            dcc.Graph(
                figure=create_reviews_distribution_chart(filtered_df),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),
    ], style={'display': 'flex', 'marginBottom': '20px'}))

    return charts
