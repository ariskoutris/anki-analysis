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
import os
import sys
from datetime import datetime, timedelta
from functools import lru_cache

# Add parent directory to path for anki_config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from anki_config import get_db_path as get_config_db_path


def get_db_path():
    """Get the path to the decompressed Anki database using the active date from config"""
    return get_config_db_path()


def connect_db():
    """Connect to the decompressed Anki database"""
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


# =============================================================================
# SESSION DATA
# =============================================================================

def build_time_filter(review_days: int | None = None, year_filter: int | None = None) -> str:
    """
    Build SQL filter for time-based queries.

    Parameters:
        review_days: Only include reviews from the last N days
        year_filter: Only include reviews from a specific year

    Returns:
        SQL WHERE clause fragment
    """
    if year_filter:
        # Filter for a specific year
        start_timestamp = datetime(year_filter, 1, 1).timestamp()
        end_timestamp = datetime(year_filter + 1, 1, 1).timestamp()
        return f"AND r.id/1000 >= {start_timestamp} AND r.id/1000 < {end_timestamp}"
    elif review_days:
        cutoff_timestamp = (datetime.now() - timedelta(days=review_days)).timestamp()
        return f"AND r.id/1000 >= {cutoff_timestamp}"
    return ""


def get_session_data(review_days: int | None = None, year_filter: int | None = None) -> pd.DataFrame:
    """
    Extract comprehensive session-based statistics.

    Parameters:
        review_days: Only include reviews from the last N days (None = all)
        year_filter: Only include reviews from a specific year (None = no filter)

    Returns:
        DataFrame with session-level statistics
    """
    conn = connect_db()

    # Build review time filter
    review_filter = build_time_filter(review_days, year_filter)

    query = f"""
        SELECT
            date(r.id/1000, 'unixepoch', 'localtime') as session_date,
            CAST(strftime('%H', datetime(r.id/1000, 'unixepoch', 'localtime')) AS INTEGER) as session_hour,
            COUNT(*) as total_cards,
            COUNT(CASE WHEN r.type = 0 THEN 1 END) as new_cards,
            COUNT(CASE WHEN r.type = 1 THEN 1 END) as review_cards,
            COUNT(CASE WHEN r.type = 2 THEN 1 END) as relearn_cards,
            SUM(CASE WHEN r.ease >= 3 THEN 1 ELSE 0 END) as successful_cards,
            SUM(CASE WHEN r.ease < 3 THEN 1 ELSE 0 END) as failed_cards,
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


def get_hourly_stats(review_days: int | None = None, year_filter: int | None = None) -> pd.DataFrame:
    """Get aggregated statistics by hour of day"""
    conn = connect_db()

    review_filter = build_time_filter(review_days, year_filter)

    query = f"""
        SELECT
            CAST(strftime('%H', datetime(r.id/1000, 'unixepoch', 'localtime')) AS INTEGER) as hour,
            AVG(r.time)/1000.0 as avg_time_seconds,
            AVG(CASE WHEN r.ease >= 3 THEN 1.0 ELSE 0.0 END) * 100 as success_rate,
            COUNT(*) as review_count
        FROM revlog r
        JOIN cards c ON r.cid = c.id
        WHERE r.id > 0
          AND r.type != 4
          AND c.queue != -1
          {review_filter}
        GROUP BY hour
        HAVING review_count >= 10
        ORDER BY hour
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    return df


