"""
Card chart builders for the Anki Learning Dashboard.
All functions are pure: DataFrame in, Plotly Figure out.
"""

# TODO: Refactor chart code organization. There is no distinction between card and session charts anymore.

import pandas as pd
import plotly.graph_objects as go

from .constants import COLORS, DARK_CHART_LAYOUT, DARK_CHART_AXIS


def create_known_words_chart(df):
    """
    Expected known cards over time: Σ retrievability across all cards seen.
    Input: DataFrame from fsrs_engine.get_known_words_timeseries
    """
    if df.empty:
        return go.Figure()

    fig = go.Figure()

    # Upper envelope: total cards ever seen (reference line)
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['cards_seen'],
        name='Cards seen',
        mode='lines',
        line=dict(color=COLORS['text_muted'], width=1, dash='dot'),
        hovertemplate='Cards seen: %{y}<extra></extra>',
    ))

    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['expected_known'],
        name='Expected known',
        mode='lines',
        line=dict(color=COLORS['primary'], width=2),
        fill='tozeroy',
        fillcolor='rgba(91, 141, 255, 0.15)',
        customdata=df['known_pct'],
        hovertemplate='Known: %{y:.0f} cards (%{customdata:.0f}% of seen)<extra></extra>',
    ))

    fig.update_layout(
        title='Known Cards (Σ Retrievability)',
        yaxis_title='Cards',
        hovermode='x unified',
        **DARK_CHART_LAYOUT,
    )
    fig.update_xaxes(**DARK_CHART_AXIS)
    fig.update_yaxes(rangemode='tozero', **DARK_CHART_AXIS)

    return fig


def create_retention_workload_chart(data):
    """
    Desired retention vs equilibrium reviews/day for the current collection.
    Input from fsrs_engine.get_retention_workload_curve.
    """
    curve = data['curve']
    if curve.empty:
        return go.Figure()

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=curve['retention'],
        y=curve['reviews_per_day'],
        mode='lines',
        line=dict(color=COLORS['warning'], width=2),
        customdata=curve['avg_interval'],
        hovertemplate=('Retention: %{x:.1%}<br>Reviews/day: %{y:.0f}'
                       '<br>Avg interval: %{customdata:.0f}d<extra></extra>'),
        showlegend=False,
    ))

    # Mark the current desired-retention setting
    current = data['current_retention']
    idx = (curve['retention'] - current).abs().idxmin()
    cur_load = curve.loc[idx, 'reviews_per_day']
    fig.add_trace(go.Scatter(
        x=[curve.loc[idx, 'retention']],
        y=[cur_load],
        mode='markers+text',
        marker=dict(color=COLORS['warning'], size=10, symbol='circle',
                    line=dict(color='#111217', width=2)),
        text=[f'current: {current:.0%} → {cur_load:.0f}/day'],
        textposition='top left',
        textfont=dict(color='#e0e0e0', size=10),
        hoverinfo='skip',
        showlegend=False,
    ))

    fig.update_layout(
        title='Retention ⇄ Workload Tradeoff',
        xaxis_title='Desired retention',
        yaxis_title='Equilibrium reviews/day',
        **DARK_CHART_LAYOUT,
    )
    fig.update_xaxes(tickformat='.0%', **DARK_CHART_AXIS)
    fig.update_yaxes(rangemode='tozero', **DARK_CHART_AXIS)

    return fig


def create_completion_chart(data, paces=(5, 10, 20), horizon_days=3 * 365):
    """
    Cumulative cards introduced + projected deck completion at candidate
    new-card paces. Input from fsrs_engine.get_completion_projection.
    """
    curve = data['intro_curve']
    if curve.empty:
        return go.Figure()

    introduced = data['introduced']
    total = introduced + data['remaining_new']

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=curve['date'],
        y=curve['cum_introduced'],
        name='Introduced',
        mode='lines',
        line=dict(color=COLORS['primary'], width=2),
        fill='tozeroy',
        fillcolor='rgba(91, 141, 255, 0.12)',
        hovertemplate='%{x|%b %Y}: %{y} cards<extra></extra>',
    ))

    # Deck size target
    fig.add_hline(y=total, line=dict(color=COLORS['text_muted'], width=1, dash='dash'),
                  annotation_text=f'deck: {total:,}',
                  annotation_font=dict(color='#8b8fa3', size=10))

    # Projection scenarios (sequential opacity = pace magnitude)
    today = curve['date'].iloc[-1]
    remaining = data['remaining_new']
    if remaining > 0:
        opacities = (0.35, 0.6, 0.95)
        for pace, op in zip(paces, opacities):
            days_needed = remaining / pace
            if days_needed <= horizon_days:
                end = today + pd.Timedelta(days=days_needed)
                label = f"{pace}/day → {end.strftime('%b %Y')}"
                end_y = total
            else:
                end = today + pd.Timedelta(days=horizon_days)
                label = f'{pace}/day → beyond {end.year}'
                end_y = introduced + pace * horizon_days
            fig.add_trace(go.Scatter(
                x=[today, end], y=[introduced, end_y],
                name=label,
                mode='lines',
                line=dict(color=f'rgba(45, 212, 168, {op})', width=2, dash='dot'),
                hovertemplate=label + '<extra></extra>',
            ))

    fig.update_layout(
        title='Deck Completion Projection',
        yaxis_title='Cards',
        **DARK_CHART_LAYOUT,
    )
    fig.update_xaxes(**DARK_CHART_AXIS)
    fig.update_yaxes(rangemode='tozero', **DARK_CHART_AXIS)

    return fig


