#!/usr/bin/env python3
"""
Data Layer for Anki Dashboard
Consolidates all database access, FSRS calculations, and data transformations
"""

import sqlite3
import pandas as pd
import numpy as np
import json
import math
from datetime import datetime, timedelta

from src.config import get_db_path


def connect_db():
    """Connect to the Anki database"""
    return sqlite3.connect(get_db_path())


def calculate_retrievability(stability: float, days_since_review: float) -> float:
    """
    Calculate FSRS retrievability using the standard formula:
    R = exp(ln(0.9) * days_since_review / stability)
    """
    if stability <= 0 or days_since_review < 0:
        return 0.0
    return math.exp(math.log(0.9) * days_since_review / stability)


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
            CAST(strftime('%H', datetime(r.id/1000, 'unixepoch', 'localtime')) AS INTEGER) as session_hour,
            COUNT(*) as total_cards,
            COUNT(CASE WHEN r.type = 0 THEN 1 END) as new_cards,
            COUNT(CASE WHEN r.type = 1 THEN 1 END) as review_cards,
            COUNT(CASE WHEN r.type = 2 THEN 1 END) as relearn_cards,
            SUM(CASE WHEN r.ease >= 2 THEN 1 ELSE 0 END) as successful_cards,
            SUM(CASE WHEN r.ease < 2 THEN 1 ELSE 0 END) as failed_cards,
            AVG(r.time)/1000.0 as avg_time_per_card,
            SUM(r.time)/1000.0/60.0 as total_session_minutes,
            MIN(r.id/1000) as session_start_timestamp,
            MAX(r.id/1000) as session_end_timestamp
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

    # Calculate derived metrics
    df['date'] = pd.to_datetime(df['session_date'])
    df['success_rate'] = (df['successful_cards'] / df['total_cards'] * 100).round(1)
    df['cards_per_minute'] = (df['total_cards'] / df['total_session_minutes']).replace([np.inf, -np.inf], 0)
    df['new_card_ratio'] = (df['new_cards'] / df['total_cards'] * 100).round(1)
    df['session_duration'] = (df['session_end_timestamp'] - df['session_start_timestamp']) / 60.0

    # Efficiency score: success per time spent
    df['efficiency_score'] = np.where(
        (df['total_cards'] > 0) & (df['avg_time_per_card'] > 0),
        df['successful_cards'] / df['total_cards'] / (df['avg_time_per_card'] / 10),
        0
    )

    return df


