"""
FSRS history replay engine.

Reconstructs per-review FSRS memory states (stability, difficulty, predicted
retrievability) by replaying the full review log through py-fsrs using each
deck's own FSRS parameters from deck presets.

Shared infrastructure for the known-words metric, model calibration, and
cohort analyses. Results are cached per (db mtime, deck_id) since replaying
the log is the most expensive computation in the app.
"""

import json
import os
import random
import struct
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
from fsrs import Scheduler, Card, Rating, State

from .config import get_db_path
from .data_loader import connect_db, get_collection_start_date


# =============================================================================
# DECK CONFIG PARSING (protobuf)
# =============================================================================

def _read_varint(blob: bytes, i: int) -> tuple[int, int]:
    """Read a protobuf varint starting at index i. Returns (value, next_index)."""
    value = 0
    shift = 0
    while True:
        b = blob[i]
        i += 1
        value |= (b & 0x7F) << shift
        shift += 7
        if not b & 0x80:
            return value, i


def _iter_pb_fields(blob: bytes):
    """Yield (field_number, wire_type, raw_value) for a protobuf message."""
    i = 0
    n = len(blob)
    while i < n:
        tag, i = _read_varint(blob, i)
        field, wire = tag >> 3, tag & 7
        if wire == 0:
            value, i = _read_varint(blob, i)
        elif wire == 1:
            value = blob[i:i + 8]
            i += 8
        elif wire == 2:
            length, i = _read_varint(blob, i)
            value = blob[i:i + length]
            i += length
        elif wire == 5:
            value = blob[i:i + 4]
            i += 4
        else:
            return  # unknown wire type; bail out
        yield field, wire, value


def _to_fsrs6_params(params: list[float]) -> tuple[float, ...] | None:
    """Migrate FSRS-4.5 (17) / FSRS-5 (19) parameter lists to FSRS-6 (21)."""
    params = list(params)
    if len(params) == 17:
        params += [0.0, 0.0]  # FSRS-4.5 -> FSRS-5: w17, w18
    if len(params) == 19:
        params += [0.0, 0.5]  # FSRS-5 -> FSRS-6: w19 (short-term), w20 (decay)
    if len(params) != 21:
        return None
    return tuple(params)


# DeckConfig.Config protobuf fields holding FSRS params, newest scheme first
_FSRS_PARAM_FIELDS = (6, 5, 3)  # fsrs_params_6, fsrs_params_5, fsrs_params_4
_DESIRED_RETENTION_FIELD = 37


# DeckConfig.Config protobuf fields for scheduling settings
_LEARN_STEPS_FIELD = 1       # repeated float, minutes
_RELEARN_STEPS_FIELD = 2     # repeated float, minutes
_NEW_PER_DAY_FIELD = 9       # uint32
_REV_PER_DAY_FIELD = 10      # uint32


def _parse_deck_config(blob: bytes) -> dict:
    """Extract FSRS params, retention, learning steps and daily limits."""
    param_arrays: dict[int, list[float]] = {}
    desired_retention = 0.9
    learn_steps: list[float] = []
    relearn_steps: list[float] = []
    new_per_day = 20    # Anki defaults when the field is absent
    rev_per_day = 200

    for field, wire, value in _iter_pb_fields(blob):
        if field in _FSRS_PARAM_FIELDS and wire == 2 and len(value) % 4 == 0 and len(value) >= 68:
            param_arrays[field] = list(struct.unpack(f'<{len(value) // 4}f', value))
        elif field == _DESIRED_RETENTION_FIELD and wire == 5:
            desired_retention = struct.unpack('<f', value)[0]
        elif field == _LEARN_STEPS_FIELD and wire == 2 and len(value) % 4 == 0:
            learn_steps = list(struct.unpack(f'<{len(value) // 4}f', value))
        elif field == _RELEARN_STEPS_FIELD and wire == 2 and len(value) % 4 == 0:
            relearn_steps = list(struct.unpack(f'<{len(value) // 4}f', value))
        elif field == _NEW_PER_DAY_FIELD and wire == 0:
            new_per_day = value
        elif field == _REV_PER_DAY_FIELD and wire == 0:
            rev_per_day = value

    params = None
    for field in _FSRS_PARAM_FIELDS:
        if field in param_arrays:
            params = _to_fsrs6_params(param_arrays[field])
            if params:
                break

    return {
        'params': params,
        'desired_retention': desired_retention,
        'learn_steps': learn_steps,
        'relearn_steps': relearn_steps,
        'new_per_day': int(new_per_day),
        'rev_per_day': int(rev_per_day),
    }


