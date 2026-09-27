#!/usr/bin/env python3
"""
Data Layer for Anki Dashboard
Consolidates all database access, FSRS calculations, and data transformations
"""

import sqlite3
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta

from src.config import get_db_path


def connect_db():
    """Connect to the Anki database"""
    return sqlite3.connect(get_db_path())


# FSRS-6 default decay (-w20), for presets without optimized params
DEFAULT_DECAY = -0.1542


def calculate_retrievability(stability: float, days_since_review: float,
                             decay: float = DEFAULT_DECAY) -> float:
    """
    FSRS-6 forgetting curve: R = (1 + factor * t / S) ** decay,
    factor = 0.9 ** (1 / decay) - 1 (so R = 0.9 when t = S).
    """
    if stability <= 0 or days_since_review < 0:
        return 0.0
    factor = 0.9 ** (1.0 / decay) - 1.0
    return (1.0 + factor * days_since_review / stability) ** decay


def parse_fsrs_data(data_json: str) -> dict | None:
    """Parse FSRS JSON data from cards"""
    if not data_json:
        return None
    try:
        return json.loads(data_json)
    except (json.JSONDecodeError, TypeError):
        return None


def get_collection_start_date() -> datetime:
    """Get collection creation date from database"""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('SELECT crt FROM col')
    collection_timestamp = cursor.fetchone()[0]
    conn.close()
    return datetime.fromtimestamp(collection_timestamp)


def get_deck_list() -> list[dict]:
    """Get list of all decks from the database."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM decks')
    decks = [
        {'id': row[0], 'name': row[1].replace('\x1f', '::')}
        for row in cursor.fetchall()
    ]
    conn.close()
    decks.sort(key=lambda d: d['name'].lower())
    return decks


def build_deck_filter(deck_id: int | None = None) -> str:
    """
    Build SQL filter fragment for deck filtering.

    Parameters:
        deck_id: Deck ID to filter by, or None for all decks

    Returns:
        SQL WHERE clause fragment like "AND c.did = 123" or ""
    """
    if deck_id is not None:
        return f"AND c.did = {int(deck_id)}"
    return ""


# =============================================================================
# SESSION DATA
# =============================================================================

def build_time_filter(review_days: int | None = None) -> str:
    """SQL fragment limiting reviews to the last N days ("" for all)."""
    if not review_days:
        return ""
    cutoff_timestamp = (datetime.now() - timedelta(days=review_days)).timestamp()
    return f"AND r.id/1000 >= {cutoff_timestamp}"


def get_session_data(review_days: int | None = None, deck_id: int | None = None) -> pd.DataFrame:
    """
    Extract comprehensive session-based statistics.

    Parameters:
        review_days: Only include reviews from the last N days (None = all)
        deck_id: Only include reviews for cards in this deck (None = all decks)

    Returns:
        DataFrame with session-level statistics
    """
    conn = connect_db()

    # Build review time filter
    review_filter = build_time_filter(review_days)
    deck_filter = build_deck_filter(deck_id)

    query = f"""
        SELECT
            date(r.id/1000, 'unixepoch', 'localtime') as session_date,
            COUNT(*) as total_cards,
            SUM(CASE WHEN r.ease >= 2 THEN 1 ELSE 0 END) as successful_cards,
            SUM(r.time)/1000.0/60.0 as total_session_minutes
        FROM revlog r
        JOIN cards c ON r.cid = c.id
        WHERE r.id > 0
          AND r.type != 4
          AND c.queue != -1
          {review_filter}
          {deck_filter}
        GROUP BY session_date
        HAVING total_cards >= 5
        ORDER BY session_date
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        return df

    df['date'] = pd.to_datetime(df['session_date'])
    df['success_rate'] = (df['successful_cards'] / df['total_cards'] * 100).round(1)
    df['cards_per_minute'] = (df['total_cards'] / df['total_session_minutes']).replace([np.inf, -np.inf], 0)
    return df


