#!/usr/bin/env python3
"""
Focused Learning Insights for Anki Core 2K Deck
Creates specific visualizations for learning pattern interpretation
"""

import sqlite3
import os
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict

def connect_db():
    """Connect to the decompressed Anki database"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    db_path = os.path.join(project_dir, 'data', 'decompressed_anki21b.db')
    return sqlite3.connect(db_path)

def create_learning_insights():
    """Create focused learning insight visualizations"""
    
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('Core 2K Learning Insights & Patterns', fontsize=16, fontweight='bold')
    
    conn = connect_db()
    cursor = conn.cursor()
    
    # 1. Forgetting Curve Analysis
    ax1 = axes[0, 0]
    cursor.execute("""
        SELECT 
            r.ivl as interval_days,
            AVG(CASE WHEN r.ease >= 3 THEN 1.0 ELSE 0.0 END) * 100 as success_rate,
            COUNT(*) as review_count
        FROM revlog r
        WHERE r.type = 1 AND r.ivl > 0 AND r.ivl <= 365
        GROUP BY r.ivl
        HAVING review_count >= 3
        ORDER BY r.ivl
    """)
    
    forgetting_data = cursor.fetchall()
    if forgetting_data:
        intervals = [row[0] for row in forgetting_data]
        success_rates = [row[1] for row in forgetting_data]
        
        # Smooth the curve
        if len(intervals) > 5:
            z = np.polyfit(intervals, success_rates, 3)
            p = np.poly1d(z)
            smooth_x = np.linspace(min(intervals), max(intervals), 100)
            smooth_y = p(smooth_x)
            ax1.plot(smooth_x, smooth_y, 'r-', linewidth=2, alpha=0.8, label='Forgetting Curve')
        
        ax1.scatter(intervals, success_rates, alpha=0.6, s=30, c='blue')
        ax1.set_xlabel('Interval (days)')
        ax1.set_ylabel('Success Rate (%)')
        ax1.set_title('Forgetting Curve Analysis')
        ax1.set_ylim(0, 100)
        ax1.grid(True, alpha=0.3)
        if len(intervals) > 5:
            ax1.legend()
    
    # 2. Learning Efficiency by Time of Day
    ax2 = axes[0, 1]
    cursor.execute("""
        SELECT 
            CAST(strftime('%H', datetime(r.id/1000, 'unixepoch')) AS INTEGER) as hour,
            AVG(r.time)/1000.0 as avg_time_seconds,
            AVG(CASE WHEN r.ease >= 3 THEN 1.0 ELSE 0.0 END) * 100 as success_rate,
            COUNT(*) as review_count
        FROM revlog r
        WHERE r.id > 0 AND r.type != 4  -- Exclude manual reschedules (type 4)
        GROUP BY hour
        HAVING review_count >= 10
        ORDER BY hour
    """)
    
    hourly_data = cursor.fetchall()
    if hourly_data:
        hours = [row[0] for row in hourly_data]
        times = [row[1] for row in hourly_data]
        success = [row[2] for row in hourly_data]
        
        # Dual axis plot
        ax2_twin = ax2.twinx()
        
        line1 = ax2.plot(hours, times, 'bo-', label='Avg Time (s)', alpha=0.7)
        line2 = ax2_twin.plot(hours, success, 'ro-', label='Success Rate (%)', alpha=0.7)
        
        ax2.set_xlabel('Hour of Day')
        ax2.set_ylabel('Average Time (seconds)', color='blue')
        ax2_twin.set_ylabel('Success Rate (%)', color='red')
        ax2.set_title('Study Efficiency by Hour')
        ax2.grid(True, alpha=0.3)
        
        # Combined legend
        lines = line1 + line2
        labels = [l.get_label() for l in lines]
        ax2.legend(lines, labels, loc='upper left')
    
    # 3. Card Difficulty Distribution
    ax3 = axes[0, 2]
    cursor.execute("""
        SELECT 
            c.lapses,
            COUNT(*) as card_count,
            AVG(c.factor/10.0) as avg_ease,
            AVG(c.ivl) as avg_interval
        FROM cards c
        WHERE c.type >= 0
        GROUP BY c.lapses
        ORDER BY c.lapses
    """)
    
    difficulty_data = cursor.fetchall()
    if difficulty_data:
        lapses = [row[0] for row in difficulty_data]
        counts = [row[1] for row in difficulty_data]
        
        # Color code by difficulty
        colors = ['green' if l == 0 else 'orange' if l <= 2 else 'red' for l in lapses]
        bars = ax3.bar(lapses, counts, color=colors, alpha=0.7)
        
        ax3.set_xlabel('Number of Lapses')
        ax3.set_ylabel('Number of Cards')
        ax3.set_title('Card Difficulty Distribution')
        ax3.grid(True, alpha=0.3)
        
        # Add percentage labels
        total_cards = sum(counts)
        for i, bar in enumerate(bars):
            height = bar.get_height()
            percentage = (height / total_cards) * 100
            ax3.text(bar.get_x() + bar.get_width()/2., height + max(counts)*0.01,
                    f'{percentage:.1f}%', ha='center', va='bottom')
    
    # 4. Learning Progress Momentum
    ax4 = axes[1, 0]
    cursor.execute("""
        SELECT 
            date(r.id/1000, 'unixepoch') as review_date,
            COUNT(*) as daily_reviews,
            SUM(CASE WHEN r.ease >= 3 THEN 1 ELSE 0 END) as daily_success
        FROM revlog r
        WHERE r.id > 0 AND r.type != 4  -- Exclude manual reschedules (type 4)
        GROUP BY review_date
        ORDER BY review_date
    """)
    
    daily_data = cursor.fetchall()
    if daily_data:
        # Calculate 7-day moving averages
        reviews = [row[1] for row in daily_data]
        successes = [row[2] for row in daily_data]
        
        if len(reviews) > 7:
            window = 7
            moving_avg_reviews = []
            moving_avg_success_rate = []
            
            for i in range(window-1, len(reviews)):
                avg_reviews = sum(reviews[i-window+1:i+1]) / window
                total_in_window = sum(reviews[i-window+1:i+1])
                success_in_window = sum(successes[i-window+1:i+1])
                success_rate = (success_in_window / total_in_window * 100) if total_in_window > 0 else 0
                
                moving_avg_reviews.append(avg_reviews)
                moving_avg_success_rate.append(success_rate)
            
            days = range(len(moving_avg_reviews))
            ax4.plot(days, moving_avg_reviews, 'b-', label='Avg Reviews/Day', linewidth=2)
            
            ax4_twin = ax4.twinx()
            ax4_twin.plot(days, moving_avg_success_rate, 'g-', label='Success Rate %', linewidth=2)
            
            ax4.set_xlabel('Days (7-day windows)')
            ax4.set_ylabel('Average Reviews per Day', color='blue')
            ax4_twin.set_ylabel('Success Rate (%)', color='green')
            ax4.set_title('Learning Momentum (7-day moving avg)')
            ax4.grid(True, alpha=0.3)
    
    # 5. Interval Success Analysis
    ax5 = axes[1, 1]
    cursor.execute("""
        SELECT 
            CASE 
                WHEN r.ivl <= 1 THEN '≤1d'
                WHEN r.ivl <= 3 THEN '2-3d'
                WHEN r.ivl <= 7 THEN '4-7d'
                WHEN r.ivl <= 14 THEN '1-2w'
                WHEN r.ivl <= 30 THEN '2-4w'
                WHEN r.ivl <= 90 THEN '1-3m'
                ELSE '3m+'
            END as interval_group,
            AVG(CASE WHEN r.ease >= 3 THEN 1.0 ELSE 0.0 END) * 100 as success_rate,
            COUNT(*) as review_count,
            AVG(r.time)/1000.0 as avg_time
        FROM revlog r
        WHERE r.type = 1 AND r.ivl > 0
        GROUP BY interval_group
        ORDER BY 
            CASE 
                WHEN r.ivl <= 1 THEN 1
                WHEN r.ivl <= 3 THEN 2
                WHEN r.ivl <= 7 THEN 3
                WHEN r.ivl <= 14 THEN 4
                WHEN r.ivl <= 30 THEN 5
                WHEN r.ivl <= 90 THEN 6
                ELSE 7
            END
    """)
    
    interval_data = cursor.fetchall()
    if interval_data:
        groups = [row[0] for row in interval_data]
        success_rates = [row[1] for row in interval_data]
        times = [row[3] for row in interval_data]
        
        # Create bubble chart - size represents review time
        sizes = [t * 20 for t in times]  # Scale for visibility
        colors = plt.cm.RdYlGn([sr/100 for sr in success_rates])
        
        scatter = ax5.scatter(range(len(groups)), success_rates, s=sizes, c=colors, alpha=0.7)
        ax5.set_xticks(range(len(groups)))
        ax5.set_xticklabels(groups, rotation=45)
        ax5.set_ylabel('Success Rate (%)')
        ax5.set_title('Success by Interval\n(bubble size = review time)')
        ax5.set_ylim(0, 100)
        ax5.grid(True, alpha=0.3)
        
        # Add colorbar
        cbar = plt.colorbar(scatter, ax=ax5)
        cbar.set_label('Success Rate')
    
    # 6. Study Session Analysis
    ax6 = axes[1, 2]
    cursor.execute("""
        SELECT 
            date(r.id/1000, 'unixepoch') as study_date,
            COUNT(*) as session_size,
            AVG(r.time)/1000.0 as avg_time_per_card,
            SUM(r.time)/1000.0/60.0 as total_session_minutes
        FROM revlog r
        WHERE r.id > 0 AND r.type != 4  -- Exclude manual reschedules (type 4)
        GROUP BY study_date
        HAVING session_size >= 5
        ORDER BY study_date
    """)
    
    session_data = cursor.fetchall()
    if session_data:
        session_sizes = [row[1] for row in session_data]
        session_times = [row[3] for row in session_data]
        
        # Efficiency = cards per minute
        efficiency = [size/time if time > 0 else 0 for size, time in zip(session_sizes, session_times)]
        
        # Create scatter plot
        colors = plt.cm.viridis([e/max(efficiency) if max(efficiency) > 0 else 0 for e in efficiency])
        scatter = ax6.scatter(session_sizes, session_times, c=efficiency, 
                             cmap='viridis', alpha=0.7, s=60)
        
        ax6.set_xlabel('Cards per Session')
        ax6.set_ylabel('Session Duration (minutes)')
        ax6.set_title('Study Session Efficiency')
        ax6.grid(True, alpha=0.3)
        
        # Add colorbar
        cbar = plt.colorbar(scatter, ax=ax6)
        cbar.set_label('Cards/Minute')
        
        # Add efficiency trend line
        if len(session_sizes) > 3:
            z = np.polyfit(session_sizes, session_times, 1)
            p = np.poly1d(z)
            ax6.plot(sorted(session_sizes), p(sorted(session_sizes)), "r--", alpha=0.8)
    
    conn.close()
    
    plt.tight_layout()

     # Use dynamic path for output
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    output_path = os.path.join(project_dir, 'visualizations', 'learning_insights.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    print("Learning insights saved as 'learning_insights.png'")

if __name__ == "__main__":
    create_learning_insights()