# Fixed cohort-year -> color mapping so filters never repaint a cohort
_COHORT_PALETTE = [COLORS['primary'], COLORS['secondary'], COLORS['success'],
                   COLORS['warning'], COLORS['info'], COLORS['danger']]


def create_cohort_chart(df):
    """
    Share of each introduction-year cohort that is mature (stability above
    the app's maturity bar) as a function of card age.
    Input from fsrs_engine.get_cohort_maturity_curves.
    """
    if df.empty:
        return go.Figure()

    fig = go.Figure()

    for cohort in sorted(df['cohort'].unique()):
        sub = df[df['cohort'] == cohort]
        color = _COHORT_PALETTE[(int(cohort) - 2020) % len(_COHORT_PALETTE)]
        fig.add_trace(go.Scatter(
            x=sub['age_days'],
            y=sub['pct_mature'],
            name=str(cohort),
            mode='lines',
            line=dict(color=color, width=2),
            customdata=sub['n'],
            hovertemplate=(f'{cohort} cohort<br>Age: %{{x:.0f}}d<br>'
                           'Mature: %{y:.0f}%<br>Cards observed: %{customdata}<extra></extra>'),
        ))

    fig.update_layout(
        title='Cohort Maturity (by introduction year)',
        xaxis_title='Card age (days)',
        yaxis_title='% mature (stability > 30d)',
        **DARK_CHART_LAYOUT,
    )
    fig.update_xaxes(rangemode='tozero', **DARK_CHART_AXIS)
    fig.update_yaxes(range=[0, 100], **DARK_CHART_AXIS)

    return fig


def create_fatigue_chart(df):
    """
    Accuracy vs position within a study session, with Wilson 95% CI band.
    Input from fsrs_engine.get_fatigue_curve.
    """
    if df.empty:
        return go.Figure()

    fig = go.Figure()

    # CI band
    fig.add_trace(go.Scatter(
        x=pd.concat([df['position'], df['position'][::-1]]),
        y=pd.concat([df['ci_high'], df['ci_low'][::-1]]),
        fill='toself',
        fillcolor='rgba(41, 182, 246, 0.12)',
        line=dict(width=0),
        hoverinfo='skip',
        showlegend=False,
    ))

    fig.add_trace(go.Scatter(
        x=df['position'],
        y=df['success_rate'],
        mode='lines+markers',
        line=dict(color=COLORS['info'], width=2),
        marker=dict(size=6),
        customdata=df[['avg_time_s', 'n']],
        hovertemplate=('Cards %{x:.0f}±5 into session<br>Accuracy: %{y:.1f}%'
                       '<br>Avg answer time: %{customdata[0]:.1f}s'
                       '<br>Reviews: %{customdata[1]}<extra></extra>'),
        showlegend=False,
    ))

    fig.update_layout(
        title='Within-Session Fatigue',
        xaxis_title='Position in session',
        yaxis_title='Accuracy (%)',
        **DARK_CHART_LAYOUT,
    )
    fig.update_xaxes(rangemode='tozero', **DARK_CHART_AXIS)
    fig.update_yaxes(**DARK_CHART_AXIS)

    return fig


def create_calibration_chart(df, summary=None):
    """
    FSRS calibration: predicted retrievability vs observed recall, binned,
    with Wilson 95% CIs. Perfect calibration lies on the identity line.
    Inputs from fsrs_engine.get_calibration_data / get_calibration_summary.
    """
    if df.empty:
        return go.Figure()

    fig = go.Figure()

    # Identity line: perfect calibration
    lo = min(df['predicted'].min(), df['ci_low'].min()) - 0.02
    lo = max(0.0, lo)
    fig.add_trace(go.Scatter(
        x=[lo, 1], y=[lo, 1],
        mode='lines',
        line=dict(color=COLORS['text_muted'], width=1, dash='dash'),
        hoverinfo='skip',
        showlegend=False,
    ))

    fig.add_trace(go.Scatter(
        x=df['predicted'],
        y=df['observed'],
        mode='markers',
        marker=dict(color=COLORS['secondary'], size=7),
        error_y=dict(
            type='data', symmetric=False,
            array=df['ci_high'] - df['observed'],
            arrayminus=df['observed'] - df['ci_low'],
            color='rgba(176, 122, 255, 0.4)', thickness=1.2, width=0,
        ),
        customdata=df['n'],
        hovertemplate=('Predicted: %{x:.1%}<br>Observed: %{y:.1%}'
                       '<br>Reviews: %{customdata}<extra></extra>'),
        showlegend=False,
    ))

    annotations = []
    if summary and summary.get('n'):
        gap = summary['gap_pp']
        direction = 'underestimates' if gap > 0 else 'overestimates'
        annotations.append(dict(
            text=f"FSRS {direction} your recall by {abs(gap):.1f} pp (n={summary['n']:,})",
            xref='paper', yref='paper', x=0.02, y=0.98,
            showarrow=False, font=dict(color='#8b8fa3', size=10),
        ))

    fig.update_layout(
        title='FSRS Calibration',
        xaxis_title='Predicted retrievability',
        yaxis_title='Observed recall',
        annotations=annotations,
        **DARK_CHART_LAYOUT,
    )
    fig.update_xaxes(tickformat='.0%', **DARK_CHART_AXIS)
    fig.update_yaxes(tickformat='.0%', **DARK_CHART_AXIS)

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