def _parse_deck_kind_config_id(kind_blob: bytes) -> int | None:
    """Extract the deck_config id from a decks.kind blob (normal decks only)."""
    for field, wire, value in _iter_pb_fields(kind_blob):
        if field == 1 and wire == 2:  # NormalDeck submessage
            for sub_field, sub_wire, sub_value in _iter_pb_fields(value):
                if sub_field == 1 and sub_wire == 0:  # config_id
                    return sub_value
    return None


def get_deck_fsrs_configs() -> dict[int, dict]:
    """
    Map deck_id -> {'params': tuple(21)|None, 'desired_retention': float}.

    Decks without FSRS params (or filtered decks) get params=None, which
    means py-fsrs default parameters are used for replay.
    """
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute('SELECT id, config FROM deck_config')
    configs = {row[0]: _parse_deck_config(row[1]) for row in cursor.fetchall()}

    cursor.execute('SELECT id, kind FROM decks')
    deck_map = {}
    default = {'params': None, 'desired_retention': 0.9,
               'learn_steps': [], 'relearn_steps': [], 'new_per_day': 20, 'rev_per_day': 200}
    for deck_id, kind_blob in cursor.fetchall():
        config_id = _parse_deck_kind_config_id(kind_blob)
        deck_map[deck_id] = configs.get(config_id, default)

    conn.close()
    return deck_map


def _make_scheduler(params: tuple[float, ...] | None,
                    learn_steps: list[float] | None = None,
                    relearn_steps: list[float] | None = None) -> Scheduler:
    """
    Build a py-fsrs scheduler, falling back to defaults on bad params.
    Learning/relearning steps (minutes, from the deck preset) are passed
    through when provided so the simulator schedules like the real deck.
    """
    kwargs = {'enable_fuzzing': False}
    if learn_steps:
        kwargs['learning_steps'] = tuple(timedelta(minutes=m) for m in learn_steps)
    if relearn_steps:
        kwargs['relearning_steps'] = tuple(timedelta(minutes=m) for m in relearn_steps)
    if params:
        try:
            return Scheduler(parameters=params, **kwargs)
        except ValueError:
            pass
    return Scheduler(**kwargs)


# =============================================================================
# REVIEW LOG REPLAY
# =============================================================================

_replay_cache: dict = {}


def _db_token():
    try:
        return os.path.getmtime(get_db_path())
    except OSError:
        return None