def get_daily_reviews(review_days: int | None = None, year_filter: int | None = None) -> pd.DataFrame:
    """Get daily review statistics"""
    conn = connect_db()

    review_filter = build_time_filter(review_days, year_filter)

    query = f"""
        SELECT
            date(r.id/1000, 'unixepoch', 'localtime') as review_date,
            COUNT(*) as daily_reviews,
            SUM(CASE WHEN r.ease >= 3 THEN 1 ELSE 0 END) as daily_success,
            SUM(r.time)/1000.0/60.0 as daily_minutes
        FROM revlog r
        JOIN cards c ON r.cid = c.id
        WHERE r.id > 0
          AND r.type != 4
          AND c.queue != -1
          {review_filter}
        GROUP BY review_date
        ORDER BY review_date
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    if not df.empty:
        df['date'] = pd.to_datetime(df['review_date'])
        df['success_rate'] = (df['daily_success'] / df['daily_reviews'] * 100).fillna(0)

    return df


def get_review_intervals(review_days: int | None = None, year_filter: int | None = None) -> pd.DataFrame:
    """Get review success rates by interval (for memory decay curve)"""
    conn = connect_db()

    review_filter = build_time_filter(review_days, year_filter)

    query = f"""
        SELECT
            r.ivl as interval_days,
            AVG(CASE WHEN r.ease >= 3 THEN 1.0 ELSE 0.0 END) * 100 as success_rate,
            COUNT(*) as review_count
        FROM revlog r
        JOIN cards c ON r.cid = c.id
        WHERE r.type = 1
          AND r.ivl > 0
          AND r.ivl <= 365
          AND c.queue != -1
          {review_filter}
        GROUP BY r.ivl
        HAVING review_count >= 3
        ORDER BY r.ivl
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    return df


# =============================================================================
# CARD DATA
# =============================================================================

def get_card_data(include_suspended: bool = False) -> pd.DataFrame:
    """
    Get comprehensive card-level data with FSRS parameters.

    Parameters:
        include_suspended: Whether to include suspended cards

    Returns:
        DataFrame with card-level statistics and FSRS metrics
    """
    conn = connect_db()
    cursor = conn.cursor()

    current_time = datetime.now()
    current_timestamp_ms = int(current_time.timestamp() * 1000)
    collection_start = get_collection_start_date()

    suspend_filter = "" if include_suspended else "AND c.queue != -1"

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


def get_card_review_history(card_id: int) -> pd.DataFrame:
    """Get the review history for a specific card"""
    conn = connect_db()

    query = f"""
        SELECT
            datetime(r.id/1000, 'unixepoch', 'localtime') as review_time,
            r.ease,
            r.ivl,
            r.time/1000.0 as time_seconds,
            r.type
        FROM revlog r
        WHERE r.cid = {card_id}
        ORDER BY r.id
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    if not df.empty:
        df['review_time'] = pd.to_datetime(df['review_time'])

    return df


def get_total_time_per_card() -> pd.DataFrame:
    """Get total time spent on each card"""
    conn = connect_db()

    query = """
        SELECT
            c.id as card_id,
            c.data,
            c.reps,
            c.lapses,
            SUM(r.time)/1000.0 as total_time_seconds,
            COUNT(r.id) as total_reviews
        FROM cards c
        LEFT JOIN revlog r ON c.id = r.cid
        WHERE c.data IS NOT NULL
          AND c.data != ""
          AND c.queue != -1
          AND c.type IN (1, 2)
        GROUP BY c.id
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    # Parse FSRS data and add metrics - using column lists to avoid pandas issues
    card_ids = []
    stabilities = []
    difficulties = []
    retrievabilities = []
    reps_list = []
    lapses_list = []
    total_times = []
    total_reviews_list = []
    avg_times = []

    current_time = datetime.now()
    current_timestamp_ms = int(current_time.timestamp() * 1000)

    for _, row in df.iterrows():
        fsrs = parse_fsrs_data(row['data'])
        if fsrs and 's' in fsrs and 'd' in fsrs:
            stability = fsrs['s']
            difficulty = fsrs['d']
            last_review_time_sec = fsrs.get('lrt', 0)

            if last_review_time_sec > 0:
                days_since_review = (current_timestamp_ms / 1000 - last_review_time_sec) / 86400
            else:
                days_since_review = 0

            retrievability = calculate_retrievability(stability, days_since_review) * 100
            total_time = float(row['total_time_seconds'] or 0)
            total_revs = int(row['total_reviews'] or 0)

            card_ids.append(int(row['card_id']))
            stabilities.append(float(stability))
            difficulties.append(float(difficulty))
            retrievabilities.append(float(retrievability))
            reps_list.append(int(row['reps']))
            lapses_list.append(int(row['lapses']))
            total_times.append(total_time)
            total_reviews_list.append(total_revs)
            avg_times.append(total_time / max(total_revs, 1))

    if not card_ids:
        return pd.DataFrame(columns=[
            'card_id', 'stability', 'difficulty', 'retrievability', 'reps',
            'lapses', 'total_time_seconds', 'total_reviews', 'avg_time_per_review'
        ])

    return pd.DataFrame({
        'card_id': card_ids,
        'stability': stabilities,
        'difficulty': difficulties,
        'retrievability': retrievabilities,
        'reps': reps_list,
        'lapses': lapses_list,
        'total_time_seconds': total_times,
        'total_reviews': total_reviews_list,
        'avg_time_per_review': avg_times
    })