def get_hourly_stats(review_days: int | None = None, deck_id: int | None = None) -> pd.DataFrame:
    """Get aggregated statistics by hour of day"""
    conn = connect_db()

    review_filter = build_time_filter(review_days)
    deck_filter = build_deck_filter(deck_id)

    query = f"""
        SELECT
            CAST(strftime('%H', datetime(r.id/1000, 'unixepoch', 'localtime')) AS INTEGER) as hour,
            AVG(CASE WHEN r.ease >= 2 THEN 1.0 ELSE 0.0 END) * 100 as success_rate,
            COUNT(*) as review_count
        FROM revlog r
        JOIN cards c ON r.cid = c.id
        WHERE r.id > 0
          AND r.type != 4
          AND c.queue != -1
          {review_filter}
          {deck_filter}
        GROUP BY hour
        HAVING review_count >= 10
        ORDER BY hour
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    return df


def get_daily_reviews(review_days: int | None = None, deck_id: int | None = None) -> pd.DataFrame:
    """Get daily review statistics"""
    conn = connect_db()

    review_filter = build_time_filter(review_days)
    deck_filter = build_deck_filter(deck_id)

    query = f"""
        SELECT
            date(r.id/1000, 'unixepoch', 'localtime') as review_date,
            COUNT(*) as daily_reviews,
            SUM(CASE WHEN r.ease >= 2 THEN 1 ELSE 0 END) as daily_success
        FROM revlog r
        JOIN cards c ON r.cid = c.id
        WHERE r.id > 0
          AND r.type != 4
          AND c.queue != -1
          {review_filter}
          {deck_filter}
        GROUP BY review_date
        ORDER BY review_date
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    if not df.empty:
        df['date'] = pd.to_datetime(df['review_date'])
        df['success_rate'] = (df['daily_success'] / df['daily_reviews'] * 100).fillna(0)

    return df


# =============================================================================
# CARD DATA
# =============================================================================

def get_card_data(deck_id: int | None = None) -> pd.DataFrame:
    """
    Learning/review cards (suspended included, matching Anki) with FSRS
    memory state from cards.data. Returns DataFrame[stability, difficulty,
    retrievability (%), days_overdue, is_suspended].
    """
    from .fsrs_engine import get_deck_fsrs_configs
    deck_configs = get_deck_fsrs_configs()

    conn = connect_db()
    rows = conn.execute(f"""
        SELECT c.data, c.queue, c.due, CASE WHEN c.odid THEN c.odid ELSE c.did END
        FROM cards c
        WHERE c.data IS NOT NULL
          AND c.data != ""
          AND c.type IN (1, 2)
          {build_deck_filter(deck_id)}
    """).fetchall()
    conn.close()

    now = datetime.now()
    collection_start = get_collection_start_date()
    records = []
    for data_json, queue, due, home_did in rows:
        fsrs = parse_fsrs_data(data_json)
        if not (fsrs and 's' in fsrs and 'd' in fsrs):
            continue
        lrt = fsrs.get('lrt', 0)
        days_since_review = (now.timestamp() - lrt) / 86400 if lrt > 0 else 0
        decay = deck_configs.get(home_did, {}).get('decay', DEFAULT_DECAY)
        records.append((
            float(fsrs['s']),
            float(fsrs['d']),
            calculate_retrievability(fsrs['s'], days_since_review, decay) * 100,
            (now - (collection_start + timedelta(days=due))).days,
            queue == -1,
        ))

    return pd.DataFrame(records, columns=[
        'stability', 'difficulty', 'retrievability', 'days_overdue', 'is_suspended'])


# =============================================================================
# SUMMARY STATISTICS
# =============================================================================

def get_overview_stats(deck_id: int | None = None) -> dict:
    """Review cards, review count, hours studied and days since the first review."""
    deck_filter = build_deck_filter(deck_id)
    conn = connect_db()
    review_cards = conn.execute(
        f"SELECT COUNT(*) FROM cards c WHERE c.type = 2 {deck_filter}").fetchone()[0]
    total_reviews, total_ms, first_ts, last_ts = conn.execute(f"""
        SELECT COUNT(*), SUM(r.time), MIN(r.id/1000), MAX(r.id/1000)
        FROM revlog r
        JOIN cards c ON r.cid = c.id
        WHERE r.type != 4
          {deck_filter}
    """).fetchone()
    conn.close()

    return {
        'review_cards': review_cards,
        'total_reviews': total_reviews,
        'total_hours': round((total_ms or 0) / 3_600_000, 1),
        'days_studied': (datetime.fromtimestamp(last_ts) - datetime.fromtimestamp(first_ts)).days
                        if first_ts else 0,
    }


