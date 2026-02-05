#!/usr/bin/env python3
"""
Interactive Anki Learning Dashboard
A comprehensive dashboard for analyzing your Anki learning journey using Plotly Dash
"""

import dash
from dash import dcc, html, Input, Output, State, callback
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# Import data loader robustly so this module works both when run as a script
# (python dashboard/app.py) and when imported as a package (import dashboard.app)
try:
    # Preferred when running as a package
    from .data_loader import (
        get_session_data,
        get_hourly_stats,
        get_daily_reviews,
        get_review_intervals,
        get_card_data,
        get_total_time_per_card,
        get_overview_stats,
        get_memory_state_summary,
        calculate_daily_load,
        get_daily_load_by_stability,
        get_future_load_forecast
    )
except Exception:
    # Fallback for script execution: add project root to sys.path and import absolutely
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from data_loader import (
        get_session_data,
        get_hourly_stats,
        get_daily_reviews,
        get_review_intervals,
        get_card_data,
        get_total_time_per_card,
        get_overview_stats,
        get_memory_state_summary,
        calculate_daily_load,
        get_daily_load_by_stability,
        get_future_load_forecast
    )

# Color palette
COLORS = {
    'primary': '#667eea',
    'secondary': '#764ba2',
    'success': '#06d6a0',
    'warning': '#ffd166',
    'danger': '#ef476f',
    'info': '#118ab2',
    'dark': '#073b4c',
    'light': '#f8f9fa',
    'critical': '#C73E1D',
    'at_risk': '#F18F01',
    'moderate': '#FFD23F',
    'good': '#06A77D',
    'excellent': '#0FA3B1',
}

# Memory state colors
MEMORY_COLORS = {
    'Critical (<50%)': COLORS['critical'],
    'At Risk (50-70%)': COLORS['at_risk'],
    'Moderate (70-85%)': COLORS['moderate'],
    'Good (85-95%)': COLORS['good'],
    'Excellent (95%+)': COLORS['excellent'],
}





# Initialize the Dash app
import os, sys
# Ensure project root is importable for anki_config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from anki_config import get_active_date, get_available_dates as get_config_available_dates, set_active_date

DATE_OPTIONS = [{'label': d, 'value': d} for d in get_config_available_dates()]
ACTIVE_DATE = get_active_date()

app = dash.Dash(
    __name__,
    title="Anki Learning Dashboard",
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}]
)