# =============================================================================
# SUMMARY STATISTICS
# =============================================================================

def get_overview_stats() -> dict:
    """Get high-level overview statistics"""
    conn = connect_db()
    cursor = conn.cursor()

    # Card counts
    cursor.execute("""
        SELECT
            COUNT(*) as total_cards,
            SUM(CASE WHEN queue = -1 THEN 1 ELSE 0 END) as suspended,
            SUM(CASE WHEN type = 0 THEN 1 ELSE 0 END) as new_cards,
            SUM(CASE WHEN type = 1 THEN 1 ELSE 0 END) as learning,
            SUM(CASE WHEN type = 2 THEN 1 ELSE 0 END) as review
        FROM cards
    """)
    card_stats = cursor.fetchone()

    # Review counts
    cursor.execute("""
        SELECT
            COUNT(*) as total_reviews,
            SUM(time)/1000.0/3600.0 as total_hours,
            AVG(time)/1000.0 as avg_time_per_review
        FROM revlog
        WHERE type != 4
    """)
    review_stats = cursor.fetchone()

    # Date range
    cursor.execute("""
        SELECT
            MIN(id/1000) as first_review,
            MAX(id/1000) as last_review
        FROM revlog
        WHERE type != 4
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


def get_memory_state_summary() -> dict:
    """Get summary of current memory states"""
    cards_df = get_card_data()

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


def calculate_daily_load() -> float:
    """
    Calculate daily load: sum of 1/stability for all review cards.
    Formula: Σ(1/S_n) where S_n is the FSRS stability (minimum 1 day)

    For FSRS decks, uses stability instead of interval as that's what FSRS uses
    for scheduling. Falls back to interval for non-FSRS cards.

    Returns average number of cards to be reviewed daily (assuming no backlog)
    """
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT c.ivl, c.data
        FROM cards c
        WHERE c.queue = 2  -- Review cards only (not new, learning, suspended, or buried)
          AND c.ivl > 0
          AND c.odid = 0  -- Not in filtered deck
    """)

    daily_load = 0.0
    for ivl, data_json in cursor.fetchall():
        # Try to use FSRS stability if available
        interval_to_use = max(ivl, 1)  # Default to interval

        if data_json:
            try:
                fsrs_data = json.loads(data_json)
                if 's' in fsrs_data and fsrs_data['s'] > 0:
                    # Use FSRS stability (float) instead of interval
                    interval_to_use = max(fsrs_data['s'], 1.0)
            except (json.JSONDecodeError, TypeError):
                pass

        daily_load += 1.0 / interval_to_use

    conn.close()

    return round(daily_load, 2)


