"""
Card chart builders for the Anki Learning Dashboard.
All functions are pure: DataFrame in, Plotly Figure out.
"""

# TODO: Refactor chart code organization. There is no distinction between card and session charts anymore.

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .constants import COLORS, DARK_CHART_LAYOUT, DARK_CHART_AXIS
from .charts_session import get_time_period_markers, add_session_time_markers


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
        title='Known Cards',
        yaxis_title='Cards',
        hovermode='x unified',
        **DARK_CHART_LAYOUT,
    )
    fig.update_xaxes(**DARK_CHART_AXIS)
    fig.update_yaxes(rangemode='tozero', **DARK_CHART_AXIS)

    return fig


def create_load_timeseries_chart(df, use_sessions=False, session_dates=None):
    """
    Historical daily load (Σ 1/interval ≈ reviews/day) over time.
    Input: DataFrame[date, load] from data_loader.get_load_timeseries.
    In session mode the series is compressed to study-session days and the
    x-axis becomes a sequential session number.
    """
    if df.empty:
        return go.Figure()

    fig = go.Figure()
    line = dict(color=COLORS['warning'], width=2)
    fill = 'rgba(240, 180, 41, 0.12)'

    if use_sessions and session_dates is not None and len(session_dates):
        d = df[df['date'].isin(pd.DatetimeIndex(session_dates))].reset_index(drop=True)
        if d.empty:
            d = df.reset_index(drop=True)
        fig.add_trace(go.Scatter(
            x=d.index, y=d['load'], mode='lines', line=line,
            fill='tozeroy', fillcolor=fill, customdata=d['date'],
            hovertemplate=('Session %{x}<br>%{customdata|%b %d, %Y}'
                           '<br>Load: %{y:.1f} reviews/day<extra></extra>'),
        ))
        x_title = 'Session Number'
    else:
        d = df
        fig.add_trace(go.Scatter(
            x=d['date'], y=d['load'], mode='lines', line=line,
            fill='tozeroy', fillcolor=fill,
            hovertemplate='%{x|%b %d, %Y}<br>Load: %{y:.1f} reviews/day<extra></extra>',
        ))
        x_title = None

    fig.update_layout(
        title='Load Trend',
        xaxis_title=x_title,
        yaxis_title='Daily load',
        hovermode='x unified',
        **DARK_CHART_LAYOUT,
    )
    fig.update_xaxes(**DARK_CHART_AXIS)
    fig.update_yaxes(rangemode='tozero', **DARK_CHART_AXIS)

    if use_sessions and session_dates is not None and len(session_dates):
        fig = add_session_time_markers(fig, get_time_period_markers(d, 'date'))
    return fig