def replay_reviews(deck_id: int | None = None) -> pd.DataFrame:
    """
    Replay the full review history through FSRS, card by card.

    Returns one row per genuine review (types 0-3, ease 1-4, card still in
    collection) with columns:
        cid, did, ts, rating, review_type, elapsed_days,
        predicted_r  (retrievability just before this review; NaN on first),
        s_before, s_after, d_after,
        decay, factor (forgetting-curve constants of the card's preset)
    """
    cache_key = (_db_token(), deck_id)
    if _replay_cache.get('key') == cache_key:
        return _replay_cache['df']

    deck_configs = get_deck_fsrs_configs()
    schedulers = {}  # params tuple -> Scheduler
    for cfg in deck_configs.values():
        params = cfg['params']
        if params not in schedulers:
            schedulers[params] = _make_scheduler(params)
    default_scheduler = _make_scheduler(None)

    conn = connect_db()
    deck_filter = f'AND c.did = {int(deck_id)}' if deck_id is not None else ''
    rows = conn.execute(f"""
        SELECT r.id, r.cid, r.ease, r.type, c.did
        FROM revlog r
        JOIN cards c ON r.cid = c.id
        WHERE r.type IN (0, 1, 2, 3)
          AND r.ease BETWEEN 1 AND 4
          {deck_filter}
        ORDER BY r.cid, r.id
    """).fetchall()
    conn.close()

    cols = {name: [] for name in (
        'cid', 'did', 'ts', 'rating', 'review_type', 'elapsed_days',
        'predicted_r', 's_before', 's_after', 'd_after', 'decay', 'factor')}

    card = None
    current_cid = None
    scheduler = default_scheduler
    decay = factor = np.nan

    for rid, cid, ease, rtype, did in rows:
        if cid != current_cid:
            current_cid = cid
            card = Card(card_id=cid)
            cfg = deck_configs.get(did)
            scheduler = schedulers.get(cfg['params'], default_scheduler) if cfg else default_scheduler
            # FSRS-6 forgetting curve: R(t) = (1 + factor * t/S) ** decay
            w20 = scheduler.parameters[20]
            decay = -w20
            factor = 0.9 ** (1.0 / decay) - 1.0

        ts = datetime.fromtimestamp(rid / 1000, tz=timezone.utc)

        if card.last_review is not None:
            elapsed = (ts - card.last_review).total_seconds() / 86400.0
            predicted_r = scheduler.get_card_retrievability(card, ts)
        else:
            elapsed = np.nan
            predicted_r = np.nan

        s_before = card.stability if card.stability is not None else np.nan
        card, _ = scheduler.review_card(card, Rating(ease), ts)

        cols['cid'].append(cid)
        cols['did'].append(did)
        cols['ts'].append(rid // 1000)
        cols['rating'].append(ease)
        cols['review_type'].append(rtype)
        cols['elapsed_days'].append(elapsed)
        cols['predicted_r'].append(predicted_r)
        cols['s_before'].append(s_before)
        cols['s_after'].append(card.stability)
        cols['d_after'].append(card.difficulty)
        cols['decay'].append(decay)
        cols['factor'].append(factor)

    df = pd.DataFrame(cols)
    _replay_cache['key'] = cache_key
    _replay_cache['df'] = df
    return df


# =============================================================================
# KNOWN WORDS (expected vocabulary) TIME SERIES
# =============================================================================

def get_known_words_timeseries(deck_id: int | None = None) -> pd.DataFrame:
    """
    Expected number of currently-recallable cards over time:
    for each day d, sum of retrievability R(d) over every card seen so far.

    Returns DataFrame with columns: date, expected_known, cards_seen, known_pct
    """
    df = replay_reviews(deck_id)
    if df.empty:
        return pd.DataFrame(columns=['date', 'expected_known', 'cards_seen', 'known_pct'])

    first_day = pd.Timestamp(datetime.fromtimestamp(df['ts'].min()).date())
    today = pd.Timestamp(datetime.now().date())
    dates = pd.date_range(first_day, today, freq='D')
    # Evaluate at local midnight of each day, in epoch seconds
    day_ts = dates.map(lambda d: d.timestamp()).to_numpy(dtype=np.float64)
    n_days = len(dates)

    known = np.zeros(n_days)
    seen = np.zeros(n_days, dtype=np.int64)

    ts_arr = df['ts'].to_numpy(dtype=np.float64)
    s_arr = df['s_after'].to_numpy(dtype=np.float64)
    cid_arr = df['cid'].to_numpy()
    decay_arr = df['decay'].to_numpy(dtype=np.float64)
    factor_arr = df['factor'].to_numpy(dtype=np.float64)

    # Card boundaries (rows are sorted by cid, ts)
    boundaries = np.flatnonzero(np.r_[True, cid_arr[1:] != cid_arr[:-1], True])

    for b in range(len(boundaries) - 1):
        lo, hi = boundaries[b], boundaries[b + 1]
        for i in range(lo, hi):
            seg_start_ts = ts_arr[i]
            seg_end_ts = ts_arr[i + 1] if i + 1 < hi else np.inf
            stability = s_arr[i]
            if not stability > 0:
                continue
            # Grid days strictly after this review, up to (excluding) the next
            start_idx = np.searchsorted(day_ts, seg_start_ts, side='right')
            end_idx = np.searchsorted(day_ts, seg_end_ts, side='right') if np.isfinite(seg_end_ts) else n_days
            if start_idx >= end_idx:
                continue
            t = (day_ts[start_idx:end_idx] - seg_start_ts) / 86400.0
            known[start_idx:end_idx] += (1.0 + factor_arr[i] * t / stability) ** decay_arr[i]
            seen[start_idx:end_idx] += 1

    result = pd.DataFrame({
        'date': dates,
        'expected_known': known,
        'cards_seen': seen,
    })
    result['known_pct'] = np.where(seen > 0, known / np.maximum(seen, 1) * 100, 0.0)
    return result


# =============================================================================
# PLANNING: RETENTION <-> WORKLOAD, COMPLETION PROJECTION
# =============================================================================

def get_retention_workload_curve(deck_id: int | None = None) -> dict:
    """
    Sweep desired retention and compute the equilibrium review workload it
    implies for the current collection: Σ 1/interval_i(R_d), where each
    card's next interval comes from its stability and its preset's
    forgetting curve: I(R_d, S) = S/factor * (R_d^(1/decay) - 1).

    Returns {'curve': DataFrame[retention, reviews_per_day, avg_interval],
             'current_retention': float, 'n_cards': int}
    """
    import json

    deck_configs = get_deck_fsrs_configs()

    conn = connect_db()
    deck_filter = f'AND c.did = {int(deck_id)}' if deck_id is not None else ''
    rows = conn.execute(f"""
        SELECT c.did, c.data FROM cards c
        WHERE c.queue = 2 AND c.data IS NOT NULL AND c.data != ''
          {deck_filter}
    """).fetchall()
    conn.close()

    stabilities, decays = [], []
    retentions_cfg = []
    for did, data_json in rows:
        try:
            data = json.loads(data_json)
        except (ValueError, TypeError):
            continue
        s = data.get('s')
        if not s or s <= 0:
            continue
        cfg = deck_configs.get(did) or {'params': None, 'desired_retention': 0.9}
        params = cfg['params']
        w20 = params[20] if params else 0.1542  # py-fsrs default decay param
        stabilities.append(s)
        decays.append(-w20)
        retentions_cfg.append(cfg['desired_retention'])

    if not stabilities:
        return {'curve': pd.DataFrame(columns=['retention', 'reviews_per_day', 'avg_interval']),
                'current_retention': 0.9, 'n_cards': 0}

    s_arr = np.array(stabilities)
    decay_arr = np.array(decays)
    factor_arr = 0.9 ** (1.0 / decay_arr) - 1.0

    grid = np.round(np.arange(0.70, 0.971, 0.005), 3)
    loads, avg_ivls = [], []
    for r_d in grid:
        ivl = s_arr / factor_arr * (r_d ** (1.0 / decay_arr) - 1.0)
        ivl = np.clip(ivl, 1.0, None)
        loads.append(float(np.sum(1.0 / ivl)))
        avg_ivls.append(float(np.mean(ivl)))

    curve = pd.DataFrame({
        'retention': grid,
        'reviews_per_day': loads,
        'avg_interval': avg_ivls,
    })
    # Collection-level current setting: the modal preset value
    current_retention = float(pd.Series(retentions_cfg).mode().iloc[0])

    return {'curve': curve, 'current_retention': current_retention, 'n_cards': len(s_arr)}


# =============================================================================
# FORWARD SIMULATION (FSRS simulator)
# =============================================================================

def _load_sim_cards(deck_id: int | None) -> tuple[list[dict], int]:
    """
    Snapshot the current review/learning cards as plain dicts (stability,
    difficulty, due datetime, last_review datetime) plus the count of
    available new cards. Suspended and already-new cards are excluded from
    the review set; new-card pool = non-suspended queue==0 cards.
    """
    conn = connect_db()
    collection_start = get_collection_start_date()
    deck_filter = f'AND c.did = {int(deck_id)}' if deck_id is not None else ''

    rows = conn.execute(f"""
        SELECT c.id, c.data, c.queue, c.due, c.type
        FROM cards c
        WHERE c.queue IN (1, 2, 3)
          AND c.data IS NOT NULL AND c.data != ''
          {deck_filter}
    """).fetchall()
    new_count = conn.execute(
        f"SELECT COUNT(*) FROM cards c WHERE c.queue = 0 {deck_filter}").fetchone()[0]
    conn.close()

    cards = []
    for cid, data_json, queue, due, ctype in rows:
        try:
            data = json.loads(data_json)
        except (ValueError, TypeError):
            continue
        s, d = data.get('s'), data.get('d')
        if not s or not d or s <= 0:
            continue
        lrt = data.get('lrt', 0)
        last_review = datetime.fromtimestamp(lrt, tz=timezone.utc) if lrt else None
        if queue == 2:
            due_dt = collection_start.replace(tzinfo=timezone.utc) + timedelta(days=int(due))
        else:  # learning / relearning: due is an epoch timestamp
            due_dt = datetime.fromtimestamp(int(due), tz=timezone.utc)
        cards.append({'s': float(s), 'd': float(d), 'due': due_dt, 'last_review': last_review})

    return cards, int(new_count)


def get_deck_sim_defaults(deck_id: int | None = None) -> dict:
    """
    Simulator input defaults drawn from the deck's Anki preset:
    desired retention (%), new cards/day, and reviews/day limit.
    """
    cfg = get_deck_fsrs_configs().get(deck_id) if deck_id is not None else None
    if not cfg:
        return {'retention': 90, 'new_per_day': 20, 'rev_per_day': 200}
    return {
        'retention': round(cfg['desired_retention'] * 100),
        'new_per_day': cfg['new_per_day'],
        'rev_per_day': cfg['rev_per_day'],
    }


def get_rating_distributions(deck_id: int | None = None) -> tuple[list[float], list[float]]:
    """
    Rating probabilities measured from the deck's own revlog, mirroring how
    Anki's simulator personalizes the forecast:
      - first_prob:   [Again, Hard, Good, Easy] on a card's first exposure
      - success_prob: [Hard, Good, Easy] given a non-lapse on later reviews
    Falls back to Anki's generic defaults when data is sparse (<100 reviews).
    """
    conn = connect_db()
    deck_filter = f'AND c.did = {int(deck_id)}' if deck_id is not None else ''
    first = dict(conn.execute(f"""
        SELECT r.ease, COUNT(*) FROM revlog r JOIN cards c ON r.cid = c.id
        WHERE r.type = 0 AND r.ease BETWEEN 1 AND 4 {deck_filter} GROUP BY r.ease
    """).fetchall())
    succ = dict(conn.execute(f"""
        SELECT r.ease, COUNT(*) FROM revlog r JOIN cards c ON r.cid = c.id
        WHERE r.type = 1 AND r.ease BETWEEN 2 AND 4 {deck_filter} GROUP BY r.ease
    """).fetchall())
    conn.close()

    ft = sum(first.get(e, 0) for e in (1, 2, 3, 4))
    first_prob = ([first.get(e, 0) / ft for e in (1, 2, 3, 4)]
                  if ft >= 100 else [0.24, 0.094, 0.495, 0.171])
    st = sum(succ.get(e, 0) for e in (2, 3, 4))
    success_prob = ([succ.get(e, 0) / st for e in (2, 3, 4)]
                    if st >= 100 else [0.224, 0.631, 0.145])
    return first_prob, success_prob


def simulate_future(
    deck_id: int | None = None,
    days: int = 365,
    desired_retention: float = 0.9,
    new_per_day: int = 0,
    max_reviews: int = 9999,
    additional_new: int = 0,
    n_runs: int = 3,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Monte-Carlo forward simulation of the FSRS scheduler for the current
    collection, mirroring Anki's FSRS simulator.

    Each simulated day: due cards (capped at max_reviews) are reviewed —
    passed with probability equal to their current retrievability, failed
    otherwise — and new cards are introduced up to new_per_day. Learning
    steps collapse within the day. 'Memorized' is Σ retrievability across
    all introduced cards (same metric as the known-words chart), so the
    projection continues that curve smoothly.

    Returns DataFrame: date, memorized, reviews_per_day (means over runs).
    """
    cfg = get_deck_fsrs_configs().get(deck_id) if deck_id is not None else None
    params = cfg['params'] if cfg else None
    scheduler = _make_scheduler(
        params,
        learn_steps=cfg['learn_steps'] if cfg else None,
        relearn_steps=cfg['relearn_steps'] if cfg else None,
    )
    scheduler.desired_retention = float(desired_retention)

    # Forgetting-curve constants for the vectorized 'memorized' sum
    decay = -scheduler.parameters[20]
    factor = 0.9 ** (1.0 / decay) - 1.0

    base_cards, new_count = _load_sim_cards(deck_id)
    pool0 = new_count + int(additional_new)

    start = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)
    mem_acc = np.zeros(days)
    rev_acc = np.zeros(days)

    # Rating distributions measured from the deck's own revlog (like Anki),
    # falling back to generic defaults when data is sparse.
    FIRST = [Rating.Again, Rating.Hard, Rating.Good, Rating.Easy]
    SUCCESS = [Rating.Hard, Rating.Good, Rating.Easy]
    FIRST_P, SUCCESS_P = get_rating_distributions(deck_id)

    def sample_review_rating(rng, r):
        """Again on lapse (prob 1-r); else Hard/Good/Easy per Anki weights."""
        if rng.random() >= r:
            return Rating.Again
        return rng.choices(SUCCESS, SUCCESS_P)[0]

    for run in range(n_runs):
        rng = random.Random(seed + run)
        # Fresh mutable card objects for this run
        cards = [Card(stability=c['s'], difficulty=c['d'], state=State.Review,
                      due=c['due'], last_review=c['last_review']) for c in base_cards]
        pool = pool0

        for day in range(days):
            date = start + timedelta(days=day)
            day_ts = date.timestamp()
            day_end = date.date()
            budget = max_reviews
            reviews_today = 0

            # fsrs-rs priority: due ascending, then by difficulty. Over-limit
            # cards are postponed to the *next* day (due = day+1) rather than
            # kept at their old due — so they don't jump the queue, and a
            # persistent backlog builds under sustained overload.
            next_day = start + timedelta(days=day + 1)
            due_idx = [i for i, c in enumerate(cards) if c.due.date() <= day_end]
            due_idx.sort(key=lambda i: (cards[i].due, cards[i].difficulty or 0.0))

            for i in due_idx:
                if budget <= 0:
                    # Postpone the remaining due cards to tomorrow.
                    c = cards[i]
                    cards[i] = Card(card_id=c.card_id, state=c.state, step=c.step,
                                    stability=c.stability, difficulty=c.difficulty,
                                    due=next_day, last_review=c.last_review)
                    continue
                guard = 0
                while cards[i].due.date() <= day_end and budget > 0 and guard < 12:
                    c = cards[i]
                    r = scheduler.get_card_retrievability(c, date)
                    cards[i], _ = scheduler.review_card(c, sample_review_rating(rng, r), date)
                    budget -= 1
                    reviews_today += 1
                    guard += 1

            # Introduce new cards. Their learning reps are tracked separately
            # from reviews_today (Anki counts learning apart from reviews and
            # never lets the reviews line exceed the review limit).
            n_new = min(new_per_day, pool)
            for _ in range(n_new):
                c = Card()
                guard = 0
                while guard < 12:
                    if c.stability is None:
                        rating = rng.choices(FIRST, FIRST_P)[0]
                    else:
                        rating = sample_review_rating(rng, scheduler.get_card_retrievability(c, date))
                    c, _ = scheduler.review_card(c, rating, date)
                    guard += 1
                    if c.due.date() > day_end:
                        break
                cards.append(c)
                pool -= 1

            # Vectorized 'memorized' = Σ retrievability over reviewed cards
            stabs = np.fromiter((c.stability for c in cards if c.stability), dtype=np.float64)
            if stabs.size:
                lrs = np.fromiter((c.last_review.timestamp() for c in cards if c.stability),
                                  dtype=np.float64)
                t = np.maximum((day_ts - lrs) / 86400.0, 0.0)
                mem_acc[day] += np.sum((1.0 + factor * t / stabs) ** decay)
            rev_acc[day] += reviews_today

    dates = [(start + timedelta(days=d)).date() for d in range(days)]
    return pd.DataFrame({
        'date': pd.to_datetime(dates),
        'memorized': mem_acc / n_runs,
        'reviews_per_day': rev_acc / n_runs,
    })


# =============================================================================
# SESSION FATIGUE
# =============================================================================

def get_fatigue_curve(
    deck_id: int | None = None,
    gap_minutes: int = 30,
    bin_size: int = 10,
    max_position: int = 120,
    min_bin_n: int = 50,
) -> pd.DataFrame:
    """
    Accuracy and answer time as a function of position within a study
    session (sessions split on >gap_minutes idle). Reveals whether recall
    degrades after N cards in one sitting.

    Returns DataFrame: position (bin center), success_rate, ci_low,
    ci_high, avg_time_s, n
    """
    conn = connect_db()
    deck_filter = f'AND c.did = {int(deck_id)}' if deck_id is not None else ''
    df = pd.read_sql_query(f"""
        SELECT r.id / 1000 AS ts, r.ease, r.time AS time_ms
        FROM revlog r
        JOIN cards c ON r.cid = c.id
        WHERE r.type IN (0, 1, 2, 3)
          AND r.ease BETWEEN 1 AND 4
          {deck_filter}
        ORDER BY r.id
    """, conn)
    conn.close()

    if df.empty:
        return pd.DataFrame(columns=['position', 'success_rate', 'ci_low', 'ci_high', 'avg_time_s', 'n'])

    session_id = (df['ts'].diff() > gap_minutes * 60).cumsum()
    df['position'] = df.groupby(session_id).cumcount() + 1
    df = df[df['position'] <= max_position].copy()
    df['recalled'] = (df['ease'] >= 2).astype(float)
    df['bin'] = (df['position'] - 1) // bin_size

    grouped = df.groupby('bin').agg(
        successes=('recalled', 'sum'),
        n=('recalled', 'size'),
        avg_time_s=('time_ms', lambda t: t.mean() / 1000.0),
        time_std_s=('time_ms', lambda t: t.std() / 1000.0),
    ).reset_index()
    grouped = grouped[grouped['n'] >= min_bin_n].copy()
    if grouped.empty:
        return pd.DataFrame(columns=['position', 'success_rate', 'ci_low', 'ci_high',
                                     'avg_time_s', 'time_ci_low', 'time_ci_high', 'n'])

    grouped['position'] = grouped['bin'] * bin_size + bin_size / 2
    grouped['success_rate'] = grouped['successes'] / grouped['n'] * 100
    ci_low, ci_high = _wilson_interval(
        grouped['successes'].to_numpy(), grouped['n'].to_numpy())
    grouped['ci_low'] = ci_low * 100
    grouped['ci_high'] = ci_high * 100

    # 95% CI for the mean answer time (normal approx; bins are large)
    sem = grouped['time_std_s'] / np.sqrt(grouped['n'])
    grouped['time_ci_low'] = (grouped['avg_time_s'] - 1.96 * sem).clip(lower=0)
    grouped['time_ci_high'] = grouped['avg_time_s'] + 1.96 * sem

    return grouped[['position', 'success_rate', 'ci_low', 'ci_high',
                    'avg_time_s', 'time_ci_low', 'time_ci_high', 'n']]


# =============================================================================
# COHORT LEARNING CURVES
# =============================================================================

# =============================================================================
# MODEL CALIBRATION
# =============================================================================

def _wilson_interval(successes: np.ndarray, n: np.ndarray, z: float = 1.96):
    """Wilson score interval for binomial proportions (vectorized)."""
    p = successes / n
    denom = 1.0 + z ** 2 / n
    center = (p + z ** 2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / denom
    return center - half, center + half


def get_calibration_data(deck_id: int | None = None, n_bins: int = 15) -> pd.DataFrame:
    """
    Bin reviews by FSRS-predicted retrievability and compare against
    observed recall. Same-day reviews are excluded (learning steps, where
    the power forgetting curve does not apply), matching FSRS evaluation
    practice.

    Returns DataFrame with columns:
        predicted (bin mean), observed, n, ci_low, ci_high
    """
    df = replay_reviews(deck_id)
    if df.empty:
        return pd.DataFrame(columns=['predicted', 'observed', 'n', 'ci_low', 'ci_high'])

    mask = df['predicted_r'].notna() & (df['elapsed_days'] >= 1.0)
    sample = df.loc[mask, ['predicted_r', 'rating']].copy()
    if len(sample) < 50:
        return pd.DataFrame(columns=['predicted', 'observed', 'n', 'ci_low', 'ci_high'])

    sample['recalled'] = (sample['rating'] >= 2).astype(float)
    # Equal-count bins so sparse regions get wide bins instead of noise
    sample['bin'] = pd.qcut(sample['predicted_r'], q=n_bins, duplicates='drop')

    grouped = sample.groupby('bin', observed=True).agg(
        predicted=('predicted_r', 'mean'),
        observed=('recalled', 'mean'),
        n=('recalled', 'size'),
        successes=('recalled', 'sum'),
    ).reset_index(drop=True)

    ci_low, ci_high = _wilson_interval(
        grouped['successes'].to_numpy(), grouped['n'].to_numpy())
    grouped['ci_low'] = ci_low
    grouped['ci_high'] = ci_high

    return grouped[['predicted', 'observed', 'n', 'ci_low', 'ci_high']]


def get_calibration_summary(deck_id: int | None = None) -> dict:
    """Overall calibration verdict: mean predicted vs observed recall."""
    df = replay_reviews(deck_id)
    if df.empty:
        return {'n': 0, 'mean_predicted': 0.0, 'mean_observed': 0.0, 'gap_pp': 0.0}

    mask = df['predicted_r'].notna() & (df['elapsed_days'] >= 1.0)
    sample = df.loc[mask]
    if sample.empty:
        return {'n': 0, 'mean_predicted': 0.0, 'mean_observed': 0.0, 'gap_pp': 0.0}

    mean_pred = float(sample['predicted_r'].mean())
    mean_obs = float((sample['rating'] >= 2).mean())
    return {
        'n': int(len(sample)),
        'mean_predicted': mean_pred,
        'mean_observed': mean_obs,
        'gap_pp': (mean_obs - mean_pred) * 100,  # + means FSRS underestimates you
    }