def get_hourly_stats(review_days: int | None = None, deck_id: int | None = None) -> pd.DataFrame:
    """Get aggregated statistics by hour of day"""
    conn = connect_db()

    review_filter = build_time_filter(review_days)
    deck_filter = build_deck_filter(deck_id)

    query = f"""
        SELECT
            CAST(strftime('%H', datetime(r.id/1000, 'unixepoch', 'localtime')) AS INTEGER) as hour,
            AVG(r.time)/1000.0 as avg_time_seconds,
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
            SUM(CASE WHEN r.ease >= 2 THEN 1 ELSE 0 END) as daily_success,
            SUM(r.time)/1000.0/60.0 as daily_minutes
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

def get_card_data(include_suspended: bool = True, deck_id: int | None = None) -> pd.DataFrame:
    """
    Get comprehensive card-level data with FSRS parameters.

    Parameters:
        include_suspended: Whether to include suspended cards (default True, matching Anki)
        deck_id: Only include cards from this deck (None = all decks)

    Returns:
        DataFrame with card-level statistics and FSRS metrics
    """
    conn = connect_db()
    cursor = conn.cursor()

    current_time = datetime.now()
    current_timestamp_ms = int(current_time.timestamp() * 1000)
    collection_start = get_collection_start_date()

    suspend_filter = "" if include_suspended else "AND c.queue != -1"
    deck_filter = build_deck_filter(deck_id)

    query = f"""
        SELECT
            c.id,
            c.data,
            c.type,
            c.queue,
            c.reps,
            c.lapses,
            c.ivl,
            c.due
        FROM cards c
        WHERE c.data IS NOT NULL
          AND c.data != ""
          AND c.type IN (1, 2)
          {suspend_filter}
          {deck_filter}
    """

    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    # Build lists for each column to avoid pandas conversion issues
    ids = []
    stabilities = []
    difficulties = []
    retrievabilities = []
    days_since_reviews = []
    reps_list = []
    lapses_list = []
    intervals = []
    dues = []
    days_overdues = []
    is_suspendeds = []
    card_types = []

    for row in rows:
        card_id, data_json, card_type, queue, reps, lapses, ivl, due = row
        fsrs = parse_fsrs_data(data_json)

        if fsrs and 's' in fsrs and 'd' in fsrs:
            stability = fsrs['s']
            difficulty = fsrs['d']
            last_review_time_sec = fsrs.get('lrt', 0)

            if last_review_time_sec > 0:
                days_since_review = (current_timestamp_ms / 1000 - last_review_time_sec) / 86400
            else:
                days_since_review = 0

            retrievability = calculate_retrievability(stability, days_since_review) * 100

            # Calculate scheduled date and overdue status
            scheduled_date = collection_start + timedelta(days=due)
            days_overdue = (current_time - scheduled_date).days

            ids.append(int(card_id))
            stabilities.append(float(stability))
            difficulties.append(float(difficulty))
            retrievabilities.append(float(retrievability))
            days_since_reviews.append(float(days_since_review))
            reps_list.append(int(reps))
            lapses_list.append(int(lapses))
            intervals.append(int(ivl))
            dues.append(int(due))
            days_overdues.append(int(days_overdue))
            is_suspendeds.append(queue == -1)
            card_types.append('Learning' if card_type == 1 else 'Review')

    if not ids:
        return pd.DataFrame(columns=[
            'id', 'stability', 'difficulty', 'retrievability', 'days_since_review',
            'reps', 'lapses', 'interval', 'due', 'days_overdue', 'is_suspended', 'card_type'
        ])

    return pd.DataFrame({
        'id': ids,
        'stability': stabilities,
        'difficulty': difficulties,
        'retrievability': retrievabilities,
        'days_since_review': days_since_reviews,
        'reps': reps_list,
        'lapses': lapses_list,
        'interval': intervals,
        'due': dues,
        'days_overdue': days_overdues,
        'is_suspended': is_suspendeds,
        'card_type': card_types
    })


# =============================================================================
# SUMMARY STATISTICS
# =============================================================================

def get_overview_stats(deck_id: int | None = None) -> dict:
    """Get high-level overview statistics"""
    conn = connect_db()
    cursor = conn.cursor()

    deck_filter = build_deck_filter(deck_id)

    # Card counts
    cursor.execute(f"""
        SELECT
            COUNT(*) as total_cards,
            SUM(CASE WHEN c.queue = -1 THEN 1 ELSE 0 END) as suspended,
            SUM(CASE WHEN c.type = 0 THEN 1 ELSE 0 END) as new_cards,
            SUM(CASE WHEN c.type = 1 THEN 1 ELSE 0 END) as learning,
            SUM(CASE WHEN c.type = 2 THEN 1 ELSE 0 END) as review
        FROM cards c
        WHERE 1=1
          {deck_filter}
    """)
    card_stats = cursor.fetchone()

    # Review counts (join cards for deck filtering)
    cursor.execute(f"""
        SELECT
            COUNT(*) as total_reviews,
            SUM(r.time)/1000.0/3600.0 as total_hours,
            AVG(r.time)/1000.0 as avg_time_per_review
        FROM revlog r
        JOIN cards c ON r.cid = c.id
        WHERE r.type != 4
          {deck_filter}
    """)
    review_stats = cursor.fetchone()

    # Date range
    cursor.execute(f"""
        SELECT
            MIN(r.id/1000) as first_review,
            MAX(r.id/1000) as last_review
        FROM revlog r
        JOIN cards c ON r.cid = c.id
        WHERE r.type != 4
          {deck_filter}
    """)
    date_stats = cursor.fetchone()

    conn.close()

    first_review = datetime.fromtimestamp(date_stats[0]) if date_stats[0] else None
    last_review = datetime.fromtimestamp(date_stats[1]) if date_stats[1] else None

    return {
        'total_cards': card_stats[0] or 0,
        'suspended_cards': card_stats[1] or 0,
        'new_cards': card_stats[2] or 0,
        'learning_cards': card_stats[3] or 0,
        'review_cards': card_stats[4] or 0,
        'total_reviews': review_stats[0] or 0,
        'total_hours': round(review_stats[1] or 0, 1),
        'avg_time_per_review': round(review_stats[2] or 0, 1),
        'first_review': first_review,
        'last_review': last_review,
        'days_studied': (last_review - first_review).days if first_review and last_review else 0
    }


def get_memory_state_summary(deck_id: int | None = None) -> dict:
    """Get summary of current memory states"""
    cards_df = get_card_data(deck_id=deck_id)

    if cards_df.empty:
        return {
            'total': 0,
            'critical': 0,
            'at_risk': 0,
            'moderate': 0,
            'good': 0,
            'excellent': 0,
            'mean_retrievability': 0.0,
            'median_retrievability': 0.0
        }

    retrievabilities = cards_df['retrievability']

    return {
        'total': len(retrievabilities),
        'critical': int(len(retrievabilities[retrievabilities < 50])),
        'at_risk': int(len(retrievabilities[(retrievabilities >= 50) & (retrievabilities < 70)])),
        'moderate': int(len(retrievabilities[(retrievabilities >= 70) & (retrievabilities < 85)])),
        'good': int(len(retrievabilities[(retrievabilities >= 85) & (retrievabilities < 95)])),
        'excellent': int(len(retrievabilities[retrievabilities >= 95])),
        'mean_retrievability': round(float(retrievabilities.mean()), 1) if len(retrievabilities) > 0 else 0.0,
        'median_retrievability': round(float(retrievabilities.median()), 1) if len(retrievabilities) > 0 else 0.0
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
            params = (cfgs.get(did) or {}).get('params')
            return -(params[20] if params else 0.1542)

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


def get_consistency_stats(review_days: int | None = None, deck_id: int | None = None) -> dict:
    """
    Calculate study consistency statistics: streaks, gaps, and regularity.

    Study days follow Anki's rollover hour (default 4am), so a late-night
    session before the rollover counts toward the previous calendar day —
    matching how Anki assigns reviews to days.

    Returns:
        Dictionary with streak and consistency metrics
    """
    conn = connect_db()

    # Get all study dates, shifted back by the rollover so the day boundary
    # sits at Anki's rollover hour rather than midnight.
    rollover = get_rollover_hour()
    review_filter = build_time_filter(review_days)
    deck_filter = build_deck_filter(deck_id)
    query = f"""
        SELECT DISTINCT date(r.id/1000, 'unixepoch', 'localtime', '-{rollover} hours') as study_date
        FROM revlog r
        JOIN cards c ON r.cid = c.id
        WHERE r.id > 0
          AND r.type != 4
          AND c.queue != -1
          {review_filter}
          {deck_filter}
        ORDER BY study_date
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        return {
            'current_streak': 0,
            'longest_streak': 0,
            'total_study_days': 0,
            'avg_days_per_week': 0.0,
            'best_hour': None
        }

    df['study_date'] = pd.to_datetime(df['study_date']).dt.date
    study_dates = set(df['study_date'])
    # "Today" per the same rollover: before the rollover hour it's still yesterday.
    today = (datetime.now() - timedelta(hours=rollover)).date()

    # Calculate current streak (consecutive days ending today or yesterday)
    current_streak = 0
    check_date = today
    while check_date in study_dates:
        current_streak += 1
        check_date -= timedelta(days=1)

    # If no study today, check if streak was broken (yesterday not studied)
    if today not in study_dates and (today - timedelta(days=1)) in study_dates:
        current_streak = 0
        check_date = today - timedelta(days=1)
        while check_date in study_dates:
            current_streak += 1
            check_date -= timedelta(days=1)

    # Calculate longest streak
    sorted_dates = sorted(study_dates)
    longest_streak = 0
    streak = 1
    for i in range(1, len(sorted_dates)):
        if (sorted_dates[i] - sorted_dates[i-1]).days == 1:
            streak += 1
        else:
            longest_streak = max(longest_streak, streak)
            streak = 1
    longest_streak = max(longest_streak, streak)

    # Calculate avg days per week (last 4 weeks)
    four_weeks_ago = today - timedelta(days=28)
    recent_days = [d for d in study_dates if d >= four_weeks_ago]
    avg_days_per_week = len(recent_days) / 4 if recent_days else 0

    return {
        'current_streak': current_streak,
        'longest_streak': longest_streak,
        'total_study_days': len(study_dates),
        'avg_days_per_week': round(avg_days_per_week, 1)
    }


