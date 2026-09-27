/* Chart grid: drag the ⠿ grip to move a chart, drag its right edge to set
   its width (1-3 columns). The layout is a list of {id, w} in display order,
   rendered with CSS grid `order` + `grid-column: span` (the DOM is never
   reordered, so React's tree stays intact) and saved to localStorage.
   Charts resize themselves via the ResizeObserver in the index template. */
(function () {
    var KEY = 'ankidash-grid', COLS = 3;

    function panels(grid) {
        return Array.prototype.filter.call(grid.children, function (p) { return p.dataset.id; });
    }

    function load(grid) {
        var defaults = panels(grid).map(function (p) { return {id: p.dataset.id, w: +p.dataset.w}; });
        var known = {}, seen = {}, state = [], saved = [];
        defaults.forEach(function (d) { known[d.id] = true; });
        try { saved = JSON.parse(localStorage.getItem(KEY)) || []; } catch (e) {}
        saved.forEach(function (s) {
            if (s && known[s.id] && !seen[s.id]) {
                seen[s.id] = true;
                state.push({id: s.id, w: Math.min(COLS, Math.max(1, s.w | 0))});
            }
        });
        defaults.forEach(function (d) { if (!seen[d.id]) { state.push(d); } });
        return state;
    }

    function save(state) {
        try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {}
    }

    // Pack rows in order; the last panel of each row stretches over any
    // leftover columns, so the grid never has holes.
    function apply(grid, state) {
        var spans = state.map(function (s) { return s.w; }), used = 0;
        state.forEach(function (s, i) {
            if (used + s.w > COLS) { spans[i - 1] += COLS - used; used = 0; }
            used += s.w;
        });
        spans[state.length - 1] += COLS - used;
        var byId = {};
        panels(grid).forEach(function (p) { byId[p.dataset.id] = p; });
        state.forEach(function (s, i) {
            byId[s.id].style.order = i;
            byId[s.id].style.gridColumn = 'span ' + spans[i];
        });
    }

    function init(grid) {
        var state = load(grid);
        apply(grid, state);

        grid.addEventListener('pointerdown', function (e) {
            var grip = e.target.closest('.grid-panel__grip');
            var handle = e.target.closest('.grid-panel__resize');
            if (!grip && !handle) { return; }
            e.preventDefault();
            var panel = e.target.closest('.grid-panel'), id = panel.dataset.id;
            var index = function (pid) { return state.findIndex(function (s) { return s.id === pid; }); };
            var lastTarget = null;
            panel.classList.add(grip ? 'is-moving' : 'is-resizing');
            document.body.classList.add('grid-busy');

            function resize(ev) {
                var gap = parseFloat(getComputedStyle(grid).columnGap) || 0;
                var col = (grid.clientWidth - gap * (COLS - 1)) / COLS;
                var width = ev.clientX - panel.getBoundingClientRect().left;
                var w = Math.min(COLS, Math.max(1, Math.round((width + gap) / (col + gap))));
                var s = state[index(id)];
                if (w !== s.w) { s.w = w; apply(grid, state); }
            }

            function move(ev) {
                var el = document.elementFromPoint(ev.clientX, ev.clientY);
                var over = el && el.closest('.grid-panel');
                if (!over || over === panel || over.parentNode !== grid) { return; }
                var r = over.getBoundingClientRect();
                var after = ev.clientX > r.left + r.width / 2;
                var target = over.dataset.id + (after ? ':after' : ':before');
                if (target === lastTarget) { return; }
                lastTarget = target;
                var item = state.splice(index(id), 1)[0];
                state.splice(index(over.dataset.id) + (after ? 1 : 0), 0, item);
                apply(grid, state);
            }

            // While moving, scroll the page when the pointer nears the top or
            // bottom edge, so off-screen positions can be reached.
            var pointer = null, scrolling = null, EDGE = 60;
            function autoScroll() {
                scrolling = null;
                if (!pointer) { return; }
                var y = pointer.clientY, dy = 0;
                if (y < EDGE) { dy = -(EDGE - y) / 3; }
                else if (y > window.innerHeight - EDGE) { dy = (y - window.innerHeight + EDGE) / 3; }
                if (dy) {
                    window.scrollBy(0, dy);
                    move(pointer);
                    scrolling = requestAnimationFrame(autoScroll);
                }
            }

            var onMove = grip ? function (ev) {
                pointer = {clientX: ev.clientX, clientY: ev.clientY};
                move(pointer);
                if (!scrolling) { scrolling = requestAnimationFrame(autoScroll); }
            } : resize;
            function end() {
                pointer = null;
                if (scrolling) { cancelAnimationFrame(scrolling); }
                window.removeEventListener('pointermove', onMove);
                window.removeEventListener('pointerup', end);
                window.removeEventListener('pointercancel', end);
                panel.classList.remove('is-moving', 'is-resizing');
                document.body.classList.remove('grid-busy');
                save(state);
            }
            window.addEventListener('pointermove', onMove);
            window.addEventListener('pointerup', end);
            window.addEventListener('pointercancel', end);
        });
    }

    // Dash renders the layout after this script loads; wire up the grid
    // once it appears (and again if it's ever re-mounted).
    new MutationObserver(function () {
        var grid = document.getElementById('chart-grid');
        if (grid && !grid.dataset.ready) { grid.dataset.ready = '1'; init(grid); }
    }).observe(document.documentElement, {childList: true, subtree: true});
})();
