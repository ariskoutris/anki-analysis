#!/usr/bin/env python3
"""
Predictive Learning Analysis for Anki Core 2K Deck
Creates visualizations to predict future learning patterns and identify optimization opportunities
"""

import sqlite3
import os
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
import math

def connect_db():
    """Connect to the decompressed Anki database"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    db_path = os.path.join(project_dir, 'data', 'decompressed_anki21b.db')
    return sqlite3.connect(db_path)

def predict_workload():
    """Predict upcoming review workload"""
    conn = connect_db()
    cursor = conn.cursor()
    
    # Get current card states for prediction
    cursor.execute("""
        SELECT 
            c.due,
            c.ivl,
            c.factor/10.0 as ease,
            c.type,
            COUNT(*) as card_count
        FROM cards c
        WHERE c.type IN (1, 2)  -- Review and relearn cards
        GROUP BY c.due, c.ivl, c.factor, c.type
        ORDER BY c.due
    """)
    
    workload_data = cursor.fetchall()
    conn.close()
    return workload_data

def create_predictive_analysis():
    """Create predictive analysis visualizations"""
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Predictive Learning Analysis - Core 2K Deck', fontsize=16, fontweight='bold')
    
    conn = connect_db()
    cursor = conn.cursor()
    
    # 1. Upcoming Review Workload Prediction
    ax1 = axes[0, 0]
    workload_data = predict_workload()
    
    if workload_data:
        # Group by due date and sum cards
        due_counts = {}
        for row in workload_data:
            due_date = row[0]
            card_count = row[4]
            if due_date in due_counts:
                due_counts[due_date] += card_count
            else:
                due_counts[due_date] = card_count
        
        # Get current day for reference
        cursor.execute("SELECT julianday('now') - julianday('2000-01-01') as current_day")
        current_day = cursor.fetchone()[0]
        
        # Filter to next 30 days
        future_dates = []
        future_counts = []
        
        for due_date, count in sorted(due_counts.items()):
            days_from_now = due_date - current_day
            if 0 <= days_from_now <= 30:
                future_dates.append(days_from_now)
                future_counts.append(count)
        
        if future_dates:
            ax1.bar(future_dates, future_counts, alpha=0.7, color='skyblue', edgecolor='navy')
            ax1.set_xlabel('Days from Today')
            ax1.set_ylabel('Cards Due')
            ax1.set_title('Predicted Review Workload (Next 30 Days)')
            ax1.grid(True, alpha=0.3)
            
            # Add trend line
            if len(future_dates) > 3:
                z = np.polyfit(future_dates, future_counts, 2)
                p = np.poly1d(z)
                trend_x = np.linspace(min(future_dates), max(future_dates), 100)
                trend_y = p(trend_x)
                ax1.plot(trend_x, trend_y, 'r--', alpha=0.8, linewidth=2, label='Trend')
                ax1.legend()
    
    # 2. Learning Efficiency Optimization
    ax2 = axes[0, 1]
    cursor.execute("""
        SELECT 
            CAST(strftime('%H', datetime(r.id/1000, 'unixepoch')) AS INTEGER) as hour,
            AVG(r.time)/1000.0 as avg_time,
            AVG(CASE WHEN r.ease >= 3 THEN 1.0 ELSE 0.0 END) as success_rate,
            COUNT(*) as review_count
        FROM revlog r
        WHERE r.id > 0 AND r.type != 4  -- Exclude manual reschedules (type 4)
        GROUP BY hour
        HAVING review_count >= 5
        ORDER BY hour
    """)
    
    efficiency_data = cursor.fetchall()
    if efficiency_data:
        hours = [row[0] for row in efficiency_data]
        times = [row[1] for row in efficiency_data]
        success_rates = [row[2] for row in efficiency_data]
        
        # Calculate efficiency score (success rate / time)
        efficiency_scores = [sr / t if t > 0 else 0 for sr, t in zip(success_rates, times)]
        max_efficiency = max(efficiency_scores) if efficiency_scores else 1
        normalized_scores = [score / max_efficiency * 100 for score in efficiency_scores]
        
        # Color code hours by efficiency
        colors = plt.cm.RdYlGn([score/100 for score in normalized_scores])
        bars = ax2.bar(hours, normalized_scores, color=colors, alpha=0.8)
        
        ax2.set_xlabel('Hour of Day')
        ax2.set_ylabel('Efficiency Score (%)')
        ax2.set_title('Optimal Study Times')
        ax2.grid(True, alpha=0.3)
        
        # Highlight best hours
        if normalized_scores:
            best_hours = [h for h, s in zip(hours, normalized_scores) if s > np.percentile(normalized_scores, 75)]
            ax2.axhline(y=np.percentile(normalized_scores, 75), color='red', linestyle='--', alpha=0.7)
            ax2.text(max(hours), np.percentile(normalized_scores, 75) + 5, 
                    f'Best hours: {", ".join(map(str, best_hours))}', 
                    ha='right', va='bottom', fontweight='bold')
    
    # 3. Card Maturation Timeline
    ax3 = axes[1, 0]
    cursor.execute("""
        SELECT 
            CASE 
                WHEN c.ivl <= 7 THEN 'Week 1'
                WHEN c.ivl <= 30 THEN 'Month 1'
                WHEN c.ivl <= 90 THEN 'Month 2-3'
                WHEN c.ivl <= 180 THEN 'Month 4-6'
                WHEN c.ivl <= 365 THEN 'Month 7-12'
                ELSE 'Year 2+'
            END as maturity_stage,
            COUNT(*) as card_count,
            AVG(c.factor/10.0) as avg_ease
        FROM cards c
        WHERE c.type >= 0
        GROUP BY maturity_stage
        ORDER BY 
            CASE 
                WHEN c.ivl <= 7 THEN 1
                WHEN c.ivl <= 30 THEN 2
                WHEN c.ivl <= 90 THEN 3
                WHEN c.ivl <= 180 THEN 4
                WHEN c.ivl <= 365 THEN 5
                ELSE 6
            END
    """)
    
    maturity_data = cursor.fetchall()
    if maturity_data:
        stages = [row[0] for row in maturity_data]
        counts = [row[1] for row in maturity_data]
        ease_factors = [row[2] if row[2] else 2.5 for row in maturity_data]
        
        # Create stacked bar with ease factor coloring
        colors = plt.cm.RdYlGn([(e - 1.3) / (4.0 - 1.3) for e in ease_factors])
        bars = ax3.bar(stages, counts, color=colors, alpha=0.8)
        
        ax3.set_xlabel('Maturity Stage')
        ax3.set_ylabel('Number of Cards')
        ax3.set_title('Card Maturation Pipeline')
        ax3.tick_params(axis='x', rotation=45)
        ax3.grid(True, alpha=0.3)
        
        # Add ease factor annotations
        for i, (bar, ease) in enumerate(zip(bars, ease_factors)):
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height + max(counts)*0.01,
                    f'E:{ease:.1f}', ha='center', va='bottom', fontsize=9)
    
    # 4. Performance Prediction Model
    ax4 = axes[1, 1]
    
    # Analyze success rate trends over time
    cursor.execute("""
        SELECT 
            date(r.id/1000, 'unixepoch') as review_date,
            COUNT(*) as daily_reviews,
            SUM(CASE WHEN r.ease >= 3 THEN 1 ELSE 0 END) as daily_success,
            AVG(r.time)/1000.0 as avg_time
        FROM revlog r
        WHERE r.id > 0 AND r.type != 4  -- Exclude manual reschedules (type 4)
        GROUP BY review_date
        HAVING daily_reviews >= 5
        ORDER BY review_date
    """)
    
    trend_data = cursor.fetchall()
    if trend_data and len(trend_data) > 10:
        dates = range(len(trend_data))
        success_rates = [(row[2] / row[1] * 100) if row[1] > 0 else 0 for row in trend_data]
        
        # Fit polynomial trend
        z = np.polyfit(dates, success_rates, 2)
        p = np.poly1d(z)
        
        # Predict future performance
        future_dates = list(range(len(dates), len(dates) + 30))  # Next 30 sessions
        predicted_rates = [p(d) for d in future_dates]
        
        # Plot historical and predicted
        ax4.plot(dates, success_rates, 'bo-', alpha=0.7, label='Historical', markersize=4)
        ax4.plot(future_dates, predicted_rates, 'ro--', alpha=0.8, label='Predicted', linewidth=2)
        
        # Add confidence band
        if len(success_rates) > 20:
            recent_std = np.std(success_rates[-20:])
            upper_bound = [rate + recent_std for rate in predicted_rates]
            lower_bound = [rate - recent_std for rate in predicted_rates]
            ax4.fill_between(future_dates, lower_bound, upper_bound, alpha=0.2, color='red')
        
        ax4.set_xlabel('Study Sessions')
        ax4.set_ylabel('Success Rate (%)')
        ax4.set_title('Performance Prediction')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        ax4.set_ylim(0, 100)
        
        # Add vertical line to separate historical from predicted
        ax4.axvline(x=len(dates)-1, color='gray', linestyle=':', alpha=0.7)
        ax4.text(len(dates)-1, 90, 'Future →', rotation=90, va='top', ha='right')
    
    conn.close()
    
    plt.tight_layout()

    # Use dynamic path for output
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    output_path = os.path.join(project_dir, 'visualizations', 'predictive_analysis.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    print("Predictive analysis saved as 'predictive_analysis.png'")

def create_study_recommendations():
    """Generate specific study recommendations based on data"""
    conn = connect_db()
    cursor = conn.cursor()
    
    print("\n" + "="*60)
    print("PERSONALIZED STUDY RECOMMENDATIONS")
    print("="*60)
    
    # 1. Optimal study time
    cursor.execute("""
        SELECT 
            CAST(strftime('%H', datetime(r.id/1000, 'unixepoch')) AS INTEGER) as hour,
            AVG(CASE WHEN r.ease >= 3 THEN 1.0 ELSE 0.0 END) as success_rate,
            AVG(r.time)/1000.0 as avg_time,
            COUNT(*) as review_count
        FROM revlog r
        WHERE r.id > 0 AND r.type != 4  -- Exclude manual reschedules (type 4)
        GROUP BY hour
        HAVING review_count >= 10
        ORDER BY (success_rate / avg_time) DESC
        LIMIT 3
    """)
    
    best_hours = cursor.fetchall()
    if best_hours:
        print("\n1. OPTIMAL STUDY TIMES:")
        for i, (hour, success, time, count) in enumerate(best_hours, 1):
            efficiency = success / time if time > 0 else 0
            print(f"   {i}. {hour:02d}:00 - Success: {success*100:.1f}%, "
                  f"Avg time: {time:.1f}s, Efficiency: {efficiency:.3f}")
    
    # 2. Problem areas
    cursor.execute("""
        SELECT 
            c.lapses,
            COUNT(*) as card_count,
            AVG(c.factor/10.0) as avg_ease
        FROM cards c
        WHERE c.lapses > 0
        GROUP BY c.lapses
        ORDER BY c.lapses DESC
        LIMIT 5
    """)
    
    problem_cards = cursor.fetchall()
    if problem_cards:
        print("\n2. CARDS NEEDING ATTENTION:")
        total_problem_cards = sum(row[1] for row in problem_cards)
        print(f"   Total cards with lapses: {total_problem_cards}")
        for lapses, count, ease in problem_cards:
            print(f"   {lapses} lapses: {count} cards (avg ease: {ease:.2f})")
    
    # 3. Study load prediction
    cursor.execute("""
        SELECT 
            c.due,
            COUNT(*) as cards_due
        FROM cards c
        WHERE c.type IN (1, 2)
        GROUP BY c.due
        ORDER BY c.due
        LIMIT 10
    """)
    
    upcoming_reviews = cursor.fetchall()
    if upcoming_reviews:
        print("\n3. UPCOMING REVIEW LOAD:")
        cursor.execute("SELECT julianday('now') - julianday('2000-01-01') as current_day")
        current_day = cursor.fetchone()[0]
        
        for due_date, count in upcoming_reviews[:7]:
            days_from_now = int(due_date - current_day)
            if days_from_now >= 0:
                day_name = ["Today", "Tomorrow", "In 2 days", "In 3 days", 
                           "In 4 days", "In 5 days", "In 6 days"][min(days_from_now, 6)]
                if days_from_now > 6:
                    day_name = f"In {days_from_now} days"
                print(f"   {day_name}: {count} cards")
    
    # 4. Performance insights
    cursor.execute("""
        SELECT 
            AVG(CASE WHEN r.ease >= 3 THEN 1.0 ELSE 0.0 END) * 100 as overall_success,
            AVG(r.time)/1000.0 as avg_time,
            COUNT(*) as total_reviews
        FROM revlog r
        WHERE r.id > 0 AND r.type != 4  -- Exclude manual reschedules (type 4)
    """)
    
    performance = cursor.fetchone()
    if performance:
        success_rate, avg_time, total_reviews = performance
        print(f"\n4. OVERALL PERFORMANCE:")
        print(f"   Success rate: {success_rate:.1f}%")
        print(f"   Average review time: {avg_time:.1f} seconds")
        print(f"   Total reviews completed: {total_reviews}")
        
        if success_rate < 75:
            print("   ⚠️  Consider reviewing difficult cards more frequently")
        elif success_rate > 90:
            print("   ✅ Excellent retention! Consider increasing new card rate")
        
        if avg_time > 20:
            print("   ⚠️  Review time is high - consider working on recognition speed")
        elif avg_time < 8:
            print("   ⚠️  Very fast reviews - ensure you're not rushing")
    
    conn.close()

if __name__ == "__main__":
    create_predictive_analysis()
    create_study_recommendations()