def get_workload_summary(
    forecast_df: pd.DataFrame | None = None,
    cards_df: pd.DataFrame | None = None,
    deck_id: int | None = None
) -> dict:
    """
    Get summary of upcoming workload for quick stats.

    Returns:
        Dictionary with workload metrics
    """
    if forecast_df is None:
        forecast_df = get_future_load_forecast(30, deck_id=deck_id)
    if cards_df is None:
        cards_df = get_card_data(deck_id=deck_id)

    if forecast_df.empty:
        return {
            'due_this_week': 0,
            'overdue_cards': 0,
            'peak_day': None,
            'peak_day_count': 0,
            'daily_load': 0.0
        }

    # Cards due in next 7 days
    due_this_week = int(forecast_df.head(7)['due_count'].sum())

    # Find peak day in next 30 days
    peak_idx = forecast_df['due_count'].idxmax()
    peak_day = forecast_df.loc[peak_idx, 'date']
    peak_day_count = int(forecast_df.loc[peak_idx, 'due_count'])

    # Overdue cards (days_overdue > 0, excluding suspended)
    overdue_cards = 0
    if not cards_df.empty and 'days_overdue' in cards_df.columns:
        active = cards_df[~cards_df['is_suspended']]
        overdue_cards = int((active['days_overdue'] > 0).sum())

    # Current daily load
    daily_load = calculate_daily_load(deck_id=deck_id)

    return {
        'due_this_week': due_this_week,
        'overdue_cards': overdue_cards,
        'peak_day': peak_day,
        'peak_day_count': peak_day_count,
        'daily_load': daily_load
    }