def get_card_load(deck_id: int | None = None, use_stability: bool = False,
                  with_intro: bool = False) -> pd.DataFrame:
    """
    Per-card current load contribution for review cards. contrib = 1/interval,
    where the interval is either the stored `ivl` (interval mode) or the FSRS
    interval implied by the card's stability at its deck's desired retention
    (stability mode) — more robust after manual/FSRS rescheduling, which
    leaves stored intervals stale.

    Returns DataFrame[did, ivl, lapses, contrib] (+ intro_date if with_intro).
    """
    conn = connect_db()
    deck_filter = build_deck_filter(deck_id)
    if with_intro:
        query = f"""
            SELECT c.did AS did, c.ivl AS ivl, c.lapses AS lapses, c.data AS data,
                   MIN(r.id) / 1000 AS first_ts
            FROM cards c
            JOIN revlog r ON r.cid = c.id
            WHERE c.queue = 2 AND c.ivl > 0 AND c.odid = 0
              AND r.type IN (0, 1, 2, 3)
              {deck_filter}
            GROUP BY c.id
        """
    else:
        query = f"""
            SELECT c.did AS did, c.ivl AS ivl, c.lapses AS lapses, c.data AS data
            FROM cards c
            WHERE c.queue = 2 AND c.ivl > 0 AND c.odid = 0
              {deck_filter}
        """
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        cols = ['did', 'ivl', 'lapses', 'contrib'] + (['intro_date'] if with_intro else [])
        return pd.DataFrame(columns=cols)

    ivl_contrib = 1.0 / df['ivl'].clip(lower=1)
    if use_stability:
        from .fsrs_engine import get_deck_fsrs_configs
        cfgs = get_deck_fsrs_configs()

        def decay_of(did):
            return (cfgs.get(did) or {}).get('decay', DEFAULT_DECAY)

        def rd_of(did):
            return (cfgs.get(did) or {}).get('desired_retention', 0.9)

        s = pd.to_numeric(
            df['data'].apply(lambda j: (parse_fsrs_data(j) or {}).get('s')),
            errors='coerce').to_numpy(dtype=float)
        decay = df['did'].map(decay_of).to_numpy(dtype=float)
        r_d = df['did'].map(rd_of).to_numpy(dtype=float)
        factor = 0.9 ** (1.0 / decay) - 1.0
        with np.errstate(invalid='ignore', divide='ignore'):
            interval = s / factor * (r_d ** (1.0 / decay) - 1.0)
        interval = np.clip(interval, 1.0, None)
        contrib = 1.0 / interval
        # Cards without a parsed stability fall back to the stored interval
        contrib = np.where(np.isfinite(contrib), contrib, ivl_contrib.to_numpy())
    else:
        contrib = ivl_contrib.to_numpy()

    out = pd.DataFrame({
        'did': df['did'], 'ivl': df['ivl'], 'lapses': df['lapses'],
        'contrib': contrib,
    })
    if with_intro:
        out['intro_date'] = pd.to_datetime(df['first_ts'], unit='s').dt.normalize()
    return out


def calculate_daily_load(deck_id: int | None = None,
                         use_stability: bool = False) -> float:
    """
    Daily load: Σ(1/interval) over review cards (the average number of cards
    due per day at steady state). See get_card_load for interval vs stability.
    """
    df = get_card_load(deck_id, use_stability=use_stability)
    return round(float(df['contrib'].sum()) if not df.empty else 0.0, 2)


def get_load_timeseries(deck_id: int | None = None,
                        use_stability: bool = False) -> pd.DataFrame:
    """
    Historical daily load: for each day, Σ(1/interval) over all cards in
    review state on that day, reconstructed from the revlog. Each review
    sets an interval that holds until the card's next review, so a card
    contributes 1/interval from each review until the following one (and 0
    while it sits in learning, where the logged interval is non-positive).

    In stability mode the interval at each review is instead derived from the
    replayed stability (s_after) at that card's deck desired retention.

    Returns DataFrame[date, load].
    """
    if use_stability:
        return _load_timeseries_stability(deck_id)

    conn = connect_db()
    deck_filter = build_deck_filter(deck_id)
    # Restrict to cards that are currently review cards so the series
    # endpoint matches the current daily-load figure (Σ 1/interval).
    # type 4 (manual/FSRS reschedules) are kept here: they change a card's
    # interval and therefore its load, even though they aren't real reviews.
    df = pd.read_sql_query(f"""
        SELECT r.cid, r.id / 1000 AS ts, r.ivl
        FROM revlog r
        JOIN cards c ON r.cid = c.id
        WHERE r.type IN (0, 1, 2, 3, 4)
          AND c.queue = 2 AND c.odid = 0
          {deck_filter}
        ORDER BY r.cid, r.id
    """, conn)
    # Authoritative current contribution per card (stored interval)
    cur = pd.read_sql_query(f"""
        SELECT c.id AS cid, 1.0 / MAX(c.ivl, 1) AS contrib
        FROM cards c
        WHERE c.queue = 2 AND c.ivl > 0 AND c.odid = 0
          {deck_filter}
    """, conn)
    conn.close()

    if df.empty:
        return pd.DataFrame(columns=['date', 'load'])

    # A card's contribution while a given interval is in effect
    df['contrib'] = np.where(df['ivl'] > 0, 1.0 / df['ivl'], 0.0)
    # Load changes at each review by (new contribution − the card's previous)
    df['delta'] = df['contrib'] - df.groupby('cid')['contrib'].shift(fill_value=0.0)
    df['date'] = pd.to_datetime(df['ts'], unit='s').dt.normalize()

    # Reconcile each card's endpoint to its current stored interval, so the
    # series ends exactly at today's daily load even for interval changes
    # that were never written to the revlog.
    today = pd.Timestamp(datetime.now().date())
    last_contrib = df.groupby('cid')['contrib'].last()
    recon = cur.set_index('cid')['contrib'].subtract(last_contrib, fill_value=0.0)
    recon_df = pd.DataFrame({'date': today, 'delta': recon.to_numpy()})

    events = pd.concat([df[['date', 'delta']], recon_df], ignore_index=True)
    daily = events.groupby('date')['delta'].sum().sort_index()
    full = pd.date_range(daily.index.min(), today, freq='D')
    load = daily.reindex(full, fill_value=0.0).cumsum()
    return pd.DataFrame({'date': load.index, 'load': load.to_numpy()})