# Custom CSS
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                margin: 0;
            }
            .main-container {
                max-width: 1600px;
                margin: 0 auto;
                padding: 20px;
            }
            .header {
                text-align: center;
                color: white;
                padding: 20px 0;
            }
            .header h1 {
                margin: 0;
                font-size: 2.5rem;
                font-weight: 700;
            }
            .header p {
                margin: 10px 0 0;
                opacity: 0.9;
            }
            .stat-card {
                background: white;
                border-radius: 12px;
                padding: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                text-align: center;
            }
            .stat-value {
                font-size: 2rem;
                font-weight: 700;
                color: #667eea;
            }
            .stat-label {
                color: #666;
                font-size: 0.9rem;
                margin-top: 5px;
            }
            .card {
                background: white;
                border-radius: 12px;
                padding: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }
            .tabs-container {
                background: white;
                border-radius: 12px;
                padding: 0;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                overflow: hidden;
            }
            .custom-tabs {
                border-bottom: 2px solid #eee;
            }
            .custom-tab {
                padding: 15px 30px !important;
                font-weight: 600 !important;
            }
            .custom-tab--selected {
                border-top: none !important;
                border-left: none !important;
                border-right: none !important;
                border-bottom: 3px solid #667eea !important;
                color: #667eea !important;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''


def create_stat_card(value, label, color=COLORS['primary']):
    """Create a statistic card component"""
    return html.Div([
        html.Div(value, className='stat-value', style={'color': color}),
        html.Div(label, className='stat-label')
    ], className='stat-card')


@callback(
    [Output('overview-container', 'children'), Output('active-date-banner', 'children')],
    [Input('data-folder-dropdown', 'value')],
    [State('ui-store', 'data')],
    prevent_initial_call=False
)
def update_overview_container(selected_date, ui_store):
    """Dynamically populate the overview statistics section when the selected data folder changes."""
    banner = ''
    # Use active date from config if selected_date is None
    if selected_date:
        # Update the active date in the config
        set_active_date(selected_date)
        banner = f"Active backup: {selected_date}"
    elif not get_active_date():
        # Fallback if no date is set at all
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

    # Return a tuple matching the two Outputs: (overview children, banner text)
    return overview_div, banner


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
    """Load UI preferences from local storage on page load or tab switch.
    Triggered by URL changes (page load/tab switch), reads from ui-store as State.
    Note: data-folder-dropdown is initialized from ACTIVE_DATE and controlled by user input + save callback.
    Note: xaxis-mode is loaded by toggle_xaxis_mode callback to avoid duplicate outputs."""
    # Default values
    defaults = {
        'session_time_range': 'all',
        'retrievability_filter': [0, 100],
        'difficulty_filter': [0, 10]
    }

    if not ui_store:
        ui_store = defaults

    # Extract values with fallbacks
    session = ui_store.get('session_time_range', defaults['session_time_range'])
    retr = ui_store.get('retrievability_filter', defaults['retrievability_filter'])
    diff = ui_store.get('difficulty_filter', defaults['difficulty_filter'])

    # Sync server-side state with stored backup selection if available
    backup = ui_store.get('data_backup')
    if backup:
        set_active_date(backup)

    return session, retr, diff


# =============================================================================
# SESSION TAB CONTENT
# =============================================================================

def create_session_tab():
    """Create the session analytics tab content"""
    # Generate year options dynamically based on current date
    from datetime import datetime
    current_year = datetime.now().year
    # Include years from 2020 to last year (current year is covered by recent options)
    year_options = [
        {'label': f'Year {year}', 'value': f'year_{year}'}
        for year in range(current_year - 1, 2019, -1)
    ]

    return html.Div([
        # Controls
        html.Div([
            html.Div([
                html.Label("Time Range:", style={'fontWeight': '600', 'marginRight': '10px'}),
                dcc.Dropdown(
                    id='session-time-range',
                    options=[
                        {'label': 'Last 7 days', 'value': '7'},
                        {'label': 'Last 30 days', 'value': '30'},
                        {'label': 'Last 90 days', 'value': '90'},
                        {'label': 'Last 180 days', 'value': '180'},
                        {'label': 'All time', 'value': 'all'},
                    ] + year_options,
                    value='all',
                    clearable=False,
                    style={'width': '180px'}
                ),
            ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '40px'}),
            html.Div([
                html.Label("X-Axis:", style={'fontWeight': '600', 'marginRight': '10px'}),
                html.Div([
                    html.Button(
                        "Dates",
                        id='xaxis-dates-btn',
                        n_clicks=0,
                        style={
                            'padding': '6px 16px',
                            'border': '1px solid #ddd',
                            'borderRadius': '4px 0 0 4px',
                            'backgroundColor': COLORS['primary'],
                            'color': 'white',
                            'cursor': 'pointer',
                            'fontSize': '13px',
                            'fontWeight': '500'
                        }
                    ),
                    html.Button(
                        "Sessions",
                        id='xaxis-sessions-btn',
                        n_clicks=0,
                        style={
                            'padding': '6px 16px',
                            'border': '1px solid #ddd',
                            'borderLeft': 'none',
                            'borderRadius': '0 4px 4px 0',
                            'backgroundColor': 'white',
                            'color': '#333',
                            'cursor': 'pointer',
                            'fontSize': '13px',
                            'fontWeight': '500'
                        }
                    ),
                ], style={'display': 'flex'}),
            ], style={'display': 'flex', 'alignItems': 'center'}),
            # Hidden store for xaxis mode (persistent)
            dcc.Store(id='xaxis-mode', data='dates', storage_type='local'),
            # Store to persist ALL UI preferences across reloads and tab switches
            dcc.Store(id='ui-store', storage_type='local', data={
                'session_time_range': 'all',
                'xaxis_mode': 'dates',
                'retrievability_filter': [0, 100],
                'difficulty_filter': [0, 10],
                'data_backup': get_active_date()
            }),
        ], style={'padding': '20px', 'borderBottom': '1px solid #eee', 'display': 'flex', 'alignItems': 'center'}),

        # Session charts
        html.Div(id='session-charts', style={'padding': '20px'})
    ])


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
    from dash import ctx

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

    # If triggered by url (page load), restore mode from stored data
    if triggered == 'url' or not triggered:
        mode = (ui_store or {}).get('xaxis_mode', 'dates')
        if mode == 'dates':
            return 'dates', {**active_style, 'borderRadius': '4px 0 0 4px'}, {**inactive_style, 'borderRadius': '0 4px 4px 0', 'borderLeft': 'none'}
        else:
            return 'sessions', {**inactive_style, 'borderRadius': '4px 0 0 4px'}, {**active_style, 'borderRadius': '0 4px 4px 0', 'borderLeft': 'none'}

    # Otherwise, determine mode from button clicks
    if ctx.triggered_id == 'xaxis-dates-btn':
        return 'dates', {**active_style, 'borderRadius': '4px 0 0 4px'}, {**inactive_style, 'borderRadius': '0 4px 4px 0', 'borderLeft': 'none'}
    else:
        return 'sessions', {**inactive_style, 'borderRadius': '4px 0 0 4px'}, {**active_style, 'borderRadius': '0 4px 4px 0', 'borderLeft': 'none'}


@callback(
    Output('data-folder-dropdown', 'options'),
    [Input('url', 'pathname')]
)
def refresh_data_folder_dropdown(_):
    """Refresh the dropdown options from the filesystem on page load."""
    dates = get_config_available_dates()
    options = [{'label': d, 'value': d} for d in dates]
    return options


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
    """Persist UI preferences to local storage whenever any preference changes.
    Note: data_backup is persisted separately to avoid circular dependencies."""
    from dash import ctx

    # Get current ui-store data to preserve data_backup
    current_store = ctx.states.get('ui-store.data', {}) if hasattr(ctx, 'states') else {}

    return {
        'session_time_range': session_value or 'all',
        'xaxis_mode': xaxis_value or 'dates',
        'retrievability_filter': retr_value or [0, 100],
        'difficulty_filter': diff_value or [0, 10],
        'data_backup': current_store.get('data_backup', get_active_date())
    }


@callback(
    Output('ui-store', 'data', allow_duplicate=True),
    [Input('data-folder-dropdown', 'value')],
    prevent_initial_call=True
)
def save_data_backup_to_store(backup_value):
    """Persist data backup selection separately to avoid circular dependencies."""
    from dash import ctx

    # Get current ui-store data to preserve other settings
    current_store = ctx.states.get('ui-store.data', {}) if hasattr(ctx, 'states') else {}

    # Update only the data_backup field
    updated_store = {
        'session_time_range': current_store.get('session_time_range', 'all'),
        'xaxis_mode': current_store.get('xaxis_mode', 'dates'),
        'retrievability_filter': current_store.get('retrievability_filter', [0, 100]),
        'difficulty_filter': current_store.get('difficulty_filter', [0, 10]),
        'axis_x_scale': current_store.get('axis_x_scale', 'linear'),
        'axis_y_scale': current_store.get('axis_y_scale', 'linear'),
        'data_backup': backup_value or get_active_date()
    }

    return updated_store


def parse_time_range(time_range):
    """Parse time range value into review_days and year_filter."""
    if time_range == 'all':
        return None, None
    elif isinstance(time_range, str) and time_range.startswith('year_'):
        return None, int(time_range.split('_')[1])
    else:
        return int(time_range) if time_range else None, None


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

    # Update the active date in config so data_loader uses the correct database
    # Use active date from config if selected_date is None
    if selected_date:
        set_active_date(selected_date)
    elif not get_active_date():
        # Fallback if no date is set at all
        dates = get_config_available_dates()
        if dates:
            set_active_date(dates[0])

    use_sessions = (xaxis_mode == 'sessions')

    # Parse time range value
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
        # Daily reviews over time
        html.Div([
            dcc.Graph(
                id='daily-reviews-graph',
                figure=create_daily_reviews_chart(daily_df, use_sessions=use_sessions),
                config={'displayModeBar': False}
            )
        ], style={'flex': '2', 'padding': '0 10px'}),

        # Hour of day analysis
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
        # Success rate over time
        html.Div([
            dcc.Graph(
                id='success-rate-chart',
                figure=create_success_rate_chart(session_df, use_sessions=use_sessions),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),

        # Session efficiency
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
        # Time per card distribution
        html.Div([
            dcc.Graph(
                figure=create_time_per_card_chart(session_df),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),

        # Session duration vs cards
        html.Div([
            dcc.Graph(
                figure=create_session_scatter_chart(session_df),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),

        # Memory decay curve
        html.Div([
            dcc.Graph(
                figure=create_memory_decay_chart(interval_df),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),
    ], style={'display': 'flex', 'marginBottom': '20px'}))

    # Row 4: Load Analysis
    charts.append(html.Div([
        # Future load forecast
        html.Div([
            dcc.Graph(
                figure=create_future_load_chart(60),
                config={'displayModeBar': False}
            )
        ], style={'flex': '2', 'padding': '0 10px'}),

        # Daily load contribution
        html.Div([
            dcc.Graph(
                figure=create_daily_load_contribution_chart(),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),
    ], style={'display': 'flex', 'marginBottom': '20px'}))

    # Row 5: Load Distribution & Performance
    charts.append(html.Div([
        # Load contribution distribution
        html.Div([
            dcc.Graph(
                figure=create_load_contribution_distribution_chart(),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),
    ], style={'display': 'flex', 'marginBottom': '20px'}))

    return charts


def get_time_period_markers(df, date_col='date'):
    """
    Generate markers for year boundaries when using session-based x-axis.
    Returns a list of dicts with session index and label.
    """
    if df.empty:
        return []

    df_sorted = df.sort_values(date_col).reset_index(drop=True)
    markers = []
    last_year = None

    for idx, row in df_sorted.iterrows():
        date = pd.to_datetime(row[date_col])
        current_year = date.year

        # Check for year change
        if last_year is not None and current_year != last_year:
            label = str(current_year)
            markers.append({
                'index': idx,
                'label': label,
                'date': date
            })

        last_year = current_year

    return markers


def add_session_time_markers(fig, markers, y_position='bottom'):
    """Add vertical lines and annotations for year changes in session mode."""
    for marker in markers:
        fig.add_vline(
            x=marker['index'],
            line_dash="dot",
            line_color=COLORS['danger'],
            line_width=2,
            opacity=0.6
        )

        fig.add_annotation(
            x=marker['index'],
            y=1.02,
            yref='paper',
            text=marker['label'],
            showarrow=False,
            font=dict(size=11, color=COLORS['danger']),
            textangle=0
        )

    return fig


def create_daily_reviews_chart(df, use_sessions=False):
    """Create daily reviews line chart"""
    if df.empty:
        return go.Figure()

    fig = go.Figure()

    # Sort by date and reset index for session mode
    df_plot = df.sort_values('date').reset_index(drop=True)

    if use_sessions:
        # Session mode: use sequential index as x-axis
        x_values = df_plot.index
        hover_template = 'Session %{x}<br>%{customdata|%b %d, %Y}<br>Reviews: %{y}<extra></extra>'
        custom_data = df_plot['date']
        x_title = 'Session Number'
    else:
        # Date mode: use date as x-axis
        x_values = df_plot['date']
        hover_template = '%{x|%b %d, %Y}<br>Reviews: %{y}<extra></extra>'
        custom_data = None
        x_title = 'Date'

    # Add area for reviews
    fig.add_trace(go.Scatter(
        x=x_values,
        y=df_plot['daily_reviews'],
        mode='lines',
        fill='tozeroy',
        name='Reviews',
        line=dict(color=COLORS['primary'], width=2),
        fillcolor='rgba(102, 126, 234, 0.3)',
        customdata=custom_data,
        hovertemplate=hover_template
    ))

    # Add 7-day moving average
    if len(df_plot) >= 7:
        df_plot = df_plot.copy()
        df_plot['ma7'] = df_plot['daily_reviews'].rolling(window=7).mean()
        if use_sessions:
            hover_ma = 'Session %{x}<br>%{customdata|%b %d, %Y}<br>7-day avg: %{y:.0f}<extra></extra>'
        else:
            hover_ma = '%{x|%b %d, %Y}<br>7-day avg: %{y:.0f}<extra></extra>'
        fig.add_trace(go.Scatter(
            x=x_values,
            y=df_plot['ma7'],
            mode='lines',
            name='7-day avg',
            line=dict(color=COLORS['danger'], width=2, dash='dash'),
            customdata=custom_data,
            hovertemplate=hover_ma
        ))

    fig.update_layout(
        title='Daily Reviews Over Time',
        xaxis_title=x_title,
        yaxis_title='Number of Reviews',
        hovermode='x unified',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        margin=dict(l=40, r=40, t=80, b=40),
        plot_bgcolor='white',
        paper_bgcolor='white',
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#eee')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#eee')

    # Add time period markers in session mode
    if use_sessions:
        markers = get_time_period_markers(df_plot, 'date')
        fig = add_session_time_markers(fig, markers)

    return fig


def create_hourly_chart(df):
    """Create hour of day performance chart"""
    if df.empty:
        return go.Figure()

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=df['hour'],
            y=df['review_count'],
            name='Reviews',
            marker_color=COLORS['primary'],
            opacity=0.7,
            hovertemplate='Hour %{x}:00<br>Reviews: %{y}<extra></extra>'
        ),
        secondary_y=False
    )

    fig.add_trace(
        go.Scatter(
            x=df['hour'],
            y=df['success_rate'],
            name='Success Rate',
            line=dict(color=COLORS['success'], width=3),
            mode='lines+markers',
            hovertemplate='Hour %{x}:00<br>Success: %{y:.1f}%<extra></extra>'
        ),
        secondary_y=True
    )

    fig.update_layout(
        title='Performance by Hour of Day',
        xaxis_title='Hour',
        hovermode='x unified',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        margin=dict(l=40, r=40, t=60, b=40),
        plot_bgcolor='white',
        paper_bgcolor='white',
    )
    fig.update_xaxes(dtick=2, showgrid=True, gridwidth=1, gridcolor='#eee')
    fig.update_yaxes(title_text='Reviews', secondary_y=False, showgrid=True, gridwidth=1, gridcolor='#eee')
    fig.update_yaxes(title_text='Success Rate (%)', secondary_y=True, range=[0, 100])

    return fig


def create_success_rate_chart(df, use_sessions=False):
    """Create success rate over time chart"""
    if df.empty:
        return go.Figure()

    df_sorted = df.sort_values('date').reset_index(drop=True)

    # Calculate 7-session moving average
    df_sorted = df_sorted.copy()
    df_sorted['ma7'] = df_sorted['success_rate'].rolling(window=7, min_periods=1).mean()

    if use_sessions:
        x_values = df_sorted.index
        hover_main = 'Session %{x}<br>%{customdata|%b %d, %Y}<br>Success Rate: %{y:.1f}%<extra></extra>'
        hover_ma = 'Session %{x}<br>%{customdata|%b %d, %Y}<br>7-session avg: %{y:.1f}%<extra></extra>'
        custom_data = df_sorted['date']
        x_title = 'Session Number'
    else:
        x_values = df_sorted['date']
        hover_main = '%{x|%b %d, %Y}<br>Success Rate: %{y:.1f}%<extra></extra>'
        hover_ma = '%{x|%b %d, %Y}<br>7-session avg: %{y:.1f}%<extra></extra>'
        custom_data = None
        x_title = 'Date'

    fig = go.Figure()

    # Individual sessions
    fig.add_trace(go.Scatter(
        x=x_values,
        y=df_sorted['success_rate'],
        mode='markers',
        name='Session',
        marker=dict(
            size=8,
            color=df_sorted['success_rate'],
            colorscale='RdYlGn',
            cmin=60,
            cmax=100,
            line=dict(width=1, color='white')
        ),
        customdata=custom_data,
        hovertemplate=hover_main
    ))

    # Moving average
    fig.add_trace(go.Scatter(
        x=x_values,
        y=df_sorted['ma7'],
        mode='lines',
        name='7-session avg',
        line=dict(color=COLORS['primary'], width=2),
        customdata=custom_data,
        hovertemplate=hover_ma
    ))

    # Target line
    fig.add_hline(y=90, line_dash="dash", line_color=COLORS['success'],
                  annotation_text="Target 90%", annotation_position="right")

    fig.update_layout(
        title='Recall Rate Over Time',
        xaxis_title=x_title,
        yaxis_title='Success Rate (%)',
        yaxis_range=[50, 100],
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        margin=dict(l=40, r=40, t=80, b=40),
        plot_bgcolor='white',
        paper_bgcolor='white',
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#eee')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#eee')

    # Add time period markers in session mode
    if use_sessions:
        markers = get_time_period_markers(df_sorted, 'date')
        fig = add_session_time_markers(fig, markers)

    return fig


def create_efficiency_chart(df, use_sessions=False):
    """Create session efficiency chart"""
    if df.empty:
        return go.Figure()

    df_sorted = df.sort_values('date').reset_index(drop=True)

    if use_sessions:
        x_values = df_sorted.index
        hover_template = 'Session %{x}<br>%{customdata|%b %d, %Y}<br>Speed: %{y:.1f} cards/min<extra></extra>'
        custom_data = df_sorted['date']
        x_title = 'Session Number'
    else:
        x_values = df_sorted['date']
        hover_template = '%{x|%b %d, %Y}<br>Speed: %{y:.1f} cards/min<extra></extra>'
        custom_data = None
        x_title = 'Date'

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=x_values,
        y=df_sorted['cards_per_minute'],
        mode='lines+markers',
        name='Cards/min',
        line=dict(color=COLORS['info'], width=2),
        marker=dict(size=6),
        customdata=custom_data,
        hovertemplate=hover_template
    ))

    # Add average line
    avg_speed = df_sorted['cards_per_minute'].mean()
    fig.add_hline(y=avg_speed, line_dash="dash", line_color=COLORS['warning'],
                  annotation_text=f"Avg: {avg_speed:.1f}", annotation_position="right")

    fig.update_layout(
        title='Review Speed Over Time',
        xaxis_title=x_title,
        yaxis_title='Cards per Minute',
        margin=dict(l=40, r=40, t=80, b=40),
        plot_bgcolor='white',
        paper_bgcolor='white',
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#eee')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#eee')

    # Add time period markers in session mode
    if use_sessions:
        markers = get_time_period_markers(df_sorted, 'date')
        fig = add_session_time_markers(fig, markers)

    return fig


def create_time_per_card_chart(df):
    """Create time per card distribution chart"""
    if df.empty:
        return go.Figure()

    fig = go.Figure()

    fig.add_trace(go.Histogram(
        x=df['avg_time_per_card'],
        nbinsx=30,
        marker_color=COLORS['primary'],
        opacity=0.7,
        hovertemplate='Time: %{x:.1f}s<br>Sessions: %{y}<extra></extra>'
    ))

    median_time = df['avg_time_per_card'].median()
    fig.add_vline(x=median_time, line_dash="dash", line_color=COLORS['danger'],
                  annotation_text=f"Median: {median_time:.1f}s", annotation_position="top")

    fig.update_layout(
        title='Time per Card Distribution',
        xaxis_title='Seconds per Card',
        yaxis_title='Number of Sessions',
        margin=dict(l=40, r=40, t=60, b=40),
        plot_bgcolor='white',
        paper_bgcolor='white',
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#eee')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#eee')

    return fig


def create_session_scatter_chart(df):
    """Create session size vs duration scatter chart"""
    if df.empty:
        return go.Figure()

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df['total_cards'],
        y=df['total_session_minutes'],
        mode='markers',
        marker=dict(
            size=10,
            color=df['success_rate'],
            colorscale='RdYlGn',
            cmin=60,
            cmax=100,
            colorbar=dict(title='Success %'),
            line=dict(width=1, color='white')
        ),
        hovertemplate='Cards: %{x}<br>Duration: %{y:.1f} min<br>Success: %{marker.color:.1f}%<extra></extra>'
    ))

    fig.update_layout(
        title='Session Size vs Duration',
        xaxis_title='Cards Reviewed',
        yaxis_title='Session Duration (min)',
        margin=dict(l=40, r=40, t=60, b=40),
        plot_bgcolor='white',
        paper_bgcolor='white',
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#eee')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#eee')

    return fig


def create_memory_decay_chart(df):
    """Create memory decay curve chart"""
    if df.empty:
        return go.Figure()

    fig = go.Figure()

    # Ensure proper data types and filter valid data
    df_binned = df.copy()
    df_binned['interval_days'] = pd.to_numeric(df_binned['interval_days'], errors='coerce')
    df_binned['success_rate'] = pd.to_numeric(df_binned['success_rate'], errors='coerce')
    df_binned = df_binned.dropna(subset=['interval_days', 'success_rate'])

    if df_binned.empty or len(df_binned) < 2:
        return go.Figure()

    # Bin the data for cleaner visualization
    try:
        df_binned['interval_bin'] = pd.cut(df_binned['interval_days'].values, bins=min(50, len(df_binned)))
        df_agg = df_binned.groupby('interval_bin', observed=True).agg({
            'interval_days': 'mean',
            'success_rate': 'mean',
            'review_count': 'sum'
        }).dropna()
    except (ValueError, TypeError):
        # Fallback: use raw data if binning fails
        df_agg = df_binned

    if df_agg.empty:
        return go.Figure()

    fig.add_trace(go.Scatter(
        x=df_agg['interval_days'],
        y=df_agg['success_rate'],
        mode='markers+lines',
        marker=dict(size=8, color=COLORS['primary']),
        line=dict(color=COLORS['primary'], width=2),
        hovertemplate='Interval: %{x:.0f} days<br>Success: %{y:.1f}%<extra></extra>'
    ))

    # Target line
    fig.add_hline(y=90, line_dash="dash", line_color=COLORS['success'],
                  annotation_text="Target 90%", annotation_position="right")

    fig.update_layout(
        title='Memory Retention by Interval',
        xaxis_title='Days Since Last Review',
        yaxis_title='Success Rate (%)',
        yaxis_range=[0, 100],
        margin=dict(l=40, r=40, t=60, b=40),
        plot_bgcolor='white',
        paper_bgcolor='white',
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#eee')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#eee')

    return fig


def create_future_load_chart(days_ahead=60):
    """Create future review load forecast chart"""
    df = get_future_load_forecast(days_ahead)

    if df.empty:
        return go.Figure()

    fig = go.Figure()

    # Daily due counts
    fig.add_trace(go.Bar(
        x=df['date'],
        y=df['due_count'],
        name='Due Cards',
        marker=dict(
            color=df['due_count'],
            colorscale=[[0, COLORS['success']], [0.5, COLORS['warning']], [1, COLORS['danger']]],
            cmin=0,
            cmax=df['due_count'].quantile(0.95),
            showscale=False
        ),
        hovertemplate='%{x|%b %d}<br>Due: %{y} cards<extra></extra>'
    ))

    # 7-day moving average
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['ma7'],
        mode='lines',
        name='7-day avg',
        line=dict(color=COLORS['primary'], width=3),
        hovertemplate='%{x|%b %d}<br>Avg: %{y:.0f} cards<extra></extra>'
    ))

    # Reference lines
    fig.add_hline(y=30, line_dash="dot", line_color=COLORS['warning'], opacity=0.5,
                  annotation_text="Moderate (30)", annotation_position="right")
    fig.add_hline(y=50, line_dash="dot", line_color=COLORS['danger'], opacity=0.5,
                  annotation_text="Heavy (50)", annotation_position="right")

    fig.update_layout(
        title=f'Review Load Forecast (Next {days_ahead} Days)',
        xaxis_title='Date',
        yaxis_title='Cards Due',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        margin=dict(l=40, r=40, t=60, b=40),
        plot_bgcolor='white',
        paper_bgcolor='white',
        hovermode='x unified'
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#eee')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#eee', rangemode='tozero')

    return fig


def create_daily_load_contribution_chart():
    """Create daily load contribution by stability chart"""
    df = get_daily_load_by_stability()

    if df.empty:
        return go.Figure()

    fig = go.Figure()

    # Create stacked bar showing contribution
    colors = [COLORS['danger'], COLORS['warning'], COLORS['info'], COLORS['primary'], COLORS['success'], COLORS['excellent']]

    fig.add_trace(go.Bar(
        x=df['stability_range'],
        y=df['load_contribution'],
        marker=dict(
            color=colors[:len(df)],
            line=dict(width=1, color='white')
        ),
        text=df['load_contribution'].round(2),
        textposition='auto',
        hovertemplate='%{x}<br>Load: %{y:.2f}<br>Cards: %{customdata}<extra></extra>',
        customdata=df['card_count']
    ))

    total_load = calculate_daily_load()

    fig.update_layout(
        title=f'Daily Load by Stability Range (Total: {total_load})',
        xaxis_title='Stability Range',
        yaxis_title='Load Contribution (Σ1/interval)',
        margin=dict(l=40, r=40, t=60, b=40),
        plot_bgcolor='white',
        paper_bgcolor='white',
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#eee', rangemode='tozero')

    return fig


def create_load_contribution_distribution_chart():
    """Create distribution of 1/interval values (load contribution per card)"""
    cards_df = get_card_data()

    if cards_df.empty:
        return go.Figure()

    # Filter review cards with valid intervals
    review_cards = cards_df[cards_df['interval'] > 0].copy()

    if review_cards.empty:
        return go.Figure()

    # Calculate load contribution per card
    review_cards['interval_safe'] = review_cards['interval'].clip(lower=1)
    review_cards['load_contribution'] = 1.0 / review_cards['interval_safe']

    fig = go.Figure()

    # Histogram of load contributions
    fig.add_trace(go.Histogram(
        x=review_cards['load_contribution'],
        nbinsx=50,
        marker_color=COLORS['primary'],
        opacity=0.75,
        hovertemplate='Load: %{x:.3f}<br>Cards: %{y}<extra></extra>'
    ))

    # Add vertical line for median
    median_load = review_cards['load_contribution'].median()
    fig.add_vline(
        x=median_load,
        line_dash="dash",
        line_color=COLORS['danger'],
        annotation_text=f"Median: {median_load:.3f}",
        annotation_position="top"
    )

    # Add vertical line for mean
    mean_load = review_cards['load_contribution'].mean()
    fig.add_vline(
        x=mean_load,
        line_dash="dot",
        line_color=COLORS['warning'],
        annotation_text=f"Mean: {mean_load:.3f}",
        annotation_position="bottom"
    )

    total_load = calculate_daily_load()

    fig.update_layout(
        title=f'Load Contribution Distribution (1/interval per card)',
        xaxis_title='Load Contribution (1/interval)',
        yaxis_title='Number of Cards',
        margin=dict(l=40, r=40, t=80, b=40),
        plot_bgcolor='white',
        paper_bgcolor='white',
        annotations=[
            dict(
                text=f"Total Daily Load: {total_load}",
                xref="paper", yref="paper",
                x=0.98, y=0.98,
                xanchor='right', yanchor='top',
                showarrow=False,
                font=dict(size=12, color=COLORS['dark']),
                bgcolor='rgba(255,255,255,0.8)',
                bordercolor=COLORS['primary'],
                borderwidth=1,
                borderpad=4
            )
        ]
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#eee')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#eee', rangemode='tozero')

    return fig


# =============================================================================
# CARDS TAB CONTENT
# =============================================================================

def create_cards_tab():
    """Create the card knowledge tab content"""
    return html.Div([
        # Controls
        html.Div([
            html.Div([
                html.Label("Filter by Retrievability:", style={'fontWeight': '600', 'marginRight': '10px'}),
                dcc.RangeSlider(
                    id='retrievability-filter',
                    min=0,
                    max=100,
                    step=5,
                    value=[0, 100],
                    marks={i: f'{i}%' for i in range(0, 101, 20)},
                    tooltip={"placement": "bottom", "always_visible": False}
                ),
            ], style={'flex': '2', 'marginRight': '30px'}),
            html.Div([
                html.Label("Difficulty:", style={'fontWeight': '600', 'marginRight': '10px'}),
                dcc.RangeSlider(
                    id='difficulty-filter',
                    min=0,
                    max=10,
                    step=0.5,
                    value=[0, 10],
                    marks={i: str(i) for i in range(0, 11, 2)},
                    tooltip={"placement": "bottom", "always_visible": False}
                ),
            ], style={'flex': '1'}),
        ], style={'padding': '20px', 'borderBottom': '1px solid #eee', 'display': 'flex', 'alignItems': 'center'}),

        # Card charts
        html.Div(id='card-charts', style={'padding': '20px'})
    ])


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
    # Update the active date in config so data_loader uses the correct database
    # Use active date from config if selected_date is None
    if selected_date:
        set_active_date(selected_date)
    elif not get_active_date():
        # Fallback if no date is set at all
        dates = get_config_available_dates()
        if dates:
            set_active_date(dates[0])

    cards_df = get_card_data()
    time_df = get_total_time_per_card()

    # Axis scales from UI store
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
        # Memory state breakdown
        html.Div([
            dcc.Graph(
                figure=create_memory_state_chart(cards_df),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),

        # Retrievability distribution
        html.Div([
            dcc.Graph(
                figure=create_retrievability_distribution_chart(filtered_df),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),

        # Stability distribution
        html.Div([
            dcc.Graph(
                figure=create_stability_distribution_chart(filtered_df),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),

        # Difficulty distribution
        html.Div([
            dcc.Graph(
                figure=create_difficulty_distribution_chart(filtered_df),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),
    ], style={'display': 'flex', 'marginBottom': '20px'}))

    # Row 2: Correlations
    charts.append(html.Div([
        # Stability vs Retrievability
        html.Div([
            dcc.Graph(
                figure=create_stability_retrievability_chart(filtered_df),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),

        # Difficulty vs Retrievability
        html.Div([
            dcc.Graph(
                figure=create_difficulty_retrievability_chart(filtered_df),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),

        # Lapses analysis
        html.Div([
            dcc.Graph(
                figure=create_lapses_chart(filtered_df),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),
    ], style={'display': 'flex', 'marginBottom': '20px'}))

    # Row 3: Learning Progress
    charts.append(html.Div([
        # Reviews vs Stability
        html.Div([
            dcc.Graph(
                figure=create_reviews_stability_chart(filtered_df),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),

        # Time spent analysis
        html.Div([
            dcc.Graph(
                figure=create_time_spent_chart(time_df),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),

        # Reviews distribution
        html.Div([
            dcc.Graph(
                figure=create_reviews_distribution_chart(filtered_df),
                config={'displayModeBar': False}
            )
        ], style={'flex': '1', 'padding': '0 10px'}),
    ], style={'display': 'flex', 'marginBottom': '20px'}))

    return charts


def create_memory_state_chart(df):
    """Create memory state breakdown pie chart"""
    if df.empty:
        return go.Figure()

    # Categorize cards
    categories = ['Critical (<50%)', 'At Risk (50-70%)', 'Moderate (70-85%)', 'Good (85-95%)', 'Excellent (95%+)']
    counts = [
        len(df[df['retrievability'] < 50]),
        len(df[(df['retrievability'] >= 50) & (df['retrievability'] < 70)]),
        len(df[(df['retrievability'] >= 70) & (df['retrievability'] < 85)]),
        len(df[(df['retrievability'] >= 85) & (df['retrievability'] < 95)]),
        len(df[df['retrievability'] >= 95])
    ]
    colors = [MEMORY_COLORS[cat] for cat in categories]

    fig = go.Figure(data=[go.Pie(
        labels=categories,
        values=counts,
        marker_colors=colors,
        hole=0.4,
        textinfo='percent+value',
        textposition='inside',
        insidetextorientation='horizontal',
        hovertemplate='%{label}<br>Cards: %{value}<br>Percentage: %{percent}<extra></extra>',
        sort=False  # Preserve order by retrievability category (Critical → Excellent)
    )])

    fig.update_layout(
        title='Memory State Breakdown',
        margin=dict(l=40, r=40, t=60, b=80),
        paper_bgcolor='white',
        legend=dict(orientation='h', yanchor='top', y=-0.1, xanchor='center', x=0.5)
    )

    return fig


def create_retrievability_distribution_chart(df):
    """Create retrievability distribution histogram"""
    if df.empty:
        return go.Figure()

    fig = go.Figure()

    # Create bins and color them
    fig.add_trace(go.Histogram(
        x=df['retrievability'],
        nbinsx=40,
        marker_color=COLORS['primary'],
        opacity=0.7,
        hovertemplate='Retrievability: %{x:.0f}%<br>Cards: %{y}<extra></extra>'
    ))

    # Add reference lines
    fig.add_vline(x=90, line_dash="dash", line_color=COLORS['success'],
                  annotation_text="Target", annotation_position="top")
    fig.add_vline(x=df['retrievability'].median(), line_dash="dash", line_color=COLORS['danger'],
                  annotation_text=f"Median: {df['retrievability'].median():.0f}%", annotation_position="top left")

    fig.update_layout(
        title='Retrievability Distribution',
        xaxis_title='Retrievability (%)',
        yaxis_title='Number of Cards',
        margin=dict(l=40, r=40, t=60, b=40),
        plot_bgcolor='white',
        paper_bgcolor='white',
    )
    fig.update_xaxes(range=[0, 100], showgrid=True, gridwidth=1, gridcolor='#eee')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#eee')

    return fig


def create_stability_distribution_chart(df):
    """Create stability distribution histogram"""
    if df.empty:
        return go.Figure()

    fig = go.Figure()

    fig.add_trace(go.Histogram(
        x=df['stability'],
        nbinsx=40,
        marker_color=COLORS['success'],
        opacity=0.7,
        hovertemplate='Stability: %{x:.1f} days<br>Cards: %{y}<extra></extra>'
    ))

    median_stab = df['stability'].median()
    fig.add_vline(x=median_stab, line_dash="dash", line_color=COLORS['danger'],
                  annotation_text=f"Median: {median_stab:.0f}d", annotation_position="top")

    fig.update_layout(
        title='Stability Distribution',
        xaxis_title='Stability (days)',
        yaxis_title='Number of Cards',
        margin=dict(l=40, r=40, t=60, b=40),
        plot_bgcolor='white',
        paper_bgcolor='white',
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#eee')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#eee')

    return fig


def create_difficulty_distribution_chart(df):
    """Create difficulty distribution histogram"""
    if df.empty:
        return go.Figure()

    fig = go.Figure()

    fig.add_trace(go.Histogram(
        x=df['difficulty'],
        nbinsx=30,
        marker_color=COLORS['info'],
        opacity=0.7,
        hovertemplate='Difficulty: %{x:.1f}<br>Cards: %{y}<extra></extra>'
    ))

    median_diff = df['difficulty'].median()
    fig.add_vline(x=median_diff, line_dash="dash", line_color=COLORS['danger'],
                  annotation_text=f"Median: {median_diff:.1f}", annotation_position="top")

    fig.update_layout(
        title='Difficulty Distribution',
        xaxis_title='Difficulty (0-10)',
        yaxis_title='Number of Cards',
        margin=dict(l=40, r=40, t=60, b=40),
        plot_bgcolor='white',
        paper_bgcolor='white',
    )
    fig.update_xaxes(range=[0, 10], showgrid=True, gridwidth=1, gridcolor='#eee')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#eee')

    return fig


def create_stability_retrievability_chart(df):
    """Create stability vs retrievability scatter plot"""
    if df.empty:
        return go.Figure()

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df['stability'],
        y=df['retrievability'],
        mode='markers',
        marker=dict(
            size=6,
            color=df['difficulty'],
            colorscale='Viridis',
            cmin=0,
            cmax=10,
            colorbar=dict(title='Difficulty'),
            opacity=0.7
        ),
        hovertemplate='Stability: %{x:.1f} days<br>Retrievability: %{y:.1f}%<br>Difficulty: %{marker.color:.1f}<extra></extra>'
    ))

    # Reference lines
    fig.add_hline(y=90, line_dash="dash", line_color=COLORS['success'], opacity=0.5)
    fig.add_hline(y=50, line_dash="dash", line_color=COLORS['danger'], opacity=0.5)

    fig.update_layout(
        title='Stability vs Retrievability',
        xaxis_title='Stability (days)',
        yaxis_title='Retrievability (%)',
        yaxis_range=[-5, 105],
        margin=dict(l=50, r=60, t=60, b=50),
        plot_bgcolor='white',
        paper_bgcolor='white',
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#eee', rangemode='tozero')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#eee')

    return fig


def create_difficulty_retrievability_chart(df):
    """Create difficulty vs retrievability scatter plot"""
    if df.empty:
        return go.Figure()

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df['difficulty'],
        y=df['retrievability'],
        mode='markers',
        marker=dict(
            size=6,
            color=df['lapses'],
            colorscale='Bluered',
            cmin=0,
            colorbar=dict(title='Lapses'),
            opacity=0.7
        ),
        hovertemplate='Difficulty: %{x:.1f}<br>Retrievability: %{y:.1f}%<br>Lapses: %{marker.color}<extra></extra>'
    ))

    # Reference lines
    fig.add_hline(y=90, line_dash="dash", line_color=COLORS['success'], opacity=0.5)
    fig.add_hline(y=50, line_dash="dash", line_color=COLORS['danger'], opacity=0.5)

    fig.update_layout(
        title='Difficulty vs Retrievability',
        xaxis_title='Difficulty (0-10)',
        yaxis_title='Retrievability (%)',
        xaxis_range=[-0.5, 10.5],
        yaxis_range=[-5, 105],
        margin=dict(l=50, r=60, t=60, b=50),
        plot_bgcolor='white',
        paper_bgcolor='white',
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#eee')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#eee')

    return fig


def create_lapses_chart(df):
    """Create lapses analysis chart"""
    if df.empty:
        return go.Figure()

    # Group by lapse count
    lapse_groups = df.groupby('lapses').agg({
        'retrievability': 'mean',
        'difficulty': 'mean',
        'id': 'count'
    }).reset_index()
    lapse_groups.columns = ['lapses', 'avg_retrievability', 'avg_difficulty', 'count']

    # Limit to reasonable lapse counts
    lapse_groups = lapse_groups[lapse_groups['lapses'] <= 15]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=lapse_groups['lapses'],
            y=lapse_groups['count'],
            name='Cards',
            marker_color=COLORS['primary'],
            opacity=0.7,
            hovertemplate='Lapses: %{x}<br>Cards: %{y}<extra></extra>'
        ),
        secondary_y=False
    )

    fig.add_trace(
        go.Scatter(
            x=lapse_groups['lapses'],
            y=lapse_groups['avg_retrievability'],
            name='Avg Retrievability',
            line=dict(color=COLORS['success'], width=3),
            mode='lines+markers',
            hovertemplate='Lapses: %{x}<br>Avg Retrievability: %{y:.1f}%<extra></extra>'
        ),
        secondary_y=True
    )

    fig.update_layout(
        title='Cards by Lapse Count',
        xaxis_title='Number of Lapses',
        hovermode='x unified',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        margin=dict(l=40, r=40, t=60, b=40),
        plot_bgcolor='white',
        paper_bgcolor='white',
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#eee')
    fig.update_yaxes(title_text='Number of Cards', secondary_y=False, showgrid=True, gridwidth=1, gridcolor='#eee')
    fig.update_yaxes(title_text='Avg Retrievability (%)', secondary_y=True, range=[0, 100])

    return fig


def create_reviews_stability_chart(df):
    """Create reviews vs stability chart"""
    if df.empty:
        return go.Figure()

    # Group by review count
    df = df.copy()
    df['reps_capped'] = df['reps'].clip(upper=20)
    rep_groups = df.groupby('reps_capped').agg({
        'stability': ['median', lambda x: np.percentile(x, 25), lambda x: np.percentile(x, 75)],
        'id': 'count'
    }).reset_index()
    rep_groups.columns = ['reps', 'median_stability', 'q1', 'q3', 'count']

    fig = go.Figure()

    # Confidence interval
    fig.add_trace(go.Scatter(
        x=list(rep_groups['reps']) + list(rep_groups['reps'][::-1]),
        y=list(rep_groups['q3']) + list(rep_groups['q1'][::-1]),
        fill='toself',
        fillcolor='rgba(102, 126, 234, 0.2)',
        line=dict(color='rgba(255,255,255,0)'),
        showlegend=True,
        name='IQR'
    ))

    fig.add_trace(go.Scatter(
        x=rep_groups['reps'],
        y=rep_groups['median_stability'],
        mode='lines+markers',
        name='Median Stability',
        line=dict(color=COLORS['primary'], width=3),
        marker=dict(size=8),
        hovertemplate='Reviews: %{x}<br>Median Stability: %{y:.1f} days<extra></extra>'
    ))

    fig.update_layout(
        title='Memory Strength Growth',
        xaxis_title='Number of Reviews',
        yaxis_title='Stability (days)',
        margin=dict(l=40, r=40, t=60, b=40),
        plot_bgcolor='white',
        paper_bgcolor='white',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#eee')
    fig.update_yaxes(type='log', showgrid=True, gridwidth=1, gridcolor='#eee')

    return fig


def create_time_spent_chart(df):
    """Create time spent analysis chart"""
    if df.empty:
        return go.Figure()

    fig = go.Figure()

    # Convert to minutes for better readability
    df = df.copy()
    df['total_time_minutes'] = pd.to_numeric(df['total_time_seconds'], errors='coerce') / 60
    df['stability'] = pd.to_numeric(df['stability'], errors='coerce')
    df = df.dropna(subset=['total_time_minutes', 'stability'])

    if df.empty:
        return go.Figure()

    # Create binned groups for trend line using numpy array
    time_values = df['total_time_minutes'].values.astype(np.float64)
    df['time_bin'] = pd.cut(time_values, bins=20, labels=False)
    time_groups = df.groupby('time_bin').agg({
        'total_time_minutes': 'median',
        'stability': ['median', lambda x: np.percentile(x, 25), lambda x: np.percentile(x, 75)],
    }).reset_index()
    time_groups.columns = ['bin', 'time_median', 'median_stability', 'q1', 'q3']
    time_groups = time_groups.dropna().sort_values('time_median')

    # Confidence interval (IQR)
    fig.add_trace(go.Scatter(
        x=list(time_groups['time_median']) + list(time_groups['time_median'][::-1]),
        y=list(time_groups['q3']) + list(time_groups['q1'][::-1]),
        fill='toself',
        fillcolor='rgba(102, 126, 234, 0.2)',
        line=dict(color='rgba(255,255,255,0)'),
        showlegend=True,
        name='IQR'
    ))

    # Median trend line
    fig.add_trace(go.Scatter(
        x=time_groups['time_median'],
        y=time_groups['median_stability'],
        mode='lines+markers',
        name='Median Stability',
        line=dict(color=COLORS['primary'], width=3),
        marker=dict(size=8),
        hovertemplate='Time: %{x:.1f} min<br>Median Stability: %{y:.1f} days<extra></extra>'
    ))

    # Scatter points
    fig.add_trace(go.Scatter(
        x=df['total_time_minutes'],
        y=df['stability'],
        mode='markers',
        name='Cards',
        marker=dict(
            size=6,
            color=df['lapses'],
            colorscale='Bluered',
            cmin=0,
            colorbar=dict(title='Lapses'),
            opacity=0.4
        ),
        hovertemplate='Time: %{x:.1f} min<br>Stability: %{y:.1f} days<extra></extra>'
    ))

    fig.update_layout(
        title='Time Invested vs Stability',
        xaxis_title='Total Time Spent (minutes)',
        yaxis_title='Stability (days)',
        margin=dict(l=50, r=60, t=60, b=50),
        plot_bgcolor='white',
        paper_bgcolor='white',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#eee', rangemode='tozero')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#eee', type='log')

    return fig


def create_reviews_distribution_chart(df):
    """Create reviews distribution chart (cards by review count with avg retrievability)"""
    if df.empty:
        return go.Figure()

    # Group by review count (reps)
    reviews = df.copy()
    if 'reps' not in reviews.columns:
        # fallback: try 'reviews' if present
        if 'reviews' in reviews.columns:
            reviews['reps'] = reviews['reviews']
        else:
            return go.Figure()

    review_groups = reviews.groupby('reps', observed=True).agg({
        'retrievability': 'mean',
        'difficulty': 'mean',
        'id': 'count'
    }).reset_index()
    review_groups.columns = ['reps', 'avg_retrievability', 'avg_difficulty', 'count']

    # Limit to reasonable review counts for display
    review_groups = review_groups[review_groups['reps'] <= 50]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=review_groups['reps'],
            y=review_groups['count'],
            name='Cards',
            marker_color=COLORS['primary'],
            opacity=0.75,
            hovertemplate='Reviews: %{x}<br>Cards: %{y}<extra></extra>'
        ),
        secondary_y=False
    )

    fig.add_trace(
        go.Scatter(
            x=review_groups['reps'],
            y=review_groups['avg_retrievability'],
            name='Avg Retrievability',
            line=dict(color=COLORS['success'], width=3),
            mode='lines+markers',
            hovertemplate='Reviews: %{x}<br>Avg Retrievability: %{y:.1f}%<extra></extra>'
        ),
        secondary_y=True
    )

    fig.update_layout(
        title='Cards by Review Count',
        xaxis_title='Number of Reviews',
        hovermode='x unified',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        margin=dict(l=40, r=40, t=60, b=40),
        plot_bgcolor='white',
        paper_bgcolor='white',
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#eee')
    fig.update_yaxes(title_text='Number of Cards', secondary_y=False, showgrid=True, gridwidth=1, gridcolor='#eee')
    fig.update_yaxes(title_text='Avg Retrievability (%)', secondary_y=True, range=[0, 100])

    return fig


# =============================================================================
# MAIN LAYOUT
# =============================================================================

app.layout = html.Div([
    html.Div([
        # Header
        html.Div([
            dcc.Location(id='url', refresh=True),
            html.Div([
                html.H1("📚 Anki Learning Dashboard"),
                html.P("Interactive analysis of your learning journey and memory states")
            ], style={'flex': '1'}),

            # Data backup selector
            html.Div([
                html.Label("Data backup:", style={'color': 'white', 'fontWeight': '600', 'marginRight': '8px'}),
                dcc.Dropdown(
                    id='data-folder-dropdown',
                    options=DATE_OPTIONS,
                    value=ACTIVE_DATE,
                    clearable=False,
                    style={'width': '220px'}
                ),
                html.Div(id='active-date-banner', style={'color': 'white', 'marginLeft': '12px', 'fontWeight': '600'}),

                # Global axis scale controls
                html.Div([
                    html.Label('X scale:', style={'color': 'white', 'fontWeight': '600', 'marginRight': '6px'}),
                    dcc.Dropdown(
                        id='x-scale-dropdown',
                        options=[{'label': 'Linear', 'value': 'linear'}, {'label': 'Log', 'value': 'log'}],
                        value='linear',
                        clearable=False,
                        style={'width': '120px'}
                    )
                ], style={'display': 'flex', 'alignItems': 'center', 'marginLeft': '12px'}),

                html.Div([
                    html.Label('Y scale:', style={'color': 'white', 'fontWeight': '600', 'marginRight': '6px'}),
                    dcc.Dropdown(
                        id='y-scale-dropdown',
                        options=[{'label': 'Linear', 'value': 'linear'}, {'label': 'Log', 'value': 'log'}],
                        value='linear',
                        clearable=False,
                        style={'width': '120px'}
                    )
                ], style={'display': 'flex', 'alignItems': 'center', 'marginLeft': '8px'})
            ], style={'display': 'flex', 'alignItems': 'center', 'gap': '8px'})

        ], className='header', style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between'}),

        # Overview stats (dynamic)
        html.Div(id='overview-container'),

        # Tabs
        html.Div([
            dcc.Tabs([
                dcc.Tab(
                    label='📊 Study Sessions',
                    children=create_session_tab(),
                    className='custom-tab',
                    selected_className='custom-tab--selected'
                ),
                dcc.Tab(
                    label='🧠 Card Knowledge',
                    children=create_cards_tab(),
                    className='custom-tab',
                    selected_className='custom-tab--selected'
                ),
            ], className='custom-tabs')
        ], className='tabs-container'),

    ], className='main-container')
])


if __name__ == '__main__':
    import os
    # Only print startup message once (not during Flask reloader)
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        print("\n" + "="*60)
        print("  Anki Learning Dashboard")
        print("="*60)
        print("\n  Starting server...")
        print("  Open http://127.0.0.1:8050 in your browser\n")
        print("="*60 + "\n")

    app.run(debug=True, port=8050)