def create_load_by_introduction_chart(df, use_sessions=False, session_dates=None):
    """
    Current review load grouped by when each card was introduced. In date
    mode bars are monthly (quarterly if the span exceeds ~3 years); in
    session mode cards are bucketed into equal-width session-number ranges.
    Input: DataFrame[intro_date, contrib] from get_load_by_introduction.
    """
    if df is None or df.empty:
        return go.Figure()

    marker = dict(color=COLORS['primary'], cornerradius=3)
    fig = go.Figure()

    if use_sessions and session_dates is not None and len(session_dates):
        sess = pd.DatetimeIndex(pd.Series(session_dates).sort_values())
        idx = np.clip(np.searchsorted(sess.values, df['intro_date'].values,
                                      side='right') - 1, 0, len(sess) - 1)
        # ~20 bars: round bucket width to a tidy number of sessions
        raw = max(1, len(sess) / 20)
        step = max(1, int(round(raw / 5.0) * 5) or 5)
        bucket = (idx // step) * step
        g = pd.DataFrame({'bucket': bucket, 'contrib': df['contrib'].to_numpy()})
        grouped = g.groupby('bucket').agg(
            load=('contrib', 'sum'), n=('contrib', 'size')).reset_index()
        fig.add_trace(go.Bar(
            x=grouped['bucket'] + step / 2.0, y=grouped['load'],
            width=step * 0.9, marker=marker,
            customdata=np.column_stack([grouped['n'], grouped['bucket'],
                                        grouped['bucket'] + step]),
            hovertemplate=('Sessions %{customdata[1]}–%{customdata[2]}'
                           '<br>Load: %{y:.2f}/day<br>Cards: %{customdata[0]}'
                           '<extra></extra>'),
        ))
        x_title = 'Session Number'
    else:
        intro = df['intro_date']
        span_days = (intro.max() - intro.min()).days
        freq = 'Q' if span_days > 1100 else 'M'
        period = intro.dt.to_period(freq).dt.start_time
        g = pd.DataFrame({'period': period, 'contrib': df['contrib'].to_numpy()})
        grouped = g.groupby('period').agg(
            load=('contrib', 'sum'), n=('contrib', 'size')).reset_index()
        grouped = grouped.sort_values('period')
        day_ms = 24 * 3600 * 1000
        width = (75 if freq == 'Q' else 24) * day_ms
        fig.add_trace(go.Bar(
            x=grouped['period'], y=grouped['load'], width=width, marker=marker,
            customdata=grouped['n'],
            hovertemplate=('%{x|%b %Y}<br>Load: %{y:.2f}/day'
                           '<br>Cards: %{customdata}<extra></extra>'),
        ))
        x_title = None

    fig.update_layout(
        title='Load by Introduction',
        xaxis_title=x_title,
        yaxis_title='Current daily load',
        **DARK_CHART_LAYOUT,
    )
    fig.update_xaxes(**DARK_CHART_AXIS)
    fig.update_yaxes(rangemode='tozero', **DARK_CHART_AXIS)
    return fig


def create_lapse_load_chart(df):
    """
    Daily load (Σ 1/interval) grouped by lapse count, with card count on a
    secondary axis. Input: DataFrame from data_loader.get_lapse_load.
    """
    if df is None or df.empty:
        return go.Figure()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df['lapses'], y=df['load'],
        name='Load',
        marker=dict(color=COLORS['primary'], cornerradius=3),
        customdata=df['cards'],
        hovertemplate=('%{x} lapses<br>Load: %{y:.2f}/day'
                       '<br>Cards: %{customdata}<extra></extra>'),
    ))
    fig.add_trace(go.Scatter(
        x=df['lapses'], y=df['cards'],
        name='Cards',
        mode='lines+markers',
        line=dict(color=COLORS['text_secondary'], width=2, dash='dot'),
        marker=dict(size=5),
        yaxis='y2',
        hovertemplate='%{x} lapses<br>Cards: %{y}<extra></extra>',
    ))
    fig.update_layout(
        title='Lapse Load',
        xaxis_title='Lapses',
        yaxis_title='Daily load (reviews/day)',
        yaxis2=dict(
            title=dict(text='Cards', font=dict(color='#8b8fa3', size=11)),
            overlaying='y', side='right',
            tickmode='sync', showgrid=False, zeroline=False,
            rangemode='tozero', tickfont=dict(color='#5a5e72', size=10),
        ),
        **DARK_CHART_LAYOUT,
    )
    fig.update_xaxes(rangemode='tozero', **DARK_CHART_AXIS)
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
        yaxis_title='Daily load (reviews/day)',
        **DARK_CHART_LAYOUT,
    )
    fig.update_xaxes(tickformat='.0%', **DARK_CHART_AXIS)
    fig.update_yaxes(rangemode='tozero', **DARK_CHART_AXIS)

    return fig


def _add_median_line(fig, series, label_fmt):
    """Dashed median reference line with label, matching newer charts."""
    med = float(series.median())
    fig.add_vline(
        x=med,
        line=dict(color='#e0e0e0', width=1, dash='dash'),
        annotation_text=f'median {label_fmt.format(med)}',
        annotation_position='top right',
        annotation_font=dict(color='#8b8fa3', size=10),
    )


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


