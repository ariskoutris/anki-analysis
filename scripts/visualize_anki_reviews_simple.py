import sqlite3
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
import os

# Path to the decompressed database
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
db_path = os.path.join(project_dir, 'data', 'decompressed_anki21b.db')

def connect_to_db():
    """Connect to the Anki database"""
    return sqlite3.connect(db_path)

def get_card_review_data():
    """Get card data with review information"""
    conn = connect_to_db()
    cursor = conn.cursor()
    
    # Get cards with their due dates and intervals
    query = """
    SELECT 
        c.id as card_id,
        c.due,
        c.ivl as interval_days,
        c.type,
        c.queue,
        c.reps,
        c.lapses,
        c.factor
    FROM cards c
    ORDER BY c.due
    """
    
    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()
    
    return results

def get_review_history():
    """Get review history from revlog"""
    conn = connect_to_db()
    cursor = conn.cursor()
    
    query = """
    SELECT 
        id,
        cid as card_id,
        ease,
        ivl as interval_days,
        time as review_time_ms,
        type as review_type
    FROM revlog
    ORDER BY id
    """
    
    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()
    
    return results

def create_visualizations():
    """Create multiple visualizations of the review data"""
    
    print("Loading Anki review data...")
    cards_data = get_card_review_data()
    review_history = get_review_history()
    
    print(f"Found {len(cards_data)} cards and {len(review_history)} review records")
    
    # Create a figure with multiple subplots
    fig = plt.figure(figsize=(16, 12))
    fig.suptitle('Core 2K Anki Deck Analysis', fontsize=16, fontweight='bold')
    
    # 1. Card Type Distribution
    plt.subplot(2, 3, 1)
    card_types = {0: 'New', 1: 'Learning', 2: 'Review', -1: 'Suspended'}
    queue_counts = defaultdict(int)
    
    for card in cards_data:
        queue = card[4]  # queue column
        queue_counts[queue] += 1
    
    labels = [card_types.get(q, f'Type {q}') for q in queue_counts.keys()]
    sizes = list(queue_counts.values())
    colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99']
    
    plt.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors[:len(labels)])
    plt.title('Card Distribution by Type')
    
    # 2. Interval Distribution for Review Cards
    plt.subplot(2, 3, 2)
    intervals = []
    for card in cards_data:
        if card[4] == 2 and card[2] > 0:  # Review cards with positive intervals
            intervals.append(card[2])
    
    if intervals:
        plt.hist(intervals, bins=50, edgecolor='black', alpha=0.7, color='skyblue')
        plt.xlabel('Interval (days)')
        plt.ylabel('Number of Cards')
        plt.title('Review Interval Distribution')
        plt.yscale('log')
    else:
        plt.text(0.5, 0.5, 'No review cards found', ha='center', va='center', transform=plt.gca().transAxes)
        plt.title('Review Interval Distribution')
    
    # 3. Review History Over Time (last 30 days)
    plt.subplot(2, 3, 3)
    if review_history:
        # Convert timestamps to dates and count daily reviews
        daily_reviews = defaultdict(int)
        
        for review in review_history:
            timestamp_ms = review[0]
            date = datetime.fromtimestamp(timestamp_ms / 1000).date()
            daily_reviews[date] += 1
        
        # Get last 30 days
        sorted_dates = sorted(daily_reviews.keys())
        if len(sorted_dates) > 30:
            recent_dates = sorted_dates[-30:]
        else:
            recent_dates = sorted_dates
        
        dates = [str(date) for date in recent_dates]
        counts = [daily_reviews[date] for date in recent_dates]
        
        plt.plot(range(len(dates)), counts, marker='o', markersize=4, color='green')
        plt.xlabel('Days (Recent Activity)')
        plt.ylabel('Reviews per Day')
        plt.title('Review Activity (Last 30 Days)')
        plt.xticks(range(0, len(dates), max(1, len(dates)//5)), 
                  [dates[i] for i in range(0, len(dates), max(1, len(dates)//5))], 
                  rotation=45)
    else:
        plt.text(0.5, 0.5, 'No review history found', ha='center', va='center', transform=plt.gca().transAxes)
        plt.title('Review Activity Over Time')
    
    # 4. Ease Factor Distribution
    plt.subplot(2, 3, 4)
    ease_factors = []
    for card in cards_data:
        if card[7] > 0:  # factor column
            ease_factors.append(card[7] / 10)  # Convert to percentage
    
    if ease_factors:
        plt.hist(ease_factors, bins=30, edgecolor='black', alpha=0.7, color='lightcoral')
        plt.xlabel('Ease Factor (%)')
        plt.ylabel('Number of Cards')
        plt.title('Ease Factor Distribution')
    else:
        plt.text(0.5, 0.5, 'No ease factor data', ha='center', va='center', transform=plt.gca().transAxes)
        plt.title('Ease Factor Distribution')
    
    # 5. Repetition Count Distribution
    plt.subplot(2, 3, 5)
    reps = [card[5] for card in cards_data if card[5] >= 0]  # reps column
    
    if reps:
        plt.hist(reps, bins=min(30, max(reps)), edgecolor='black', alpha=0.7, color='gold')
        plt.xlabel('Number of Repetitions')
        plt.ylabel('Number of Cards')
        plt.title('Card Repetition Distribution')
        plt.yscale('log')
    else:
        plt.text(0.5, 0.5, 'No repetition data', ha='center', va='center', transform=plt.gca().transAxes)
        plt.title('Card Repetition Distribution')
    
    # 6. Estimated Review Time Distribution
    plt.subplot(2, 3, 6)
    if review_history:
        review_times = []
        for review in review_history:
            time_ms = review[4]  # review_time_ms column
            if time_ms > 0:
                review_times.append(time_ms / 1000)  # Convert to seconds
        
        if review_times:
            # Filter out extreme outliers (>60 seconds)
            filtered_times = [t for t in review_times if t <= 60]
            
            plt.hist(filtered_times, bins=30, edgecolor='black', alpha=0.7, color='mediumpurple')
            plt.xlabel('Review Time (seconds)')
            plt.ylabel('Number of Reviews')
            plt.title('Review Time Distribution (≤60s)')
        else:
            plt.text(0.5, 0.5, 'No timing data', ha='center', va='center', transform=plt.gca().transAxes)
            plt.title('Review Time Distribution')
    else:
        plt.text(0.5, 0.5, 'No review history', ha='center', va='center', transform=plt.gca().transAxes)
        plt.title('Review Time Distribution')
    
    plt.tight_layout()
    
    # Use the same dynamic path approach for output
    output_path = os.path.join(project_dir, 'visualizations', 'anki_review_analysis.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print("Visualization saved as 'anki_review_analysis.png'")
    # plt.show()  # Commented out for headless mode
    
    # Print summary statistics
    print("\n" + "="*50)
    print("ANKI DECK SUMMARY STATISTICS")
    print("="*50)
    
    total_cards = len(cards_data)
    new_cards = len([c for c in cards_data if c[4] == 0])
    learning_cards = len([c for c in cards_data if c[4] == 1])
    review_cards = len([c for c in cards_data if c[4] == 2])
    suspended_cards = len([c for c in cards_data if c[4] == -1])
    
    # Additional breakdown: suspended cards by original type
    suspended_new = len([c for c in cards_data if c[4] == -1 and c[3] == 0])
    suspended_learning = len([c for c in cards_data if c[4] == -1 and c[3] == 1])
    suspended_review = len([c for c in cards_data if c[4] == -1 and c[3] == 2])
    suspended_relearning = len([c for c in cards_data if c[4] == -1 and c[3] == 3])  # Type 3 = relearning
    
    # Count relearning cards as review cards (they're lapsed review cards)
    active_relearning = len([c for c in cards_data if c[4] == 1 and c[3] == 3])  # Active relearning in learning queue
    
    print(f"Total Cards: {total_cards}")
    print(f"New Cards: {new_cards}")
    print(f"Learning Cards: {learning_cards}")
    print(f"Review Cards: {review_cards}")
    print(f"Suspended Cards: {suspended_cards}")
    
    if suspended_cards > 0:
        print("\nSuspended Card Breakdown:")
        print(f"  Suspended New: {suspended_new}")
        print(f"  Suspended Learning: {suspended_learning}")
        print(f"  Suspended Review: {suspended_review}")
        if suspended_relearning > 0:
            print(f"  Suspended Relearning: {suspended_relearning}")
        print("\nAnki-Style Count (includes suspended in original types):")
        print(f"  Total New (active + suspended): {new_cards + suspended_new}")
        print(f"  Total Learning (active + suspended): {learning_cards + suspended_learning}")
        print(f"  Total Review (active + suspended + relearning): {review_cards + suspended_review + suspended_relearning + active_relearning}")
        print(f"  Total Suspended: {suspended_cards}")
    
    if review_history:
        print(f"\nTotal Reviews Completed: {len(review_history)}")
        
        # Calculate average review time
        review_times = [r[4]/1000 for r in review_history if r[4] > 0]
        if review_times:
            avg_time = np.mean(review_times)
            print(f"Average Review Time: {avg_time:.1f} seconds")
        
        # Recent activity
        if review_history:
            latest_timestamp = max(r[0] for r in review_history)
            latest_date = datetime.fromtimestamp(latest_timestamp / 1000)
            print(f"Last Review: {latest_date.strftime('%Y-%m-%d %H:%M')}")
    
    # Card maturity analysis
    mature_cards = len([c for c in cards_data if c[2] >= 21 and c[4] == 2])
    young_cards = len([c for c in cards_data if 0 < c[2] < 21 and c[4] == 2])
    
    print(f"\nMature Cards (21+ day intervals): {mature_cards}")
    print(f"Young Cards (1-20 day intervals): {young_cards}")
    
    # Lapses analysis
    total_lapses = sum(c[6] for c in cards_data if c[6] > 0)
    cards_with_lapses = len([c for c in cards_data if c[6] > 0])
    
    print(f"\nTotal Lapses: {total_lapses}")
    print(f"Cards with Lapses: {cards_with_lapses}")
    
    if cards_with_lapses > 0:
        avg_lapses = total_lapses / cards_with_lapses
        print(f"Average Lapses per Lapsed Card: {avg_lapses:.1f}")

if __name__ == "__main__":
    try:
        create_visualizations()
    except Exception as e:
        print(f"Error creating visualizations: {e}")
        import traceback
        traceback.print_exc()