def get_daily_load_by_stability() -> pd.DataFrame:
    """Get daily load contribution by stability ranges"""
    cards_df = get_card_data()

    if cards_df.empty:
        return pd.DataFrame()

    # Filter review cards with valid intervals
    review_cards = cards_df[cards_df['interval'] > 0].copy()

    if review_cards.empty:
        return pd.DataFrame()

    # Calculate load contribution per card
    review_cards['interval_safe'] = review_cards['interval'].clip(lower=1)
    review_cards['load_contribution'] = 1.0 / review_cards['interval_safe']

    # Create stability bins
    bins = [0, 7, 30, 90, 180, 365, float('inf')]
    labels = ['<7d', '7-30d', '30-90d', '90-180d', '180-365d', '>365d']
    review_cards['stability_range'] = pd.cut(review_cards['stability'], bins=bins, labels=labels)

    # Group by stability range
    result = review_cards.groupby('stability_range', observed=True).agg({
        'load_contribution': 'sum',
        'id': 'count'
    }).reset_index()
    result.columns = ['stability_range', 'load_contribution', 'card_count']

    return result


def get_daily_load_history(days: int = 90) -> pd.DataFrame:
    """
    Calculate historical daily load over time.
    Uses review log to reconstruct what the daily load was at different points.
    """
    conn = connect_db()

    # Get snapshots of intervals over time from review log
    query = f"""
        WITH date_series AS (
            SELECT date(julianday('now') - n) as check_date
            FROM (
                SELECT 0 as n UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL
                SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL
                SELECT 8 UNION ALL SELECT 9 UNION ALL SELECT 10 UNION ALL SELECT 11 UNION ALL
                SELECT 12 UNION ALL SELECT 13 UNION ALL SELECT 14 UNION ALL SELECT 15 UNION ALL
                SELECT 16 UNION ALL SELECT 17 UNION ALL SELECT 18 UNION ALL SELECT 19 UNION ALL
                SELECT 20 UNION ALL SELECT 21 UNION ALL SELECT 22 UNION ALL SELECT 23 UNION ALL
                SELECT 24 UNION ALL SELECT 25 UNION ALL SELECT 26 UNION ALL SELECT 27 UNION ALL
                SELECT 28 UNION ALL SELECT 29 UNION ALL SELECT 30 UNION ALL SELECT 31 UNION ALL
                SELECT 32 UNION ALL SELECT 33 UNION ALL SELECT 34 UNION ALL SELECT 35 UNION ALL
                SELECT 36 UNION ALL SELECT 37 UNION ALL SELECT 38 UNION ALL SELECT 39 UNION ALL
                SELECT 40 UNION ALL SELECT 41 UNION ALL SELECT 42 UNION ALL SELECT 43 UNION ALL
                SELECT 44 UNION ALL SELECT 45 UNION ALL SELECT 46 UNION ALL SELECT 47 UNION ALL
                SELECT 48 UNION ALL SELECT 49 UNION ALL SELECT 50 UNION ALL SELECT 51 UNION ALL
                SELECT 52 UNION ALL SELECT 53 UNION ALL SELECT 54 UNION ALL SELECT 55 UNION ALL
                SELECT 56 UNION ALL SELECT 57 UNION ALL SELECT 58 UNION ALL SELECT 59 UNION ALL
                SELECT 60 UNION ALL SELECT 61 UNION ALL SELECT 62 UNION ALL SELECT 63 UNION ALL
                SELECT 64 UNION ALL SELECT 65 UNION ALL SELECT 66 UNION ALL SELECT 67 UNION ALL
                SELECT 68 UNION ALL SELECT 69 UNION ALL SELECT 70 UNION ALL SELECT 71 UNION ALL
                SELECT 72 UNION ALL SELECT 73 UNION ALL SELECT 74 UNION ALL SELECT 75 UNION ALL
                SELECT 76 UNION ALL SELECT 77 UNION ALL SELECT 78 UNION ALL SELECT 79 UNION ALL
                SELECT 80 UNION ALL SELECT 81 UNION ALL SELECT 82 UNION ALL SELECT 83 UNION ALL
                SELECT 84 UNION ALL SELECT 85 UNION ALL SELECT 86 UNION ALL SELECT 87 UNION ALL
                SELECT 88 UNION ALL SELECT 89
            )
            LIMIT {days}
        ),
        daily_intervals AS (
            SELECT
                ds.check_date,
                MAX(r.ivl) as interval
            FROM date_series ds
            LEFT JOIN revlog r ON date(r.id/1000, 'unixepoch', 'localtime') <= ds.check_date
            JOIN cards c ON r.cid = c.id
            WHERE r.type = 1  -- Review type
              AND c.queue = 2  -- Review queue
              AND r.ivl > 0
            GROUP BY ds.check_date, r.cid
        )
        SELECT
            check_date as date,
            COUNT(*) as review_card_count,
            SUM(1.0 / MAX(interval, 1)) as daily_load
        FROM daily_intervals
        GROUP BY check_date
        ORDER BY check_date
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])

    return df


def get_consistency_stats(review_days: int | None = None) -> dict:
    """
    Calculate study consistency statistics: streaks, gaps, and regularity.

    Returns:
        Dictionary with streak and consistency metrics
    """
    conn = connect_db()

    # Get all study dates
    review_filter = build_time_filter(review_days)
    query = f"""
        SELECT DISTINCT date(r.id/1000, 'unixepoch', 'localtime') as study_date
        FROM revlog r
        JOIN cards c ON r.cid = c.id
        WHERE r.id > 0
          AND r.type != 4
          AND c.queue != -1
          {review_filter}
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
    today = datetime.now().date()

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