def _load_timeseries_stability(deck_id: int | None = None) -> pd.DataFrame:
    """
    Stability-based load over time: replay each review and derive its interval
    from the replayed stability (s_after) at the deck desired retention, so the
    series reflects true memory state rather than possibly-stale stored ivls.
    """
    from .fsrs_engine import replay_reviews, get_deck_fsrs_configs

    df = replay_reviews(deck_id)
    if df.empty:
        return pd.DataFrame(columns=['date', 'load'])

    # Restrict to cards that are currently review cards (matches other modes)
    conn = connect_db()
    deck_filter = build_deck_filter(deck_id)
    cur = pd.read_sql_query(f"""
        SELECT c.id AS cid FROM cards c
        WHERE c.queue = 2 AND c.ivl > 0 AND c.odid = 0 {deck_filter}
    """, conn)
    conn.close()
    df = df[df['cid'].isin(set(cur['cid']))].copy()
    if df.empty:
        return pd.DataFrame(columns=['date', 'load'])

    cfgs = get_deck_fsrs_configs()
    r_d = df['did'].map(
        lambda d: (cfgs.get(d) or {}).get('desired_retention', 0.9)).to_numpy(dtype=float)
    decay = df['decay'].to_numpy(dtype=float)
    factor = df['factor'].to_numpy(dtype=float)
    interval = np.clip(
        df['s_after'].to_numpy(dtype=float) / factor * (r_d ** (1.0 / decay) - 1.0),
        1.0, None)
    df['contrib'] = 1.0 / interval

    df = df.sort_values(['cid', 'ts'])
    df['delta'] = df['contrib'] - df.groupby('cid')['contrib'].shift(fill_value=0.0)
    df['date'] = pd.to_datetime(df['ts'], unit='s').dt.normalize()

    today = pd.Timestamp(datetime.now().date())
    daily = df.groupby('date')['delta'].sum().sort_index()
    full = pd.date_range(daily.index.min(), today, freq='D')
    load = daily.reindex(full, fill_value=0.0).cumsum()
    return pd.DataFrame({'date': load.index, 'load': load.to_numpy()})


def get_load_by_introduction(deck_id: int | None = None,
                             use_stability: bool = False) -> pd.DataFrame:
    """
    Per-card current load contribution alongside each card's introduction date
    (its first genuine review). Bucketing by month/quarter or session range is
    done in the chart layer. Returns DataFrame[intro_date, contrib].
    """
    df = get_card_load(deck_id, use_stability=use_stability, with_intro=True)
    if df.empty:
        return pd.DataFrame(columns=['intro_date', 'contrib'])
    return df[['intro_date', 'contrib']]


def get_session_dates(deck_id: int | None = None) -> pd.Series:
    """
    Sorted unique study-session days — days with at least one genuine review
    (types 0-3). Normalised to match the daily series in the load/known-cards
    charts, so a study day can be mapped to a sequential session number.
    """
    conn = connect_db()
    deck_filter = build_deck_filter(deck_id)
    df = pd.read_sql_query(f"""
        SELECT r.id / 1000 AS ts
        FROM revlog r
        JOIN cards c ON r.cid = c.id
        WHERE r.type IN (0, 1, 2, 3)
          {deck_filter}
    """, conn)
    conn.close()

    if df.empty:
        return pd.Series([], dtype='datetime64[ns]')
    return (pd.to_datetime(df['ts'], unit='s').dt.normalize()
            .drop_duplicates().sort_values().reset_index(drop=True))


