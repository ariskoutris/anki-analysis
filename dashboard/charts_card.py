"""
Card chart builders for the Anki Learning Dashboard.
All functions are pure: DataFrame in, Plotly Figure out.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .constants import COLORS, MEMORY_COLORS


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
        sort=False  # Preserve order by retrievability category (Critical -> Excellent)
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