def get_best_study_hour(review_days: int | None = None) -> int | None:
    """Get the hour with highest success rate (min 20 reviews)."""
    hourly_df = get_hourly_stats(review_days)
    if hourly_df.empty:
        return None

    # Filter hours with sufficient data
    qualified = hourly_df[hourly_df['review_count'] >= 20]
    if qualified.empty:
        return None

    best_idx = qualified['success_rate'].idxmax()
    return int(qualified.loc[best_idx, 'hour'])


def get_leech_candidates(min_lapses: int = 3, max_results: int = 20) -> pd.DataFrame:
    """
    Identify problem cards (leeches) based on high lapse count and time wasted.

    Returns DataFrame of cards sorted by "leech score" (time wasted on forgetting).
    """
    time_df = get_total_time_per_card()

    if time_df.empty:
        return pd.DataFrame()

    # Filter to cards with significant lapses
    leeches = time_df[time_df['lapses'] >= min_lapses].copy()

    if leeches.empty:
        return pd.DataFrame()

    # Calculate leech score: time wasted = total_time * (lapses / reps)
    # Higher score = more time spent on cards that keep failing
    leeches['lapse_ratio'] = leeches['lapses'] / leeches['reps'].clip(lower=1)
    leeches['time_wasted_seconds'] = leeches['total_time_seconds'] * leeches['lapse_ratio']
    leeches['leech_score'] = leeches['time_wasted_seconds'] / 60  # Convert to minutes

    # Sort by leech score and take top results
    leeches = leeches.nlargest(max_results, 'leech_score')

    return leeches[['card_id', 'lapses', 'reps', 'total_time_seconds', 'stability',
                    'retrievability', 'lapse_ratio', 'leech_score']]


def get_workload_summary() -> dict:
    """
    Get summary of upcoming workload for quick stats.

    Returns:
        Dictionary with workload metrics
    """
    forecast_df = get_future_load_forecast(30)
    cards_df = get_card_data()

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

    # Overdue cards (days_overdue > 0)
    overdue_cards = 0
    if not cards_df.empty and 'days_overdue' in cards_df.columns:
        overdue_cards = int((cards_df['days_overdue'] > 0).sum())

    # Current daily load
    daily_load = calculate_daily_load()

    return {
        'due_this_week': due_this_week,
        'overdue_cards': overdue_cards,
        'peak_day': peak_day,
        'peak_day_count': peak_day_count,
        'daily_load': daily_load
    }


