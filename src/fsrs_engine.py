"""
FSRS analytics on top of Anki's own backend (the `anki` package).

Per-review memory states, deck presets, the forward simulator and the
retention/workload estimate all come from Anki itself, so they match what
Anki schedules with. This module derives the dashboard's analytics from them:
known-words series, calibration, fatigue. Replay results are cached per
(db mtime, deck_id).
"""

import os
import threading
from contextlib import contextmanager
from datetime import datetime

import numpy as np
import pandas as pd
from anki.collection import Collection
from anki.scheduler_pb2 import SimulateFsrsReviewRequest

from .config import get_db_path
from .data_loader import connect_db, build_deck_filter, DEFAULT_DECAY


# =============================================================================
# ANKI COLLECTION + DECK PRESETS
# =============================================================================

# Anki's backend fails with DBError when two threads open the collection at
# once, and Dash runs callbacks concurrently
_collection_lock = threading.Lock()


@contextmanager
def open_collection():
    """Open data/anki.db with Anki's backend (never creates an empty one)."""
    path = get_db_path()
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    with _collection_lock:
        col = Collection(path)
        try:
            yield col
        finally:
            col.close()


def _fsrs_params(conf: dict) -> list[float]:
    """A preset's FSRS params as FSRS-6's 21 ([] = Anki's defaults)."""
    params = next((list(conf[k]) for k in ('fsrsParams6', 'fsrsParams5', 'fsrsWeights')
                   if conf.get(k)), [])
    if len(params) == 17:
        params += [0.0, 0.0]  # FSRS-4.5 -> FSRS-5: w17, w18
    if len(params) == 19:
        params += [0.0, 0.5]  # FSRS-5 -> FSRS-6: w19 (short-term), w20 (decay)
    return params if len(params) == 21 else []


def get_deck_fsrs_configs() -> dict[int, dict]:
    """
    Map deck_id -> {'decay', 'desired_retention', 'new_per_day',
    'rev_per_day'} from each deck's Anki preset.
    """
    configs = {}
    with open_collection() as col:
        for deck in col.decks.all_names_and_ids():
            conf = col.decks.config_dict_for_deck_id(deck.id)
            params = _fsrs_params(conf)
            configs[deck.id] = {
                'decay': -params[20] if params else DEFAULT_DECAY,
                'desired_retention': conf.get('desiredRetention', 0.9),
                'new_per_day': conf['new']['perDay'],
                'rev_per_day': conf['rev']['perDay'],
            }
    return configs


def _main_config(col, deck_id: int | None) -> dict:
    """The deck's preset; for all decks, the preset of the deck with the most review cards."""
    if deck_id is None:
        deck_id = col.db.scalar(
            "SELECT did FROM cards WHERE queue = 2 GROUP BY did ORDER BY COUNT(*) DESC LIMIT 1") or 1
    return col.decks.config_dict_for_deck_id(deck_id)