def create_sim_memorized_chart(df):
    """
    Projected memorized cards (Σ retrievability) over the simulation horizon.
    Input from fsrs_engine.simulate_future.
    """
    if df is None or df.empty:
        return _sim_placeholder('Memorized (projected)')

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['date'], y=df['memorized'],
        mode='lines',
        line=dict(color=COLORS['primary'], width=2),
        fill='tozeroy', fillcolor='rgba(91, 141, 255, 0.12)',
        hovertemplate='%{x|%b %d, %Y}<br>Memorized: %{y:.0f} cards<extra></extra>',
        showlegend=False,
    ))
    end = df['memorized'].iloc[-1]
    fig.add_annotation(
        x=df['date'].iloc[-1], y=end, text=f'{end:.0f}',
        showarrow=False, xanchor='right', yanchor='bottom',
        font=dict(color=COLORS['primary'], size=11),
    )
    fig.update_layout(title='Memorized (projected)', yaxis_title='Cards',
                      **DARK_CHART_LAYOUT)
    fig.update_xaxes(**DARK_CHART_AXIS)
    fig.update_yaxes(rangemode='tozero', **DARK_CHART_AXIS)
    return fig


def create_sim_reviews_chart(df):
    """
    Projected reviews per day over the simulation horizon, with a 7-day
    mean. Input from fsrs_engine.simulate_future.
    """
    if df is None or df.empty:
        return _sim_placeholder('Reviews / day (projected)')

    ma = df['reviews_per_day'].rolling(7, min_periods=1).mean()
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df['date'], y=df['reviews_per_day'],
        marker=dict(color=COLORS['warning'], opacity=0.35),
        name='Daily', hovertemplate='%{x|%b %d}<br>Reviews: %{y:.0f}<extra></extra>',
    ))
    fig.add_trace(go.Scatter(
        x=df['date'], y=ma, mode='lines',
        line=dict(color=COLORS['warning'], width=2), name='7-day avg',
        hovertemplate='7-day avg: %{y:.0f}<extra></extra>',
    ))
    fig.update_layout(title='Reviews / day (projected)', yaxis_title='Reviews',
                      hovermode='x unified', **DARK_CHART_LAYOUT)
    fig.update_xaxes(**DARK_CHART_AXIS)
    fig.update_yaxes(rangemode='tozero', **DARK_CHART_AXIS)
    return fig