def get_knowledge_health_stats() -> dict:
    """
    Get summary statistics about knowledge health for section summary cards.

    Returns:
        Dictionary with health metrics
    """
    memory = get_memory_state_summary()
    cards_df = get_card_data()

    if memory['total'] == 0:
        return {
            'health_score': 0,
            'cards_needing_attention': 0,
            'median_retrievability': 0,
            'avg_stability': 0,
            'mature_cards_pct': 0,
            'leech_count': 0
        }

    # Health score: percentage of cards in good or excellent state
    health_score = round((memory['good'] + memory['excellent']) / memory['total'] * 100, 1)

    # Cards needing attention: critical + at_risk
    cards_needing_attention = memory['critical'] + memory['at_risk']

    # Stability stats
    avg_stability = 0
    mature_cards_pct = 0
    leech_count = 0

    if not cards_df.empty:
        avg_stability = round(float(cards_df['stability'].mean()), 1)
        # Mature = stability > 30 days
        mature_cards = (cards_df['stability'] > 30).sum()
        mature_cards_pct = round(mature_cards / len(cards_df) * 100, 1)
        # Leeches = cards with 3+ lapses
        leech_count = int((cards_df['lapses'] >= 3).sum())

    return {
        'health_score': health_score,
        'cards_needing_attention': cards_needing_attention,
        'median_retrievability': memory['median_retrievability'],
        'avg_stability': avg_stability,
        'mature_cards_pct': mature_cards_pct,
        'leech_count': leech_count
    }


def get_session_summary_stats(review_days: int | None = None, year_filter: int | None = None) -> dict:
    """
    Get summary statistics for session tab section cards.
    """
    session_df = get_session_data(review_days, year_filter)
    consistency = get_consistency_stats(review_days)
    best_hour = get_best_study_hour(review_days)

    if session_df.empty:
        return {
            'weekly_velocity': 0,
            'avg_success_rate': 0,
            'current_streak': consistency['current_streak'],
            'best_hour': best_hour,
            'avg_session_size': 0,
            'trend': 'stable'
        }

    # Weekly velocity: avg reviews per day in last 7 days
    recent = session_df.tail(7) if len(session_df) >= 7 else session_df
    weekly_velocity = round(float(recent['total_cards'].mean()), 1)

    # Average success rate
    avg_success_rate = round(float(session_df['success_rate'].mean()), 1)

    # Trend: compare last 7 sessions to previous 7
    trend = 'stable'
    if len(session_df) >= 14:
        recent_avg = session_df.tail(7)['success_rate'].mean()
        previous_avg = session_df.iloc[-14:-7]['success_rate'].mean()
        diff = recent_avg - previous_avg
        if diff > 2:
            trend = 'up'
        elif diff < -2:
            trend = 'down'

    avg_session_size = round(float(session_df['total_cards'].mean()), 0)

    return {
        'weekly_velocity': weekly_velocity,
        'avg_success_rate': avg_success_rate,
        'current_streak': consistency['current_streak'],
        'best_hour': best_hour,
        'avg_session_size': avg_session_size,
        'trend': trend
    }


def get_historical_average_reviews() -> float:
    """Get historical average reviews per day for capacity line."""
    session_df = get_session_data()
    if session_df.empty:
        return 0
    return round(float(session_df['total_cards'].mean()), 1)


def get_future_load_forecast(days_ahead: int = 60) -> pd.DataFrame:
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

    # Get all cards with due dates
    cursor.execute("""
        SELECT
            c.due,
            c.queue,
            c.type
        FROM cards c
        WHERE c.queue IN (1, 2)  -- Learning or review
          AND c.due > 0
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
