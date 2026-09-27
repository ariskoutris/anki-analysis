"""
Shared constants for AnkiDash.
"""

# Dark color palette
COLORS = {
    'bg_canvas': '#0b0c0e',
    'bg_secondary': '#181b23',
    'border': '#2a2d3a',
    'text_primary': '#e0e0e0',
    'text_secondary': '#8b8fa3',
    'text_muted': '#5a5e72',
    'primary': '#5b8dff',
    'secondary': '#b07aff',
    'success': '#2dd4a8',
    'warning': '#f0b429',
    'danger': '#f25f5c',
    'info': '#29b6f6',
}

# Shared dark chart layout
DARK_CHART_LAYOUT = dict(
    plot_bgcolor='#111217',
    paper_bgcolor='#111217',
    font=dict(color='#8b8fa3', size=11),
    margin=dict(l=40, r=32, t=36, b=32),
    legend=dict(
        orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1,
        font=dict(color='#8b8fa3', size=10),
    ),
)

DARK_CHART_AXIS = dict(
    showgrid=True, gridwidth=1, gridcolor='#2a2d3a',
    zeroline=False,
    tickfont=dict(color='#5a5e72', size=10),
    title_font=dict(color='#8b8fa3', size=11),
)

# Custom HTML/CSS template for the Dash app
INDEX_STRING = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            *, *::before, *::after { box-sizing: border-box; }

            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                background: #0b0c0e;
                color: #e0e0e0;
                min-height: 100vh;
                margin: 0;
            }

            /* Dashboard container */
            .dashboard {
                max-width: 1800px;
                margin: 0 auto;
                padding: 8px 12px;
            }

            /* Top bar */
            .top-bar {
                display: flex;
                align-items: center;
                padding: 6px 12px;
                background: #181b23;
                border: 1px solid #2a2d3a;
                border-radius: 4px;
                margin-bottom: 8px;
                flex-wrap: wrap;
            }
            .top-bar__title {
                font-size: 15px;
                font-weight: 600;
                color: #e0e0e0;
                padding: 0 16px 0 4px;
                white-space: nowrap;
            }
            .top-bar__controls {
                display: flex;
                align-items: center;
                gap: 14px;
                padding: 6px 14px;
                flex-wrap: wrap;
                margin-left: auto;
            }
            .top-bar__separator {
                width: 1px;
                height: 24px;
                background: #2a2d3a;
            }
            .top-bar__group {
                display: flex;
                align-items: center;
                gap: 8px;
            }
            .top-bar__label {
                font-size: 11px;
                color: #5a5e72;
                white-space: nowrap;
            }
            .top-bar__actions {
                display: flex;
                align-items: center;
                gap: 6px;
            }

            /* Stat strip */
            .stat-strip {
                display: flex;
                align-items: center;
                gap: 6px;
                padding: 6px 12px;
                background: #111217;
                border: 1px solid #2a2d3a;
                border-radius: 4px;
                margin-bottom: 8px;
                flex-wrap: wrap;
            }
            .stat-strip__separator {
                width: 1px;
                height: 28px;
                background: #2a2d3a;
                margin: 0 4px;
            }
            .stat-item {
                display: flex;
                flex-direction: column;
                align-items: center;
                padding: 2px 10px;
                min-width: 80px;
            }
            .stat-item__value {
                font-size: 18px;
                font-weight: 700;
                line-height: 1.2;
            }
            .stat-item__label {
                font-size: 10px;
                color: #5a5e72;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                line-height: 1.3;
            }
            .stat-item--secondary .stat-item__value {
                font-size: 14px;
                font-weight: 600;
            }
            .stat-item--secondary .stat-item__label {
                font-size: 9px;
            }

            /* Chart grid */
            .chart-panel {
                background: #111217;
                border: 1px solid #2a2d3a;
                border-radius: 4px;
                padding: 4px;
                min-height: 0;
            }

            /* Draggable grid items */
            .react-grid-item {
                overflow: hidden;
                border-radius: 4px;
            }
            .react-grid-dragHandle {
                padding: 0 !important;
                height: 14px;
                line-height: 14px;
                font-size: 9px;
                letter-spacing: 3px;
                user-select: none;
                opacity: 0.55;
                border-radius: 4px 4px 0 0;
                transition: opacity 0.15s, background 0.15s;
            }
            .react-grid-dragHandle:hover {
                opacity: 1;
                background: #2a2d3a !important;
            }
            .react-grid-placeholder {
                background: #5b8dff !important;
                opacity: 0.12 !important;
                border-radius: 4px;
            }

            /* Resize handles: subtle strips on every border */
            .react-grid-item > .react-resizable-handle {
                background-image: none;
                z-index: 5;
            }
            .react-grid-item > .react-resizable-handle::after {
                border: none !important;
            }
            .react-resizable-handle-e,
            .react-resizable-handle-w {
                top: 0 !important;
                height: 100% !important;
                width: 8px;
                margin-top: 0 !important;
                transform: none !important;
            }
            /* Height is fixed — vertical-only handles are dead, hide them */
            .react-resizable-handle-n,
            .react-resizable-handle-s {
                display: none;
            }

            /* Forecast simulator */
            .sim-section { margin-top: 20px; }
            .sim-header {
                display: flex; justify-content: space-between; align-items: flex-end;
                flex-wrap: wrap; gap: 16px; margin-bottom: 10px;
            }
            .section__title { font-size: 15px; font-weight: 600; color: #e0e0e0; margin: 0; }
            .section__desc { font-size: 12px; color: #8b8fa3; margin: 2px 0 0; }
            .sim-controls { display: flex; align-items: flex-end; gap: 12px; flex-wrap: wrap; }
            .sim-input { display: flex; flex-direction: column; gap: 3px; }
            .sim-input__label { font-size: 10px; color: #8b8fa3; text-transform: uppercase; letter-spacing: 0.4px; }
            .sim-input__wrap { display: flex; align-items: center; gap: 4px; }
            .sim-input__field {
                width: 84px; padding: 5px 8px; font-size: 13px;
                background: #181b23; color: #e0e0e0;
                border: 1px solid #2a2d3a; border-radius: 4px;
            }
            .sim-input__field:focus { outline: none; border-color: #5b8dff; }
            .sim-input__suffix { font-size: 12px; color: #8b8fa3; }
            .sim-run-btn {
                padding: 6px 18px; font-size: 13px; font-weight: 600;
                background: #5b8dff; color: #fff; border: none; border-radius: 4px; cursor: pointer;
            }
            .sim-run-btn:hover { background: #7aa2ff; }
            .sim-charts { display: flex; gap: 8px; }
            @media (max-width: 900px) { .sim-charts { flex-direction: column; } }

            /* Toast message */
            .toast-msg {
                position: fixed;
                top: 12px;
                right: 12px;
                z-index: 1000;
                padding: 8px 14px;
                border-radius: 4px;
                font-size: 12px;
                max-width: 360px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.5);
            }

            /* AnkiWeb login panel */
            .login-panel {
                position: fixed;
                top: 48px;
                right: 12px;
                z-index: 999;
                width: 240px;
                flex-direction: column;
                gap: 8px;
                padding: 14px;
                background: #111217;
                border: 1px solid #2a2d3a;
                border-radius: 4px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.5);
            }
            .login-panel__title { font-size: 13px; font-weight: 600; color: #e0e0e0; }
            .login-panel__field { width: 100%; box-sizing: border-box; }
            .login-panel__note { font-size: 11px; color: #5a5e72; }

            /* ---- Dash component dark overrides ---- */

            /* Dropdown button */
            button.dash-dropdown {
                background-color: #181b23 !important;
                border: 1px solid #2a2d3a !important;
                color: #e0e0e0 !important;
                border-radius: 3px !important;
            }
            button.dash-dropdown:hover {
                border-color: #5b8dff !important;
            }
            .dash-dropdown-trigger-icon {
                color: #5a5e72 !important;
            }
            .dash-dropdown-value,
            .dash-dropdown-value-item {
                color: #e0e0e0 !important;
            }

            /* Dropdown menu (popover content) */
            .dash-dropdown-content {
                background-color: #181b23 !important;
                border: 1px solid #2a2d3a !important;
                box-shadow: 0 4px 12px rgba(0,0,0,0.5) !important;
            }
            .dash-dropdown-search-container {
                background-color: #111217 !important;
                border-color: #2a2d3a !important;
            }
            .dash-dropdown-search {
                background-color: #111217 !important;
                border-color: #2a2d3a !important;
                color: #e0e0e0 !important;
            }
            .dash-dropdown-search::placeholder {
                color: #5a5e72 !important;
            }
            .dash-dropdown-search-icon {
                color: #5a5e72 !important;
            }
            .dash-dropdown-option {
                background-color: #181b23 !important;
                color: #e0e0e0 !important;
            }
            .dash-dropdown-option:hover,
            .dash-dropdown-option[data-highlighted] {
                background-color: #2a2d3a !important;
            }
            .dash-dropdown-option[data-state="checked"] {
                color: #5b8dff !important;
            }

            /* Responsive breakpoints */
            @media (max-width: 768px) {
                .top-bar {
                    flex-direction: column;
                    align-items: flex-start;
                }
                .top-bar__title {
                    margin-right: 0;
                }
                .stat-strip {
                    justify-content: center;
                }
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
        <script>
        /* Explanatory hover hints injected onto each chart's title + axis
           titles as native SVG <title> tooltips. Re-applied on every Plotly
           re-render via a MutationObserver (charts rebuild on filter changes,
           drags and resizes). */
        (function () {
            var HINTS = {
                'chart-daily-reviews': {
                    title: 'Number of cards reviewed each day.',
                    x: 'Calendar date (or session index in sessions mode).',
                    y: 'Reviews done that day.'
                },
                'chart-hourly': {
                    title: 'Review activity and accuracy broken down by hour of day.',
                    x: 'Reviews done in that hour.',
                    y: 'Hour of day (0 to 23).'
                },
                'chart-recall-rate': {
                    title: 'Share of reviews answered correctly over time.',
                    x: 'Calendar date (or session index in sessions mode).',
                    y: 'Percent of reviews rated Hard, Good or Easy.'
                },
                'chart-review-speed': {
                    title: 'Average seconds spent per card over time.',
                    x: 'Calendar date (or session index in sessions mode).',
                    y: 'Seconds spent per card.'
                },
                'chart-known-words': {
                    title: 'Estimated cards known over time, summing the retrievability of every seen card.',
                    y: 'Number of known cards.'
                },
                'chart-future-load': {
                    title: 'Upcoming due cards as a calendar heatmap, with a 7-day average trend.',
                    y: 'Average cards due per day.'
                },
                'chart-calibration': {
                    title: 'FSRS-predicted recall vs your observed recall.',
                    x: 'FSRS-predicted probability of recall.',
                    y: 'Fraction you actually recalled.'
                },
                'chart-retrievability-dist': {
                    title: 'Distribution of current recall probability across your cards.',
                    x: 'Probability of recalling the card now.',
                    y: 'Number of cards.'
                },
                'chart-stability-dist': {
                    title: 'Distribution of memory stability across your cards.',
                    x: 'Days until recall falls to 90%.',
                    y: 'Number of cards.'
                },
                'chart-difficulty-dist': {
                    title: 'Distribution of FSRS difficulty across your cards.',
                    x: 'FSRS difficulty (0 easy to 10 hard).',
                    y: 'Number of cards.'
                },
                'chart-retention-workload': {
                    title: 'Anki’s workload estimate for each desired-retention target, relative to your current setting.',
                    x: 'Desired retention setting.',
                    y: 'Review time relative to the current setting, including relearning after lapses.'
                },
                'chart-load-intro': {
                    title: 'Current review load contributed by cards, grouped by when they were introduced.',
                    x: 'Month the cards were first introduced.',
                    y: 'Daily load from those cards (Σ 1/interval).'
                },
                'chart-load-trend': {
                    title: 'Daily review load over time, reconstructed from your review history.',
                    x: 'Calendar date.',
                    y: 'Reviews per day the schedule generated (Σ 1/interval).'
                },
                'chart-lapse-load': {
                    title: 'How much of your daily review load comes from cards with each lapse count.',
                    x: 'Number of times the card has lapsed.',
                    y: 'Daily load from those cards (Σ 1/interval).'
                },
                'chart-fatigue': {
                    title: 'Success rate as a study session progresses.',
                    x: 'Card position within a session.',
                    y: 'Percent of reviews rated Hard, Good or Easy at that position.'
                },
                'chart-sim-memorized': {
                    title: 'Projected future knowledge under the simulator settings above.',
                    x: 'Projected future date.',
                    y: 'Projected cards known.'
                },
                'chart-sim-reviews': {
                    title: 'Projected future daily reviews under the simulator settings above.',
                    x: 'Projected future date.',
                    y: 'Projected reviews per day.'
                }
            };

            function apply(el, tip) {
                if (!el || !tip) return;
                el.style.pointerEvents = 'all';
                el.style.cursor = 'help';
                var existing = el.querySelector('title');
                if (existing) {
                    if (existing.textContent !== tip) existing.textContent = tip;
                    return;
                }
                var t = document.createElementNS('http://www.w3.org/2000/svg', 'title');
                t.textContent = tip;
                el.insertBefore(t, el.firstChild);
            }

            function decorate() {
                Object.keys(HINTS).forEach(function (id) {
                    var root = document.getElementById(id);
                    if (!root) return;
                    var h = HINTS[id];
                    apply(root.querySelector('.gtitle'), h.title);
                    apply(root.querySelector('.xtitle'), h.x);
                    apply(root.querySelector('.ytitle'), h.y);
                });
            }

            var pending = false;
            function schedule() {
                if (pending) return;
                pending = true;
                requestAnimationFrame(function () { pending = false; decorate(); });
            }

            function start() {
                decorate();
                new MutationObserver(schedule).observe(
                    document.body, { childList: true, subtree: true });
                setInterval(decorate, 2000);  // cheap idempotent fallback
            }

            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', start);
            } else {
                start();
            }
        })();
        </script>
    </body>
</html>
'''