def _sim_placeholder(title):
    """Empty-state figure prompting the user to run a simulation."""
    fig = go.Figure()
    fig.update_layout(
        title=title, **DARK_CHART_LAYOUT,
        annotations=[dict(text='Press Simulate to project', xref='paper', yref='paper',
                          x=0.5, y=0.5, showarrow=False,
                          font=dict(size=13, color='#5a5e72'))])
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
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
        name='Success rate',
        line=dict(color=COLORS['info'], width=2),
        marker=dict(size=6),
        customdata=df['n'],
        hovertemplate=('Cards %{x:.0f}±5 into session<br>Success rate: %{y:.1f}%'
                       '<br>Reviews: %{customdata}<extra></extra>'),
        showlegend=True,
    ))

    # Answer time on a secondary axis, with its own CI band
    fig.add_trace(go.Scatter(
        x=pd.concat([df['position'], df['position'][::-1]]),
        y=pd.concat([df['time_ci_high'], df['time_ci_low'][::-1]]),
        fill='toself',
        fillcolor='rgba(240, 180, 41, 0.12)',
        line=dict(width=0),
        yaxis='y2',
        hoverinfo='skip',
        showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=df['position'],
        y=df['avg_time_s'],
        mode='lines+markers',
        name='Answer time',
        line=dict(color=COLORS['warning'], width=2, dash='dot'),
        marker=dict(size=5),
        yaxis='y2',
        hovertemplate='Avg answer time: %{y:.1f}s<extra></extra>',
        showlegend=True,
    ))

    fig.update_layout(
        title='Session Fatigue',
        xaxis_title='Card Position',
        yaxis_title='Success Rate (%)',
        yaxis2=dict(
            title=dict(text='Answer time (s)', font=dict(color='#8b8fa3', size=11)),
            overlaying='y', side='right',
            tickmode='sync',  # share gridlines with the left axis
            showgrid=False, zeroline=False,
            rangemode='tozero',
            tickfont=dict(color='#5a5e72', size=10),
        ),
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

    # Calibration gap: shade between the observed curve and the diagonal.
    # First the diagonal evaluated at each point's predicted value (hidden),
    # then the observed curve filling down/up to it.
    d = df.sort_values('predicted')
    fig.add_trace(go.Scatter(
        x=d['predicted'], y=d['predicted'],
        mode='lines', line=dict(width=0),
        hoverinfo='skip', showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=d['predicted'], y=d['observed'],
        mode='lines', line=dict(color=COLORS['secondary'], width=2),
        fill='tonexty', fillcolor='rgba(176, 122, 255, 0.18)',
        hoverinfo='skip', showlegend=False,
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

    fig.update_layout(
        title='FSRS Calibration',
        xaxis_title='Predicted retrievability',
        yaxis_title='Observed recall',
        **DARK_CHART_LAYOUT,
    )
    fig.update_xaxes(tickformat='.0%', **DARK_CHART_AXIS)
    fig.update_yaxes(tickformat='.0%', **DARK_CHART_AXIS)

    return fig


def _histogram_bar_figure(values, edges, colors, title, x_title, hover_fmt):
    """
    Precomputed histogram rendered as slim rounded bars with gaps.
    `colors` is a single color or a per-bin list.
    """
    counts, _ = np.histogram(values, bins=edges)
    centers = (edges[:-1] + edges[1:]) / 2

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=centers,
        y=counts,
        width=(edges[1:] - edges[:-1]) * 0.82,
        marker=dict(color=colors, cornerradius=3),
        customdata=np.column_stack([edges[:-1], edges[1:]]),
        hovertemplate=hover_fmt + '<extra></extra>',
        showlegend=False,
    ))

    fig.update_layout(
        title=title,
        xaxis_title=x_title,
        yaxis_title='Cards',
        bargap=0,
        **DARK_CHART_LAYOUT,
    )
    fig.update_xaxes(**DARK_CHART_AXIS)
    fig.update_yaxes(rangemode='tozero', **DARK_CHART_AXIS)

    return fig


def create_retrievability_distribution_chart(df):
    """Retrievability histogram."""
    if df.empty:
        return go.Figure()

    fig = _histogram_bar_figure(
        df['retrievability'], np.arange(0, 100.01, 4.0), COLORS['primary'],
        'Retrievability Distribution', 'Retrievability (%)',
        '%{customdata[0]:.0f}–%{customdata[1]:.0f}%: %{y} cards')
    _add_median_line(fig, df['retrievability'], '{:.0f}%')
    return fig


def create_stability_distribution_chart(df):
    """Stability histogram, log-binned (stability is heavily right-skewed)."""
    if df.empty:
        return go.Figure()

    values = df[df['stability'] > 0]['stability']
    log_vals = np.log10(values.to_numpy(dtype=float))
    edges = np.linspace(log_vals.min(), log_vals.max(), 25)

    fig = _histogram_bar_figure(
        log_vals, edges, COLORS['success'],
        'Stability Distribution', 'Stability (days)',
        '%{customdata[2]:.0f}–%{customdata[3]:.0f}d: %{y} cards')
    # Hover needs day-denominated bin bounds alongside the log-space ones
    fig.data[0].customdata = np.column_stack([
        edges[:-1], edges[1:], 10 ** edges[:-1], 10 ** edges[1:]])

    tickvals = [t for t in (1, 3, 7, 21, 60, 180, 365, 1000)
                if log_vals.min() <= np.log10(t) <= log_vals.max() + 0.05]
    fig.update_xaxes(tickvals=[np.log10(t) for t in tickvals],
                     ticktext=[f'{t}d' for t in tickvals])

    med = float(values.median())
    fig.add_vline(
        x=np.log10(med),
        line=dict(color='#e0e0e0', width=1, dash='dash'),
        annotation_text=f'median {med:.0f}d',
        annotation_position='top left',
        annotation_font=dict(color='#8b8fa3', size=10),
    )
    return fig


def create_difficulty_distribution_chart(df):
    """Difficulty histogram."""
    if df.empty:
        return go.Figure()

    fig = _histogram_bar_figure(
        df['difficulty'], np.linspace(0, 10, 26), COLORS['info'],
        'Difficulty Distribution', 'Difficulty',
        '%{customdata[0]:.1f}–%{customdata[1]:.1f}: %{y} cards')
    _add_median_line(fig, df['difficulty'], '{:.1f}')
    return fig
