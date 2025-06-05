#!/usr/bin/env python3
"""
Advanced Anki Learning Analysis
Creates additional insightful visualizations for learning pattern interpretation
"""

import sqlite3
import matplotlib.pyplot as plt
import numpy as np
import os

def connect_db():
    """Connect to the decompressed Anki database"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    db_path = os.path.join(project_dir, 'data', 'decompressed_anki21b.db')
    return sqlite3.connect(db_path)

def get_learning_progression():
    """Analyze learning progression over time"""
    conn = connect_db()
    cursor = conn.cursor()
    
    # Get reviews over time with card state progression
    cursor.execute("""
        SELECT 
            date(r.id/1000, 'unixepoch') as review_date,
            r.type,
            r.ease,
            r.ivl,
            COUNT(*) as review_count,
            AVG(r.time) as avg_time
        FROM revlog r
        WHERE r.id > 0
        GROUP BY review_date, r.type
        ORDER BY review_date
    """)
    
    progression_data = cursor.fetchall()
    conn.close()
    return progression_data

def get_difficulty_analysis():
    """Analyze cards by difficulty and success patterns"""
    conn = connect_db()
    cursor = conn.cursor()
    
    # Get card difficulty metrics
    cursor.execute("""
        SELECT 
            c.factor/10.0 as ease_factor,
            c.reps,
            c.lapses,
            r.ease as last_rating,
            c.ivl as current_interval,
            COUNT(r.id) as total_reviews,
            AVG(r.time) as avg_review_time
        FROM cards c
        LEFT JOIN revlog r ON c.id = r.cid
        WHERE c.type >= 0
        GROUP BY c.id
        HAVING total_reviews > 0
    """)
    
    difficulty_data = cursor.fetchall()
    conn.close()
    return difficulty_data

def get_retention_analysis():
    """Analyze retention patterns and forgetting curves"""
    conn = connect_db()
    cursor = conn.cursor()
    
    # Get retention data by interval length
    cursor.execute("""
        SELECT 
            CASE 
                WHEN r.ivl <= 1 THEN '≤1 day'
                WHEN r.ivl <= 7 THEN '2-7 days'
                WHEN r.ivl <= 30 THEN '1-4 weeks'
                WHEN r.ivl <= 90 THEN '1-3 months'
                ELSE '3+ months'
            END as interval_group,
            r.ease,
            COUNT(*) as count,
            AVG(r.time) as avg_time
        FROM revlog r
        WHERE r.type = 1 AND r.ivl > 0  -- Review cards only
        GROUP BY interval_group, r.ease
        ORDER BY 
            CASE interval_group
                WHEN '≤1 day' THEN 1
                WHEN '2-7 days' THEN 2
                WHEN '1-4 weeks' THEN 3
                WHEN '1-3 months' THEN 4
                ELSE 5
            END, r.ease
    """)
    
    retention_data = cursor.fetchall()
    conn.close()
    return retention_data

def get_time_efficiency():
    """Analyze time efficiency and learning speed"""
    conn = connect_db()
    cursor = conn.cursor()
    
    # Get efficiency metrics
    cursor.execute("""
        SELECT 
            date(r.id/1000, 'unixepoch') as review_date,
            COUNT(*) as reviews_per_day,
            SUM(r.time)/1000.0/60.0 as total_minutes,
            AVG(r.time)/1000.0 as avg_seconds,
            SUM(CASE WHEN r.ease >= 3 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate
        FROM revlog r
        WHERE r.id > 0
        GROUP BY review_date
        HAVING reviews_per_day >= 5  -- Only days with meaningful study
        ORDER BY review_date
    """)
    
    efficiency_data = cursor.fetchall()
    conn.close()
    return efficiency_data

def create_advanced_visualizations():
    """Create comprehensive advanced visualizations"""
    # Set up the figure with subplots
    fig = plt.figure(figsize=(20, 24))
    fig.suptitle('Advanced Anki Learning Analysis - Core 2K Deck', fontsize=20, fontweight='bold')
    
    # 1. Learning Progression Heatmap
    ax1 = plt.subplot(4, 2, 1)
    progression_data = get_learning_progression()
    
    # Process progression data for heatmap
    dates = []
    review_types = []
    counts = []
    
    for row in progression_data:
        dates.append(row[0])
        type_map = {0: 'Learning', 1: 'Review', 2: 'Relearn', 3: 'Cram'}
        review_types.append(type_map.get(row[1], 'Unknown'))
        counts.append(row[4])
    
    # Create a simple progression plot
    unique_dates = sorted(set(dates))
    if unique_dates:
        date_indices = [unique_dates.index(d) for d in dates]
        type_colors = {'Learning': 'red', 'Review': 'green', 'Relearn': 'orange', 'Cram': 'blue'}
        
        for review_type in set(review_types):
            type_data = [(date_indices[i], counts[i]) for i in range(len(dates)) 
                        if review_types[i] == review_type]
            if type_data:
                x_vals, y_vals = zip(*type_data)
                ax1.scatter(x_vals, y_vals, c=type_colors.get(review_type, 'gray'), 
                           label=review_type, alpha=0.7, s=50)
    
    ax1.set_title('Learning Progression Over Time', fontweight='bold')
    ax1.set_xlabel('Days Since Start')
    ax1.set_ylabel('Reviews per Day')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. Difficulty Distribution
    ax2 = plt.subplot(4, 2, 2)
    difficulty_data = get_difficulty_analysis()
    
    if difficulty_data:
        ease_factors = [row[0] for row in difficulty_data if row[0] and row[0] > 0]
        lapses = [row[2] for row in difficulty_data if row[2] is not None]
        
        # Create difficulty scatter plot
        if ease_factors and lapses:
            colors = ['red' if lapse > 2 else 'orange' if lapse > 0 else 'green' for lapse in lapses]
            ax2.scatter(ease_factors, lapses, c=colors, alpha=0.6, s=30)
            ax2.set_xlabel('Ease Factor')
            ax2.set_ylabel('Number of Lapses')
            ax2.set_title('Card Difficulty Distribution', fontweight='bold')
            
            # Add legend
            import matplotlib.patches as mpatches
            green_patch = mpatches.Patch(color='green', label='No lapses')
            orange_patch = mpatches.Patch(color='orange', label='1-2 lapses')
            red_patch = mpatches.Patch(color='red', label='3+ lapses')
            ax2.legend(handles=[green_patch, orange_patch, red_patch])
    
    ax2.grid(True, alpha=0.3)
    
    # 3. Retention Analysis
    ax3 = plt.subplot(4, 2, 3)
    retention_data = get_retention_analysis()
    
    if retention_data:
        # Process retention data
        interval_groups = []
        success_rates = []
        
        # Group by interval and calculate success rates
        from collections import defaultdict
        interval_stats = defaultdict(lambda: {'total': 0, 'success': 0})
        
        for row in retention_data:
            interval_group = row[0]
            ease = row[1]
            count = row[2]
            
            interval_stats[interval_group]['total'] += count
            if ease >= 3:  # Consider ease 3+ as success
                interval_stats[interval_group]['success'] += count
        
        for interval in ['≤1 day', '2-7 days', '1-4 weeks', '1-3 months', '3+ months']:
            if interval in interval_stats and interval_stats[interval]['total'] > 0:
                interval_groups.append(interval)
                success_rate = (interval_stats[interval]['success'] / 
                              interval_stats[interval]['total']) * 100
                success_rates.append(success_rate)
        
        if interval_groups and success_rates:
            bars = ax3.bar(range(len(interval_groups)), success_rates, 
                          color=['#2E8B57', '#32CD32', '#FFD700', '#FF8C00', '#FF4500'])
            ax3.set_xticks(range(len(interval_groups)))
            ax3.set_xticklabels(interval_groups, rotation=45)
            ax3.set_ylabel('Success Rate (%)')
            ax3.set_title('Retention by Interval Length', fontweight='bold')
            ax3.set_ylim(0, 100)
            
            # Add value labels on bars
            for i, bar in enumerate(bars):
                height = bar.get_height()
                ax3.text(bar.get_x() + bar.get_width()/2., height + 1,
                        f'{height:.1f}%', ha='center', va='bottom')
    
    ax3.grid(True, alpha=0.3)
    
    # 4. Study Efficiency Over Time
    ax4 = plt.subplot(4, 2, 4)
    efficiency_data = get_time_efficiency()
    
    if efficiency_data:
        dates = [row[0] for row in efficiency_data]
        efficiency_scores = []
        
        for row in efficiency_data:
            reviews = row[1]
            minutes = row[2]
            success_rate = row[4]
            
            # Calculate efficiency: (reviews * success_rate) / minutes
            if minutes > 0:
                efficiency = (reviews * success_rate) / minutes
                efficiency_scores.append(efficiency)
            else:
                efficiency_scores.append(0)
        
        if efficiency_scores:
            # Smooth the efficiency data
            window_size = min(7, len(efficiency_scores) // 3) if len(efficiency_scores) > 10 else 1
            if window_size > 1:
                smoothed = np.convolve(efficiency_scores, np.ones(window_size)/window_size, mode='valid')
            else:
                smoothed = efficiency_scores
            
            ax4.plot(range(len(smoothed)), smoothed, 'b-', linewidth=2, alpha=0.8)
            ax4.fill_between(range(len(smoothed)), smoothed, alpha=0.3)
            ax4.set_xlabel('Study Sessions')
            ax4.set_ylabel('Efficiency Score')
            ax4.set_title('Study Efficiency Trend', fontweight='bold')
    
    ax4.grid(True, alpha=0.3)
    
    # 5. Learning Velocity Analysis
    ax5 = plt.subplot(4, 2, 5)
    
    # Calculate learning velocity (cards graduating to review state)
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            date(r.id/1000, 'unixepoch') as review_date,
            COUNT(CASE WHEN r.type = 0 AND r.ease >= 3 THEN 1 END) as graduated,
            COUNT(CASE WHEN r.type = 1 THEN 1 END) as reviewed,
            COUNT(CASE WHEN r.type = 2 THEN 1 END) as relearned
        FROM revlog r
        WHERE r.id > 0
        GROUP BY review_date
        ORDER BY review_date
    """)
    
    velocity_data = cursor.fetchall()
    conn.close()
    
    if velocity_data:
        dates = [row[0] for row in velocity_data]
        graduated = [row[1] for row in velocity_data]
        reviewed = [row[2] for row in velocity_data]
        relearned = [row[3] for row in velocity_data]
        
        x_pos = range(len(dates))
        width = 0.8
        
        # Stacked bar chart
        ax5.bar(x_pos, graduated, width, label='Graduated', color='green', alpha=0.8)
        ax5.bar(x_pos, reviewed, width, bottom=graduated, label='Reviewed', color='blue', alpha=0.8)
        ax5.bar(x_pos, relearned, width, 
                bottom=[g + r for g, r in zip(graduated, reviewed)], 
                label='Relearned', color='red', alpha=0.8)
        
        ax5.set_xlabel('Study Sessions')
        ax5.set_ylabel('Number of Cards')
        ax5.set_title('Daily Learning Velocity', fontweight='bold')
        ax5.legend()
    
    ax5.grid(True, alpha=0.3)
    
    # 6. Memory Strength Distribution
    ax6 = plt.subplot(4, 2, 6)
    
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            CASE 
                WHEN c.ivl <= 1 THEN 'New/Learning'
                WHEN c.ivl <= 7 THEN 'Short-term'
                WHEN c.ivl <= 30 THEN 'Medium-term'
                WHEN c.ivl <= 180 THEN 'Long-term'
                ELSE 'Mature'
            END as memory_stage,
            COUNT(*) as card_count,
            AVG(c.factor/10.0) as avg_ease
        FROM cards c
        WHERE c.type >= 0
        GROUP BY memory_stage
        ORDER BY 
            CASE memory_stage
                WHEN 'New/Learning' THEN 1
                WHEN 'Short-term' THEN 2
                WHEN 'Medium-term' THEN 3
                WHEN 'Long-term' THEN 4
                ELSE 5
            END
    """)
    
    memory_data = cursor.fetchall()
    conn.close()
    
    if memory_data:
        stages = [row[0] for row in memory_data]
        counts = [row[1] for row in memory_data]
        ease_values = [row[2] if row[2] else 2.5 for row in memory_data]
        
        # Create pie chart with ease factor coloring
        colors = plt.cm.RdYlGn([e/4.0 for e in ease_values])  # Normalize ease factors
        
        wedges, texts, autotexts = ax6.pie(counts, labels=stages, autopct='%1.1f%%', 
                                          colors=colors, startangle=90)
        ax6.set_title('Memory Strength Distribution', fontweight='bold')
        
        # Add ease factor info
        for i, (stage, ease) in enumerate(zip(stages, ease_values)):
            texts[i].set_text(f'{stage}\n(Ease: {ease:.1f})')
    
    # 7. Weekly Study Pattern
    ax7 = plt.subplot(4, 2, 7)
    
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            CASE CAST(strftime('%w', date(r.id/1000, 'unixepoch')) AS INTEGER)
                WHEN 0 THEN 'Sunday'
                WHEN 1 THEN 'Monday'
                WHEN 2 THEN 'Tuesday'
                WHEN 3 THEN 'Wednesday'
                WHEN 4 THEN 'Thursday'
                WHEN 5 THEN 'Friday'
                WHEN 6 THEN 'Saturday'
            END as day_of_week,
            COUNT(*) as review_count,
            AVG(r.time)/1000.0 as avg_seconds,
            SUM(r.time)/1000.0/60.0 as total_minutes
        FROM revlog r
        WHERE r.id > 0
        GROUP BY CAST(strftime('%w', date(r.id/1000, 'unixepoch')) AS INTEGER)
        ORDER BY CAST(strftime('%w', date(r.id/1000, 'unixepoch')) AS INTEGER)
    """)
    
    weekly_data = cursor.fetchall()
    conn.close()
    
    if weekly_data:
        days = [row[0] for row in weekly_data]
        counts = [row[1] for row in weekly_data]
        
        bars = ax7.bar(days, counts, color='skyblue', alpha=0.8)
        ax7.set_xlabel('Day of Week')
        ax7.set_ylabel('Total Reviews')
        ax7.set_title('Weekly Study Pattern', fontweight='bold')
        ax7.tick_params(axis='x', rotation=45)
        
        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax7.text(bar.get_x() + bar.get_width()/2., height + max(counts)*0.01,
                    f'{int(height)}', ha='center', va='bottom')
    
    ax7.grid(True, alpha=0.3)
    
    # 8. Learning Momentum
    ax8 = plt.subplot(4, 2, 8)
    
    # Calculate learning momentum (cumulative success over time)
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            date(r.id/1000, 'unixepoch') as review_date,
            SUM(CASE WHEN r.ease >= 3 THEN 1 ELSE 0 END) as daily_success,
            COUNT(*) as daily_total
        FROM revlog r
        WHERE r.id > 0
        GROUP BY review_date
        ORDER BY review_date
    """)
    
    momentum_data = cursor.fetchall()
    conn.close()
    
    if momentum_data:
        cumulative_success = []
        cumulative_total = []
        running_success = 0
        running_total = 0
        
        for row in momentum_data:
            running_success += row[1]
            running_total += row[2]
            cumulative_success.append(running_success)
            cumulative_total.append(running_total)
        
        # Calculate success rate over time
        success_rates = [s/t*100 if t > 0 else 0 for s, t in zip(cumulative_success, cumulative_total)]
        
        ax8.plot(range(len(success_rates)), success_rates, 'g-', linewidth=3, alpha=0.8)
        ax8.fill_between(range(len(success_rates)), success_rates, alpha=0.3, color='green')
        ax8.set_xlabel('Study Sessions')
        ax8.set_ylabel('Cumulative Success Rate (%)')
        ax8.set_title('Learning Momentum', fontweight='bold')
        ax8.set_ylim(0, 100)
        
        # Add final success rate annotation
        if success_rates:
            final_rate = success_rates[-1]
            ax8.annotate(f'Final: {final_rate:.1f}%', 
                        xy=(len(success_rates)-1, final_rate),
                        xytext=(len(success_rates)*0.7, final_rate + 10),
                        arrowprops=dict(arrowstyle='->', color='black', alpha=0.7),
                        fontsize=12, fontweight='bold')
    
    ax8.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Use dynamic path for output
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    output_path = os.path.join(project_dir, 'visualizations', 'advanced_anki_insights.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    print("Advanced analysis saved as 'advanced_anki_insights.png'")

if __name__ == "__main__":
    create_advanced_visualizations()
