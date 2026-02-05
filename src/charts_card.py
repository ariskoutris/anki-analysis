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
        title='Memory Strength Growth (log scale)',
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


def create_leech_chart(leech_df):
    """Create leech identification scatter chart showing problem cards"""
    if leech_df.empty:
        return go.Figure()

    fig = go.Figure()

    # Main scatter: time invested vs lapses, sized by leech score
    fig.add_trace(go.Scatter(
        x=leech_df['lapses'],
        y=leech_df['total_time_seconds'] / 60,  # Convert to minutes
        mode='markers',
        marker=dict(
            size=leech_df['leech_score'].clip(upper=30) + 5,  # Size based on leech score
            color=leech_df['retrievability'],
            colorscale='RdYlGn',
            cmin=0,
            cmax=100,
            colorbar=dict(title='Retrievability %'),
            opacity=0.7,
            line=dict(width=1, color='white')
        ),
        customdata=leech_df[['card_id', 'reps', 'stability', 'lapse_ratio']].values,
        hovertemplate=(
            'Card ID: %{customdata[0]}<br>'
            'Lapses: %{x}<br>'
            'Time Spent: %{y:.1f} min<br>'
            'Reviews: %{customdata[1]}<br>'
            'Stability: %{customdata[2]:.1f} days<br>'
            'Lapse Ratio: %{customdata[3]:.1%}<br>'
            'Retrievability: %{marker.color:.0f}%'
            '<extra></extra>'
        )
    ))

    # Add "leech zone" annotation
    fig.add_annotation(
        x=0.95, y=0.95,
        xref='paper', yref='paper',
        text=f"Top {len(leech_df)} problem cards",
        showarrow=False,
        font=dict(size=11, color=COLORS['danger']),
        bgcolor='rgba(255,255,255,0.8)',
        bordercolor=COLORS['danger'],
        borderwidth=1,
        borderpad=4
    )

    fig.update_layout(
        title='Leech Cards (High Lapses + Time Wasted)',
        xaxis_title='Number of Lapses',
        yaxis_title='Time Invested (minutes)',
        margin=dict(l=50, r=60, t=60, b=50),
        plot_bgcolor='white',
        paper_bgcolor='white',
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#eee')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#eee', rangemode='tozero')

    return fig
