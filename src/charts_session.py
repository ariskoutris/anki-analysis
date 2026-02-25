"""
Session chart builders for the Anki Learning Dashboard.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .constants import COLORS, DARK_CHART_LAYOUT, DARK_CHART_AXIS


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


def _add_trend_with_ci(fig, x_values, y_vals, color, custom_data, hover_label,
                       y_min=None, y_max=None):
    """Add polynomial regression trend line with symmetric rolling SE band."""
    n = len(y_vals)
    x_num = np.arange(n, dtype=float)
    y = np.asarray(y_vals, dtype=float)

    degree = min(3, max(1, n // 20))
    coeffs = np.polyfit(x_num, y, degree)
    y_fit = np.polyval(coeffs, x_num)

    residuals = y - y_fit
    window = min(15, n)
    se = np.sqrt(np.convolve(residuals**2, np.ones(window) / window, mode='same'))

    y_upper = y_fit + 1.96 * se
    y_lower = y_fit - 1.96 * se

    if y_max is not None:
        y_upper = np.minimum(y_upper, y_max)
    if y_min is not None:
        y_lower = np.maximum(y_lower, y_min)

    # Extract rgba fill color from hex
    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    fill_color = f'rgba({r},{g},{b},0.15)'

    if custom_data is not None:
        hover_fit = 'Session %{x}<br>%{customdata|%b %d, %Y}<br>' + hover_label + ': %{y:.1f}<extra></extra>'
    else:
        hover_fit = '%{x|%b %d, %Y}<br>' + hover_label + ': %{y:.1f}<extra></extra>'

    fig.add_trace(go.Scatter(
        x=x_values, y=y_upper, mode='lines', line=dict(width=0),
        showlegend=False, hoverinfo='skip'
    ))
    fig.add_trace(go.Scatter(
        x=x_values, y=y_lower, mode='lines', line=dict(width=0),
        fill='tonexty', fillcolor=fill_color, name='95% CI', hoverinfo='skip'
    ))
    fig.add_trace(go.Scatter(
        x=x_values, y=y_fit, mode='lines', name='Trend',
        line=dict(color=color, width=2),
        customdata=custom_data, hovertemplate=hover_fit
    ))

    y_range = [min(y_lower.min(), y_fit.min()) / 1.03, max(y_upper.max(), y_fit.max()) * 1.03]
    if y_max is not None:
        y_range[1] = min(y_range[1], y_max)
    return y_range


def create_daily_reviews_chart(df, use_sessions=False):
    """Create daily reviews line chart"""
    if df.empty:
        return go.Figure()

    fig = go.Figure()

    df_plot = df.sort_values('date').reset_index(drop=True)

    if use_sessions:
        x_values = df_plot.index
        x_range = [-0.5, len(df_plot) - 0.5]
        hover_template = 'Session %{x}<br>%{customdata|%b %d, %Y}<br>Reviews: %{y}<extra></extra>'
        custom_data = df_plot['date']
        x_title = 'Session Number'
    else:
        x_values = df_plot['date']
        x_range = [df_plot['date'].min(), df_plot['date'].max()]
        hover_template = '%{x|%b %d, %Y}<br>Reviews: %{y}<extra></extra>'
        custom_data = None
        x_title = 'Date'

    fig.add_trace(go.Scatter(
        x=x_values,
        y=df_plot['daily_reviews'],
        mode='markers',
        name='Session',
        marker=dict(
            size=6,
            color=COLORS['primary'],
            opacity=0.5,
            line=dict(width=1, color='#111217')
        ),
        customdata=custom_data,
        hovertemplate=hover_template
    ))

    y_range = _add_trend_with_ci(
        fig, x_values, df_plot['daily_reviews'].values,
        COLORS['primary'], custom_data, 'Trend', y_min=0
    )

    fig.update_layout(
        title='Daily Reviews',
        xaxis_title=x_title,
        yaxis_title='Reviews',
        hovermode='x unified',
        **DARK_CHART_LAYOUT,
    )
    fig.update_xaxes(range=x_range, **DARK_CHART_AXIS)
    fig.update_yaxes(range=y_range, **DARK_CHART_AXIS)

    if use_sessions:
        markers = get_time_period_markers(df_plot, 'date')
        fig = add_session_time_markers(fig, markers)

    return fig


def create_hourly_chart(df):
    """Create hour of day performance chart as horizontal bars colored by success rate."""
    if df.empty:
        return go.Figure()

    df = df.sort_values('hour')
    hour_labels = [f'{h}:00' for h in df['hour']]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=hour_labels,
        x=df['review_count'],
        orientation='h',
        marker=dict(
            color=df['success_rate'],
            colorscale=[[0, COLORS['danger']], [0.5, COLORS['warning']], [1, COLORS['success']]],
            cmin=df['success_rate'].min() - 5,
            cmax=min(df['success_rate'].max() + 5, 100),
            colorbar=dict(
                title=dict(text='Success %', font=dict(color='#8b8fa3', size=10)),
                tickfont=dict(color='#5a5e72', size=9),
                len=0.8,
            ),
        ),
        hovertemplate='%{y}<br>Reviews: %{x:,}<br>Success: %{customdata:.1f}%<extra></extra>',
        customdata=df['success_rate'],
    ))

    fig.update_layout(
        title='Hourly Performance',
        xaxis_title='Reviews',
        hovermode='y unified',
        yaxis=dict(type='category', autorange='reversed'),
        **DARK_CHART_LAYOUT,
    )
    fig.update_xaxes(**DARK_CHART_AXIS)
    fig.update_yaxes(**DARK_CHART_AXIS)

    return fig


def create_success_rate_chart(df, use_sessions=False):
    """Create success rate over time chart"""
    if df.empty:
        return go.Figure()

    df_sorted = df.sort_values('date').reset_index(drop=True)

    if use_sessions:
        x_values = df_sorted.index
        x_range = [-0.5, len(df_sorted) - 0.5]
        hover_main = 'Session %{x}<br>%{customdata|%b %d, %Y}<br>Success Rate: %{y:.1f}%<extra></extra>'
        custom_data = df_sorted['date']
        x_title = 'Session Number'
    else:
        x_values = df_sorted['date']
        x_range = [df_sorted['date'].min(), df_sorted['date'].max()]
        hover_main = '%{x|%b %d, %Y}<br>Success Rate: %{y:.1f}%<extra></extra>'
        custom_data = None
        x_title = 'Date'

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=x_values,
        y=df_sorted['success_rate'],
        mode='markers',
        name='Session',
        marker=dict(
            size=6,
            color=COLORS['success'],
            opacity=0.5,
            line=dict(width=1, color='#111217')
        ),
        customdata=custom_data,
        hovertemplate=hover_main
    ))

    y_range = _add_trend_with_ci(
        fig, x_values, df_sorted['success_rate'].values,
        COLORS['success'], custom_data, 'Trend', y_min=0, y_max=100
    )

    fig.update_layout(
        title='Recall Rate',
        xaxis_title=x_title,
        yaxis_title='Success Rate (%)',
        yaxis_range=y_range,
        **DARK_CHART_LAYOUT,
    )
    fig.update_xaxes(range=x_range, **DARK_CHART_AXIS)
    fig.update_yaxes(**DARK_CHART_AXIS)

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
        x_range = [-0.5, len(df_sorted) - 0.5]
        hover_template = 'Session %{x}<br>%{customdata|%b %d, %Y}<br>Speed: %{y:.1f} cards/min<extra></extra>'
        custom_data = df_sorted['date']
        x_title = 'Session Number'
    else:
        x_values = df_sorted['date']
        x_range = [df_sorted['date'].min(), df_sorted['date'].max()]
        hover_template = '%{x|%b %d, %Y}<br>Speed: %{y:.1f} cards/min<extra></extra>'
        custom_data = None
        x_title = 'Date'

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=x_values,
        y=df_sorted['cards_per_minute'],
        mode='markers',
        name='Session',
        marker=dict(
            size=6,
            color=COLORS['secondary'],
            opacity=0.5,
            line=dict(width=1, color='#111217')
        ),
        customdata=custom_data,
        hovertemplate=hover_template
    ))

    y_range = _add_trend_with_ci(
        fig, x_values, df_sorted['cards_per_minute'].values,
        COLORS['secondary'], custom_data, 'Trend', y_min=0
    )

    fig.update_layout(
        title='Review Speed',
        xaxis_title=x_title,
        yaxis_title='Cards/min',
        **DARK_CHART_LAYOUT,
    )
    fig.update_xaxes(range=x_range, **DARK_CHART_AXIS)
    fig.update_yaxes(range=y_range, **DARK_CHART_AXIS)

    if use_sessions:
        markers = get_time_period_markers(df_sorted, 'date')
        fig = add_session_time_markers(fig, markers)

    return fig


def create_future_load_chart(df, days_ahead=60):
    """Create future review load forecast chart."""
    if df.empty:
        return go.Figure()

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df['date'],
        y=df['due_count'],
        name='Due Cards',
        marker=dict(
            color=df['due_count'],
            colorscale=[[0, COLORS['success']], [0.5, COLORS['warning']], [1, COLORS['danger']]],
            cmin=0,
            cmax=df['due_count'].quantile(0.95) if len(df) > 0 else 50,
            showscale=False
        ),
        hovertemplate='%{x|%b %d}<br>Due: %{y} cards<extra></extra>'
    ))

    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['ma7'],
        mode='lines',
        name='7-day avg',
        line=dict(color=COLORS['primary'], width=3),
        hovertemplate='%{x|%b %d}<br>Avg: %{y:.0f} cards<extra></extra>'
    ))

    fig.update_layout(
        title=f'Forecast ({days_ahead}d)',
        xaxis_title='Date',
        yaxis_title='Cards Due',
        hovermode='x unified',
        **DARK_CHART_LAYOUT,
    )
    fig.update_xaxes(**DARK_CHART_AXIS)
    fig.update_yaxes(rangemode='tozero', **DARK_CHART_AXIS)

    return fig