def get_session_summary_stats(deck_id: int | None = None) -> dict:
    """Streak and average recall rate for the stat strip."""
    session_df = get_session_data(deck_id=deck_id)
    return {
        'avg_success_rate': 0 if session_df.empty else round(float(session_df['success_rate'].mean()), 1),
        'current_streak': get_consistency_stats(deck_id=deck_id)['current_streak'],
    }


def get_future_load_forecast(days_ahead: int = 60, deck_id: int | None = None) -> pd.DataFrame:
    """
    Forecast future review load based on due dates.

    Returns DataFrame with columns: date, due_count, expected_reviews
    """
    conn = connect_db()
    cursor = conn.cursor()

    # Get collection creation date to calculate absolute due dates
    cursor.execute('SELECT crt FROM col')
    collection_timestamp = cursor.fetchone()[0]
    collection_start = datetime.fromtimestamp(collection_timestamp)

    deck_filter = build_deck_filter(deck_id)

    # Get all cards with due dates
    cursor.execute(f"""
        SELECT
            c.due,
            c.queue,
            c.type
        FROM cards c
        WHERE c.queue IN (1, 2)  -- Learning or review
          AND c.due > 0
          {deck_filter}
    """)

    rows = cursor.fetchall()
    conn.close()

    # Calculate due dates
    current_date = datetime.now().date()
    forecast = {}

    for due, queue, card_type in rows:
        if queue == 2:  # Review cards: due is days since collection start
            due_date = (collection_start + timedelta(days=due)).date()
        else:  # Learning cards: due is timestamp
            due_date = datetime.fromtimestamp(due).date()

        days_until = (due_date - current_date).days

        if 0 <= days_until < days_ahead:
            forecast[days_until] = forecast.get(days_until, 0) + 1

    # Create DataFrame with all days
    dates = []
    due_counts = []

    for day in range(days_ahead):
        future_date = current_date + timedelta(days=day)
        dates.append(future_date)
        due_counts.append(forecast.get(day, 0))

    df = pd.DataFrame({
        'date': dates,
        'due_count': due_counts
    })

    # Add 7-day moving average
    df['ma7'] = df['due_count'].rolling(window=7, min_periods=1).mean()

    return df