def get_lapse_load(deck_id: int | None = None,
                   use_stability: bool = False) -> pd.DataFrame:
    """
    Current review load (Σ 1/interval) and card count grouped by a card's
    lapse count — how much of your daily burden comes from cards that keep
    failing. Review cards only. Returns DataFrame[lapses, cards, load].
    """
    df = get_card_load(deck_id, use_stability=use_stability)
    if df.empty:
        return pd.DataFrame(columns=['lapses', 'cards', 'load'])
    return (df.groupby('lapses')
            .agg(cards=('contrib', 'size'), load=('contrib', 'sum'))
            .reset_index().sort_values('lapses').reset_index(drop=True))


def get_rollover_hour(default: int = 4) -> int:
    """Anki's day-rollover hour (reviews before it belong to the previous day)."""
    try:
        conn = connect_db()
        row = conn.execute("SELECT val FROM config WHERE key = 'rollover'").fetchone()
        conn.close()
        if row and row[0] is not None:
            val = row[0].decode() if isinstance(row[0], bytes) else row[0]
            return int(val)
    except Exception:
        pass
    return default


def get_current_streak(deck_id: int | None = None) -> int:
    """
    Consecutive study days ending today (or yesterday, if today has no
    reviews yet). Days follow Anki's rollover hour, so a late-night session
    before the rollover counts toward the previous calendar day.
    """
    rollover = get_rollover_hour()
    conn = connect_db()
    study_dates = {
        datetime.strptime(d, '%Y-%m-%d').date() for (d,) in conn.execute(f"""
            SELECT DISTINCT date(r.id/1000, 'unixepoch', 'localtime', '-{rollover} hours')
            FROM revlog r
            JOIN cards c ON r.cid = c.id
            WHERE r.id > 0
              AND r.type != 4
              AND c.queue != -1
              {build_deck_filter(deck_id)}
        """)
    }
    conn.close()

    day = (datetime.now() - timedelta(hours=rollover)).date()
    if day not in study_dates:
        day -= timedelta(days=1)
    streak = 0
    while day in study_dates:
        streak += 1
        day -= timedelta(days=1)
    return streak


def get_workload_summary(deck_id: int | None = None) -> dict:
    """Cards due in the next 7 days and overdue (non-suspended) cards."""
    forecast_df = get_future_load_forecast(7, deck_id=deck_id)
    cards_df = get_card_data(deck_id=deck_id)
    active = cards_df[~cards_df['is_suspended']]
    return {
        'due_this_week': int(forecast_df['due_count'].sum()),
        'overdue_cards': int((active['days_overdue'] > 0).sum()),
    }


def get_session_summary_stats(deck_id: int | None = None) -> dict:
    """Streak and average recall rate for the stat strip."""
    session_df = get_session_data(deck_id=deck_id)
    return {
        'avg_success_rate': 0 if session_df.empty else round(float(session_df['success_rate'].mean()), 1),
        'current_streak': get_current_streak(deck_id=deck_id),
    }


def get_future_load_forecast(days_ahead: int = 60, deck_id: int | None = None) -> pd.DataFrame:
    """
    Cards due on each of the next `days_ahead` days (learning + review).

    Returns DataFrame with columns: date, due_count, ma7 (7-day moving average)
    """
    conn = connect_db()
    df = pd.read_sql_query(f"""
        SELECT c.due, c.queue
        FROM cards c
        WHERE c.queue IN (1, 2)  -- Learning or review
          AND c.due > 0
          {build_deck_filter(deck_id)}
    """, conn)
    conn.close()

    # Review cards: due is days since collection start; learning: a timestamp
    start = get_collection_start_date()
    today = datetime.now().date()
    days_until = pd.Series([
        ((start + timedelta(days=due)) if queue == 2 else datetime.fromtimestamp(due)).date() - today
        for due, queue in zip(df['due'], df['queue'])
    ], dtype=object).map(lambda d: d.days)
    counts = days_until.value_counts().reindex(range(days_ahead), fill_value=0)
    out = pd.DataFrame({
        'date': [today + timedelta(days=d) for d in range(days_ahead)],
        'due_count': counts.to_numpy(),
    })
    out['ma7'] = out['due_count'].rolling(window=7, min_periods=1).mean()
    return out
