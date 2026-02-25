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


def create_daily_reviews_chart(df, use_sessions=False):
    """Create daily reviews line chart"""
    if df.empty:
        return go.Figure()

    fig = go.Figure()

    df_plot = df.sort_values('date').reset_index(drop=True)

    if use_sessions:
        x_values = df_plot.index
        hover_template = 'Session %{x}<br>%{customdata|%b %d, %Y}<br>Reviews: %{y}<extra></extra>'
        custom_data = df_plot['date']
        x_title = 'Session Number'
    else:
        x_values = df_plot['date']
        hover_template = '%{x|%b %d, %Y}<br>Reviews: %{y}<extra></extra>'
        custom_data = None
        x_title = 'Date'

    fig.add_trace(go.Scatter(
        x=x_values,
        y=df_plot['daily_reviews'],
        mode='lines',
        fill='tozeroy',
        name='Reviews',
        line=dict(color=COLORS['primary'], width=2),
        fillcolor='rgba(91,141,255,0.15)',
        customdata=custom_data,
        hovertemplate=hover_template
    ))

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
        title='Daily Reviews',
        xaxis_title=x_title,
        yaxis_title='Reviews',
        hovermode='x unified',
        **DARK_CHART_LAYOUT,
    )
    fig.update_xaxes(**DARK_CHART_AXIS)
    fig.update_yaxes(**DARK_CHART_AXIS)

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
            marker=dict(size=5),
            hovertemplate='Hour %{x}:00<br>Success: %{y:.1f}%<extra></extra>'
        ),
        secondary_y=True
    )

    fig.update_layout(
        title='Hourly Performance',
        xaxis_title='Hour',
        hovermode='x unified',
        **DARK_CHART_LAYOUT,
    )
    fig.update_xaxes(dtick=2, **DARK_CHART_AXIS)
    fig.update_yaxes(title_text='Reviews', secondary_y=False, **DARK_CHART_AXIS)
    fig.update_yaxes(title_text='Success %', secondary_y=True, range=[0, 100],
                     **DARK_CHART_AXIS)

    return fig


def create_success_rate_chart(df, use_sessions=False):
    """Create success rate over time chart"""
    if df.empty:
        return go.Figure()

    df_sorted = df.sort_values('date').reset_index(drop=True)
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
            line=dict(width=1, color='#111217')
        ),
        customdata=custom_data,
        hovertemplate=hover_main
    ))

    fig.add_trace(go.Scatter(
        x=x_values,
        y=df_sorted['ma7'],
        mode='lines',
        name='7-session avg',
        line=dict(color=COLORS['primary'], width=2),
        customdata=custom_data,
        hovertemplate=hover_ma
    ))

    fig.update_layout(
        title='Recall Rate',
        xaxis_title=x_title,
        yaxis_title='Success Rate (%)',
        yaxis_range=[50, 100],
        **DARK_CHART_LAYOUT,
    )
    fig.update_xaxes(**DARK_CHART_AXIS)
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
        marker=dict(size=5),
        customdata=custom_data,
        hovertemplate=hover_template
    ))

    fig.update_layout(
        title='Review Speed',
        xaxis_title=x_title,
        yaxis_title='Cards/min',
        **DARK_CHART_LAYOUT,
    )
    fig.update_xaxes(**DARK_CHART_AXIS)
    fig.update_yaxes(**DARK_CHART_AXIS)

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
