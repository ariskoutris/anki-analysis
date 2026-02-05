"""
Session chart builders for the Anki Learning Dashboard.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .constants import COLORS
from .data_loader import (
    get_future_load_forecast,
    get_daily_load_by_stability,
    get_card_data,
    calculate_daily_load,
)


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