def _search(deck_id: int | None) -> str:
    return f'did:{int(deck_id)}' if deck_id is not None else ''


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
    Per-review FSRS memory states as computed by Anki (card info's history).

    Returns one row per genuine review (types 0-3, ease 1-4, card still in
    collection) with columns:
        cid, did, ts, rating, elapsed_days,
        predicted_r  (retrievability just before this review; NaN on first),
        s_after, decay, factor (forgetting-curve constants of the card's preset)
    """
    cache_key = (_db_token(), deck_id)
    if _replay_cache.get('key') == cache_key:
        return _replay_cache['df']

    conn = connect_db()
    cards = conn.execute(f"""
        SELECT c.id, CASE WHEN c.odid THEN c.odid ELSE c.did END
        FROM cards c
        WHERE c.id IN (SELECT cid FROM revlog) {build_deck_filter(deck_id)}
        ORDER BY c.id
    """).fetchall()
    conn.close()

    cols = {name: [] for name in (
        'cid', 'did', 'ts', 'rating', 'elapsed_days',
        'predicted_r', 's_after', 'decay', 'factor')}

    deck_configs = get_deck_fsrs_configs()
    with open_collection() as col:
        for cid, did in cards:
            # FSRS-6 forgetting curve: R(t) = (1 + factor * t/S) ** decay
            decay = deck_configs.get(did, {}).get('decay', DEFAULT_DECAY)
            factor = 0.9 ** (1.0 / decay) - 1.0
            prev_ts = None
            s_before = np.nan
            for e in reversed(col.card_stats_data(cid).revlog):  # oldest first
                if e.review_kind > 3 or not 1 <= e.button_chosen <= 4:
                    continue
                if prev_ts is None:
                    elapsed = predicted_r = np.nan
                else:
                    elapsed = (e.time - prev_ts) / 86400.0
                    predicted_r = (1.0 + factor * elapsed / s_before) ** decay
                s_after = e.memory_state.stability if e.HasField('memory_state') else np.nan

                cols['cid'].append(cid)
                cols['did'].append(did)
                cols['ts'].append(e.time)
                cols['rating'].append(e.button_chosen)
                cols['elapsed_days'].append(elapsed)
                cols['predicted_r'].append(predicted_r)
                cols['s_after'].append(s_after)
                cols['decay'].append(decay)
                cols['factor'].append(factor)
                prev_ts, s_before = e.time, s_after

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
# PLANNING: RETENTION <-> WORKLOAD, FORWARD SIMULATION
# =============================================================================

def get_retention_workload_curve(deck_id: int | None = None) -> dict:
    """
    Anki's retention -> workload estimate (deck options' FSRS "help me
    decide"): simulated review time at each desired retention from 70-99%,
    including the relearning cost of lapses, from the preset's params and
    the deck's own review costs.

    Returns {'curve': DataFrame[retention, relative_workload],
             'current_retention': float}; relative_workload is 1 at the
    preset's current desired retention.
    """
    with open_collection() as col:
        conf = _main_config(col, deck_id)
        costs = col._backend.get_retention_workload(w=_fsrs_params(conf), search=_search(deck_id))
    current = float(conf.get('desiredRetention', 0.9))
    if not costs:
        return {'curve': pd.DataFrame(columns=['retention', 'relative_workload']),
                'current_retention': current}

    cost = pd.Series(costs).sort_index()
    base = np.interp(current * 100, cost.index, cost.to_numpy())
    curve = pd.DataFrame({
        'retention': cost.index.to_numpy() / 100,
        'relative_workload': cost.to_numpy() / base,
    })
    return {'curve': curve, 'current_retention': current}


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


def simulate_future(
    deck_id: int | None = None,
    days: int = 365,
    desired_retention: float = 0.9,
    new_per_day: int = 0,
    max_reviews: int = 9999,
) -> pd.DataFrame:
    """
    Anki's FSRS simulator (deck options -> FSRS -> Simulator), seeded with the
    deck's current cards and using its preset's params, steps and limits;
    rating odds and review costs come from the deck's own review history.
    'Memorized' is Σ retrievability (same metric as the known-words chart);
    reviews exclude new-card learning.

    Returns DataFrame: date, memorized, reviews_per_day.
    """
    with open_collection() as col:
        conf = _main_config(col, deck_id)
        lapse = conf['lapse']
        res = col._backend.simulate_fsrs_review(SimulateFsrsReviewRequest(
            params=_fsrs_params(conf),
            desired_retention=desired_retention,
            deck_size=0,
            days_to_simulate=days,
            new_limit=new_per_day,
            review_limit=max_reviews,
            max_interval=conf['rev']['maxIvl'],
            search=_search(deck_id),
            new_cards_ignore_review_limit=col.get_config('newCardsIgnoreReviewLimit', False),
            easy_days_percentages=conf.get('easyDaysPercentages', []),
            review_order=conf.get('reviewOrder', 0),
            suspend_after_lapse_count=lapse['leechFails'] if lapse.get('leechAction') == 0 else None,
            historical_retention=conf.get('sm2Retention', 0.9),
            learning_step_count=len(conf['new']['delays']),
            relearning_step_count=len(lapse['delays']),
        ))
    return pd.DataFrame({
        'date': pd.date_range(pd.Timestamp(datetime.now().date()), periods=days, freq='D'),
        'memorized': list(res.accumulated_knowledge_acquisition),
        'reviews_per_day': list(res.daily_review_count),
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


