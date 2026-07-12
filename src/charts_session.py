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
    """Add year-change divider lines with an offset label (matching the
    median reference lines on the distribution charts)."""
    for marker in markers:
        fig.add_vline(
            x=marker['index'],
            line=dict(color='#e0e0e0', width=1, dash='dash'),
            annotation_text=marker['label'],
            annotation_position='top right',
            annotation_font=dict(color='#8b8fa3', size=10),
        )

    return fig


def _add_trend_with_ci(fig, x_values, y_vals, color, custom_data, hover_label,
                       y_min=None, y_max=None, window=15):
    """
    Add a centered rolling-mean trend with a 95% CI band (rolling SEM).
    Local estimate — unlike a global polynomial fit, it cannot invent
    structure across long gaps in the data.
    """
    n = len(y_vals)
    if n < 5:
        return None  # too few points for a meaningful trend; autorange y

    y = pd.Series(np.asarray(y_vals, dtype=float))

    w = min(window, max(3, n))
    roll = y.rolling(w, center=True, min_periods=max(2, w // 3))
    y_fit = roll.mean().to_numpy()
    sem = (roll.std() / np.sqrt(roll.count())).fillna(0).to_numpy()

    y_upper = y_fit + 1.96 * sem
    y_lower = y_fit - 1.96 * sem

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

    y_range = [np.nanmin([np.nanmin(y_lower), np.nanmin(y_fit)]) / 1.03,
               np.nanmax([np.nanmax(y_upper), np.nanmax(y_fit)]) * 1.03]
    if not all(np.isfinite(y_range)):
        return None
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
            # Single-hue sequential: success rate is a magnitude, not a status
            colorscale=[[0, '#16302b'], [1, COLORS['success']]],
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

    # Seconds per card (inverse of the cards/min rate)
    sec_per_card = 60.0 / df_sorted['cards_per_minute'].where(
        df_sorted['cards_per_minute'] > 0)

    if use_sessions:
        x_values = df_sorted.index
        x_range = [-0.5, len(df_sorted) - 0.5]
        hover_template = 'Session %{x}<br>%{customdata|%b %d, %Y}<br>Speed: %{y:.1f} sec/card<extra></extra>'
        custom_data = df_sorted['date']
        x_title = 'Session Number'
    else:
        x_values = df_sorted['date']
        x_range = [df_sorted['date'].min(), df_sorted['date'].max()]
        hover_template = '%{x|%b %d, %Y}<br>Speed: %{y:.1f} sec/card<extra></extra>'
        custom_data = None
        x_title = 'Date'

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=x_values,
        y=sec_per_card,
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
        fig, x_values, sec_per_card.values,
        COLORS['secondary'], custom_data, 'Trend', y_min=0
    )

    fig.update_layout(
        title='Review Speed',
        xaxis_title=x_title,
        yaxis_title='Sec/card',
        **DARK_CHART_LAYOUT,
    )
    fig.update_xaxes(range=x_range, **DARK_CHART_AXIS)
    fig.update_yaxes(range=y_range, **DARK_CHART_AXIS)

    if use_sessions:
        markers = get_time_period_markers(df_sorted, 'date')
        fig = add_session_time_markers(fig, markers)

    return fig


def create_future_load_chart(df, days_ahead=60):
    """
    Upcoming review load as a GitHub-style calendar heatmap (weekday rows ×
    week columns) with a 7-day-average trend line above, sharing the same
    week-based x-axis so peaks line up with their columns.
    """
    if df.empty:
        return go.Figure()

    d = df.copy()
    d['date'] = pd.to_datetime(d['date'])
    first = d['date'].min()
    week_start = first - pd.Timedelta(days=int(first.weekday()))  # Monday
    offset = (d['date'] - week_start).dt.days
    d['week'] = (offset // 7).astype(int)
    d['wd'] = (offset % 7).astype(int)
    n_weeks = int(d['week'].max()) + 1

    # Calendar matrix (weekday × week); NaN = day outside the forecast window
    z = np.full((7, n_weeks), np.nan)
    date_txt = np.empty((7, n_weeks), dtype=object)
    for _, r in d.iterrows():
        z[r['wd'], r['week']] = r['due_count']
        date_txt[r['wd'], r['week']] = r['date'].strftime('%a %b %d')

    week_centers = [w + 0.5 for w in range(n_weeks)]
    blue_scale = [
        [0.0, '#1a2030'], [0.12, '#20365f'], [0.35, '#2f5db0'],
        [0.65, '#4f86e8'], [1.0, '#9cc0ff'],
    ]

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.5, 0.5], vertical_spacing=0.05,
    )

    # Trend line (7-day average), positioned on the shared week axis
    fig.add_trace(go.Scatter(
        x=(offset + 0.5) / 7.0,
        y=d['ma7'],
        mode='lines',
        name='7-day avg',
        line=dict(color=COLORS['warning'], width=2, shape='spline'),
        fill='tozeroy', fillcolor='rgba(240, 180, 41, 0.10)',
        customdata=d['due_count'],
        hovertemplate='7-day avg: %{y:.0f} · that day: %{customdata}<extra></extra>',
    ), row=1, col=1)

    # Calendar heatmap
    fig.add_trace(go.Heatmap(
        x=week_centers, y=list(range(7)), z=z,
        customdata=date_txt,
        colorscale=blue_scale, zmin=0,
        xgap=3, ygap=3, showscale=False, hoverongaps=False,
        hovertemplate='%{customdata}: %{z:.0f} due<extra></extra>',
    ), row=2, col=1)

    # Month labels along the bottom axis
    tickvals, ticktext, last_month = [], [], None
    for w in range(n_weeks):
        wk_date = week_start + pd.Timedelta(weeks=w)
        if wk_date.month != last_month:
            tickvals.append(w + 0.5)
            ticktext.append(wk_date.strftime('%b'))
            last_month = wk_date.month

    layout = dict(DARK_CHART_LAYOUT)
    layout['margin'] = dict(l=44, r=16, t=36, b=22)
    layout['showlegend'] = False
    fig.update_layout(title='Upcoming Reviews', hovermode='closest', **layout)

    # Trend row
    fig.update_yaxes(title_text='Due/day', rangemode='tozero',
                     row=1, col=1, **DARK_CHART_AXIS)
    fig.update_xaxes(range=[0, n_weeks], showticklabels=False,
                     showgrid=False, zeroline=False, row=1, col=1)

    # Calendar row (Mon at top, month ticks below)
    fig.update_yaxes(
        row=2, col=1, autorange='reversed',
        tickvals=[0, 2, 4, 6], ticktext=['Mon', 'Wed', 'Fri', 'Sun'],
        showgrid=False, zeroline=False,
        tickfont=dict(color='#5a5e72', size=10),
    )
    fig.update_xaxes(
        row=2, col=1, range=[0, n_weeks],
        tickvals=tickvals, ticktext=ticktext,
        showgrid=False, zeroline=False,
        tickfont=dict(color='#5a5e72', size=10),
    )

    return fig
