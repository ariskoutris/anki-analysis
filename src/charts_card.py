"""
Card chart builders for the Anki Learning Dashboard.
All functions are pure: DataFrame in, Plotly Figure out.
"""

# TODO: Refactor chart code organization. There is no distinction between card and session charts anymore.

import plotly.graph_objects as go

from .constants import COLORS, MEMORY_COLORS, DARK_CHART_LAYOUT, DARK_CHART_AXIS


def create_memory_state_chart(df):
    """Create memory state breakdown donut chart"""
    if df.empty:
        return go.Figure()

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
        textfont=dict(color='#1a1a2e', size=11),
        hovertemplate='%{label}<br>Cards: %{value}<br>Percentage: %{percent}<extra></extra>',
        sort=False
    )])

    fig.update_layout(
        title='Memory State',
        margin=dict(l=20, r=20, t=36, b=80),
        paper_bgcolor='#111217',
        plot_bgcolor='#111217',
        font=dict(color='#8b8fa3', size=11),
        legend=dict(
            orientation='h', yanchor='top', y=-0.05, xanchor='center', x=0.5,
            font=dict(color='#8b8fa3', size=9),
        ),
    )

    return fig


def create_retrievability_distribution_chart(df):
    """Create retrievability distribution histogram"""
    if df.empty:
        return go.Figure()

    fig = go.Figure()

    fig.add_trace(go.Histogram(
        x=df['retrievability'],
        nbinsx=40,
        marker_color=COLORS['primary'],
        opacity=0.7,
        hovertemplate='Retrievability: %{x:.0f}%<br>Cards: %{y}<extra></extra>'
    ))

    fig.update_layout(
        title='Retrievability Distribution',
        xaxis_title='Retrievability (%)',
        yaxis_title='Cards',
        **DARK_CHART_LAYOUT,
    )
    fig.update_xaxes(rangemode='tozero', **DARK_CHART_AXIS)
    fig.update_yaxes(**DARK_CHART_AXIS)

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

    fig.update_layout(
        title='Stability Distribution',
        xaxis_title='Stability (days)',
        yaxis_title='Cards',
        **DARK_CHART_LAYOUT,
    )
    fig.update_xaxes(rangemode='tozero', **DARK_CHART_AXIS)
    fig.update_yaxes(**DARK_CHART_AXIS)

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

    fig.update_layout(
        title='Difficulty Distribution',
        xaxis_title='Difficulty (0-10)',
        yaxis_title='Cards',
        **DARK_CHART_LAYOUT,
    )
    fig.update_xaxes(rangemode='tozero', **DARK_CHART_AXIS)
    fig.update_yaxes(**DARK_CHART_AXIS)

    return fig
