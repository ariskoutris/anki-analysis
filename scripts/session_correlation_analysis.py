#!/usr/bin/env python3
"""
Session-Based Statistical Analysis with Correlation Detection
Analyzes study session statistics and their correlations:
- Efficiency score per session
- Number of cards per session (new and reviewed)  
- Success rate per session
- Hour of day per session
- Time per card per session
- Lapses per session
"""

import sqlite3
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats
from scipy.stats import pearsonr, spearmanr
import os
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

def connect_db():
    """Connect to the decompressed Anki database"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    db_path = os.path.join(project_dir, 'data', 'decompressed_anki21b.db')
    return sqlite3.connect(db_path)

def extract_session_statistics():
    """Extract comprehensive session-based statistics"""
    conn = connect_db()
    cursor = conn.cursor()
    
    # Get comprehensive session data
    cursor.execute("""
        SELECT 
            date(r.id/1000, 'unixepoch') as session_date,
            CAST(strftime('%H', datetime(r.id/1000, 'unixepoch')) AS INTEGER) as session_hour,
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
        WHERE r.id > 0 AND r.type != 4  -- Exclude manual reschedules (type 4)
        GROUP BY session_date
        HAVING total_cards >= 5  -- Only meaningful study sessions
        ORDER BY session_date
    """)
    
    session_data = cursor.fetchall()
    
    # Create a comprehensive dataframe
    sessions = []
    for row in session_data:
        session = {
            'date': row[0],
            'hour': row[1],
            'total_cards': row[2],
            'new_cards': row[3],
            'review_cards': row[4],
            'relearn_cards': row[5],
            'successful_cards': row[6],
            'failed_cards': row[7],
            'avg_time_per_card': row[8],
            'total_session_minutes': row[9],
            'session_start': row[10],
            'session_end': row[11]
        }
        
        # Calculate derived metrics
        session['success_rate'] = (session['successful_cards'] / session['total_cards'] * 100) if session['total_cards'] > 0 else 0
        session['cards_per_minute'] = session['total_cards'] / session['total_session_minutes'] if session['total_session_minutes'] > 0 else 0
        session['efficiency_score'] = (session['success_rate'] * session['cards_per_minute']) / 100 if session['cards_per_minute'] > 0 else 0
        session['new_card_ratio'] = (session['new_cards'] / session['total_cards'] * 100) if session['total_cards'] > 0 else 0
        session['session_duration'] = (session['session_end'] - session['session_start']) / 60  # minutes
        
        sessions.append(session)
    
    conn.close()
    return pd.DataFrame(sessions)

def calculate_correlations(df):
    """Calculate correlation matrices for session statistics"""
    # Select numeric columns for correlation analysis
    numeric_cols = [
        'total_cards', 'new_cards', 'review_cards', 'success_rate',
        'avg_time_per_card', 'cards_per_minute', 'efficiency_score',
        'new_card_ratio', 'session_duration', 'hour'
    ]
    
    # Pearson correlations (linear relationships)
    pearson_corr = df[numeric_cols].corr(method='pearson')
    
    # Spearman correlations (monotonic relationships)
    spearman_corr = df[numeric_cols].corr(method='spearman')
    
    return pearson_corr, spearman_corr, numeric_cols

def find_significant_correlations(corr_matrix, threshold=0.3):
    """Find correlations above a threshold and return insights"""
    significant = []
    
    for i in range(len(corr_matrix.columns)):
        for j in range(i+1, len(corr_matrix.columns)):
            corr_val = corr_matrix.iloc[i, j]
            if abs(corr_val) >= threshold:
                var1 = corr_matrix.columns[i]
                var2 = corr_matrix.columns[j]
                significant.append({
                    'var1': var1,
                    'var2': var2,
                    'correlation': corr_val,
                    'strength': 'Strong' if abs(corr_val) >= 0.7 else 'Moderate' if abs(corr_val) >= 0.5 else 'Weak',
                    'direction': 'Positive' if corr_val > 0 else 'Negative'
                })
    
    return sorted(significant, key=lambda x: abs(x['correlation']), reverse=True)

def create_session_analysis_visualization(df, pearson_corr, spearman_corr):
    """Create comprehensive session analysis visualization"""
    
    # Set up the figure
    fig = plt.figure(figsize=(24, 20))
    fig.suptitle('Comprehensive Session-Based Analysis with Correlations', fontsize=20, fontweight='bold')
    
    # 1. Session Statistics Over Time (Top row)
    ax1 = plt.subplot(4, 4, 1)
    df_sorted = df.sort_values('date')
    ax1.plot(range(len(df_sorted)), df_sorted['efficiency_score'], 'b-', linewidth=2, label='Efficiency Score', alpha=0.8)
    ax1.set_xlabel('Session Number')
    ax1.set_ylabel('Efficiency Score')
    ax1.set_title('Efficiency Score per Session')
    ax1.grid(True, alpha=0.3)
    
    # Add trend line
    if len(df_sorted) > 3:
        x = np.arange(len(df_sorted))
        z = np.polyfit(x, df_sorted['efficiency_score'], 1)
        p = np.poly1d(z)
        ax1.plot(x, p(x), 'r--', alpha=0.7, label=f'Trend (slope: {z[0]:.3f})')
        ax1.legend()
    
    # 2. Cards per Session
    ax2 = plt.subplot(4, 4, 2)
    width = 0.35
    x = range(len(df_sorted))
    ax2.bar([i - width/2 for i in x], df_sorted['new_cards'], width, label='New Cards', alpha=0.8, color='green')
    ax2.bar([i + width/2 for i in x], df_sorted['review_cards'], width, label='Review Cards', alpha=0.8, color='blue')
    ax2.set_xlabel('Session Number')
    ax2.set_ylabel('Number of Cards')
    ax2.set_title('Cards per Session (New vs Review)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 3. Success Rate per Session
    ax3 = plt.subplot(4, 4, 3)
    colors = plt.cm.RdYlGn([rate/100 for rate in df_sorted['success_rate']])
    ax3.scatter(range(len(df_sorted)), df_sorted['success_rate'], c=colors, s=60, alpha=0.8)
    ax3.plot(range(len(df_sorted)), df_sorted['success_rate'], 'k-', alpha=0.5, linewidth=1)
    ax3.set_xlabel('Session Number')
    ax3.set_ylabel('Success Rate (%)')
    ax3.set_title('Success Rate per Session')
    ax3.set_ylim(0, 100)
    ax3.grid(True, alpha=0.3)
    
    # 4. Hour of Day Analysis
    ax4 = plt.subplot(4, 4, 4)
    hour_efficiency = df.groupby('hour').agg({
        'efficiency_score': 'mean',
        'success_rate': 'mean',
        'total_cards': 'sum'
    }).reset_index()
    
    # Bubble chart: hour vs efficiency, bubble size = total cards
    bubble_sizes = [cards/10 for cards in hour_efficiency['total_cards']]
    colors = plt.cm.viridis([eff/hour_efficiency['efficiency_score'].max() if hour_efficiency['efficiency_score'].max() > 0 else 0 
                           for eff in hour_efficiency['efficiency_score']])
    
    scatter = ax4.scatter(hour_efficiency['hour'], hour_efficiency['efficiency_score'], 
                         s=bubble_sizes, c=colors, alpha=0.7, cmap='viridis')
    ax4.set_xlabel('Hour of Day')
    ax4.set_ylabel('Average Efficiency Score')
    ax4.set_title('Efficiency by Hour (bubble size = total cards)')
    ax4.grid(True, alpha=0.3)
    
    # 5. Correlation Heatmap - Pearson
    ax5 = plt.subplot(4, 4, (5, 6))
    mask = np.triu(np.ones_like(pearson_corr, dtype=bool))
    sns.heatmap(pearson_corr, mask=mask, annot=True, cmap='RdBu_r', center=0,
                square=True, linewidths=0.5, cbar_kws={"shrink": 0.8}, ax=ax5, fmt='.2f')
    ax5.set_title('Pearson Correlations (Linear Relationships)')
    
    # 6. Correlation Heatmap - Spearman  
    ax6 = plt.subplot(4, 4, (7, 8))
    mask = np.triu(np.ones_like(spearman_corr, dtype=bool))
    sns.heatmap(spearman_corr, mask=mask, annot=True, cmap='RdBu_r', center=0,
                square=True, linewidths=0.5, cbar_kws={"shrink": 0.8}, ax=ax6, fmt='.2f')
    ax6.set_title('Spearman Correlations (Monotonic Relationships)')
    
    # 7. Efficiency vs Success Rate Scatter
    ax7 = plt.subplot(4, 4, 9)
    scatter = ax7.scatter(df['success_rate'], df['efficiency_score'], 
                         c=df['total_cards'], cmap='plasma', alpha=0.7, s=60)
    ax7.set_xlabel('Success Rate (%)')
    ax7.set_ylabel('Efficiency Score')
    ax7.set_title('Efficiency vs Success Rate\n(color = total cards)')
    ax7.grid(True, alpha=0.3)
    plt.colorbar(scatter, ax=ax7, label='Total Cards')
    
    # Add correlation coefficient
    corr_coef, p_value = pearsonr(df['success_rate'], df['efficiency_score'])
    ax7.text(0.05, 0.95, f'r = {corr_coef:.3f}\np = {p_value:.3f}', 
             transform=ax7.transAxes, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # 8. Time per Card vs Cards per Session
    ax8 = plt.subplot(4, 4, 10)
    scatter = ax8.scatter(df['total_cards'], df['avg_time_per_card'], 
                         c=df['success_rate'], cmap='RdYlGn', alpha=0.7, s=60)
    ax8.set_xlabel('Total Cards in Session')
    ax8.set_ylabel('Average Time per Card (seconds)')
    ax8.set_title('Session Size vs Review Speed\n(color = success rate)')
    ax8.grid(True, alpha=0.3)
    plt.colorbar(scatter, ax=ax8, label='Success Rate (%)')
    
    # 9. New Card Ratio Impact
    ax9 = plt.subplot(4, 4, 11)
    # Bin the new card ratio for analysis
    df['new_card_ratio_bin'] = pd.cut(df['new_card_ratio'], bins=5, labels=['Very Low', 'Low', 'Medium', 'High', 'Very High'])
    ratio_analysis = df.groupby('new_card_ratio_bin').agg({
        'success_rate': 'mean',
        'efficiency_score': 'mean',
        'avg_time_per_card': 'mean'
    }).reset_index()
    
    x_pos = range(len(ratio_analysis))
    ax9.bar(x_pos, ratio_analysis['success_rate'], alpha=0.7, color='skyblue', label='Success Rate')
    ax9_twin = ax9.twinx()
    ax9_twin.plot(x_pos, ratio_analysis['efficiency_score'], 'ro-', label='Efficiency Score')
    
    ax9.set_xlabel('New Card Ratio')
    ax9.set_ylabel('Success Rate (%)', color='blue')
    ax9_twin.set_ylabel('Efficiency Score', color='red')
    ax9.set_title('Impact of New Card Ratio')
    ax9.set_xticks(x_pos)
    ax9.set_xticklabels(ratio_analysis['new_card_ratio_bin'], rotation=45)
    ax9.grid(True, alpha=0.3)
    
    # 10. Session Duration Patterns
    ax10 = plt.subplot(4, 4, 12)
    # Create duration bins
    df['duration_bin'] = pd.cut(df['session_duration'], bins=5, labels=['Very Short', 'Short', 'Medium', 'Long', 'Very Long'])
    duration_analysis = df.groupby('duration_bin').agg({
        'efficiency_score': 'mean',
        'success_rate': 'mean',
        'total_cards': 'mean'
    }).reset_index()
    
    x_pos = range(len(duration_analysis))
    bars = ax10.bar(x_pos, duration_analysis['total_cards'], alpha=0.7, 
                   color=plt.cm.viridis([eff/duration_analysis['efficiency_score'].max() 
                                       for eff in duration_analysis['efficiency_score']]))
    ax10.set_xlabel('Session Duration')
    ax10.set_ylabel('Average Cards per Session')
    ax10.set_title('Session Duration vs Productivity')
    ax10.set_xticks(x_pos)
    ax10.set_xticklabels(duration_analysis['duration_bin'], rotation=45)
    ax10.grid(True, alpha=0.3)
    
    # Add efficiency values on bars
    for i, (bar, eff) in enumerate(zip(bars, duration_analysis['efficiency_score'])):
        height = bar.get_height()
        ax10.text(bar.get_x() + bar.get_width()/2., height + 1,
                 f'Eff: {eff:.2f}', ha='center', va='bottom', fontsize=8)
    
    # 13-16: Individual metric trends over time (only 4 slots remaining)
    metrics = ['total_cards', 'success_rate', 'avg_time_per_card', 'efficiency_score']
    metric_names = ['Total Cards', 'Success Rate (%)', 'Time per Card (s)', 'Efficiency Score']
    
    for i, (metric, name) in enumerate(zip(metrics, metric_names), 13):
        ax = plt.subplot(4, 4, i)
        
        # Plot with moving average
        values = df_sorted[metric].values
        ax.plot(range(len(values)), values, 'o-', alpha=0.6, markersize=4, label='Actual')
        
        # Add 7-session moving average if enough data
        if len(values) >= 7:
            window = min(7, len(values) // 3)
            if window >= 3:
                moving_avg = pd.Series(values).rolling(window=window, center=True).mean()
                ax.plot(range(len(values)), moving_avg, 'r-', linewidth=2, alpha=0.8, label=f'{window}-session MA')
        
        ax.set_xlabel('Session Number')
        ax.set_ylabel(name)
        ax.set_title(f'{name} Over Time')
        ax.grid(True, alpha=0.3)
        if len(values) >= 7:
            ax.legend()
    
    plt.tight_layout()
    
    # Save the visualization
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    visualizations_dir = os.path.join(project_dir, 'visualizations')
    
    if not os.path.exists(visualizations_dir):
        os.makedirs(visualizations_dir)
    
    output_path = os.path.join(visualizations_dir, 'session_correlation_analysis.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✅ Session correlation analysis saved to: {output_path}")
    
    return fig

def print_correlation_insights(df, pearson_corr, spearman_corr):
    """Print detailed correlation analysis and insights"""
    
    print("\n" + "="*80)
    print("SESSION-BASED CORRELATION ANALYSIS REPORT")
    print("="*80)
    
    # Basic statistics
    print(f"\n📊 DATASET OVERVIEW:")
    print(f"   Total study sessions analyzed: {len(df)}")
    print(f"   Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"   Average session size: {df['total_cards'].mean():.1f} cards")
    print(f"   Average success rate: {df['success_rate'].mean():.1f}%")
    print(f"   Average efficiency score: {df['efficiency_score'].mean():.3f}")
    
    # Find significant correlations
    pearson_sig = find_significant_correlations(pearson_corr, threshold=0.3)
    spearman_sig = find_significant_correlations(spearman_corr, threshold=0.3)
    
    print(f"\n🔍 SIGNIFICANT CORRELATIONS (Pearson - Linear Relationships):")
    if pearson_sig:
        for i, corr in enumerate(pearson_sig[:10], 1):  # Top 10
            print(f"   {i}. {corr['var1']} ↔ {corr['var2']}")
            print(f"      Correlation: {corr['correlation']:+.3f} ({corr['strength']} {corr['direction']})")
            
            # Add interpretation
            if abs(corr['correlation']) >= 0.7:
                strength_desc = "very strong"
            elif abs(corr['correlation']) >= 0.5:
                strength_desc = "strong"
            else:
                strength_desc = "moderate"
                
            direction_desc = "increases" if corr['correlation'] > 0 else "decreases"
            print(f"      📈 When {corr['var1']} increases, {corr['var2']} tends to {direction_desc} ({strength_desc} relationship)")
            print()
    else:
        print("   No significant linear correlations found above threshold.")
    
    print(f"\n🔍 SIGNIFICANT CORRELATIONS (Spearman - Monotonic Relationships):")
    if spearman_sig:
        for i, corr in enumerate(spearman_sig[:10], 1):  # Top 10
            if corr not in pearson_sig[:10]:  # Only show if different from Pearson
                print(f"   {i}. {corr['var1']} ↔ {corr['var2']}")
                print(f"      Correlation: {corr['correlation']:+.3f} ({corr['strength']} {corr['direction']})")
                print(f"      📊 Non-linear monotonic relationship detected")
                print()
    
    # Key insights and patterns
    print(f"\n💡 KEY INSIGHTS:")
    
    # Efficiency insights
    efficiency_hour_corr = pearson_corr.loc['efficiency_score', 'hour']
    if abs(efficiency_hour_corr) > 0.2:
        direction = "improves" if efficiency_hour_corr > 0 else "declines"
        print(f"   ⏰ Study time impact: Efficiency {direction} throughout the day (r={efficiency_hour_corr:+.3f})")
    
    # Success rate insights  
    success_time_corr = pearson_corr.loc['success_rate', 'avg_time_per_card']
    if abs(success_time_corr) > 0.2:
        if success_time_corr > 0:
            print(f"   🎯 Speed vs Accuracy: Higher success rates associated with longer review times (r={success_time_corr:+.3f})")
            print(f"      💭 Suggests taking time leads to better retention")
        else:
            print(f"   ⚡ Speed vs Accuracy: Higher success rates with faster reviews (r={success_time_corr:+.3f})")
            print(f"      💭 Suggests good mastery enables quick, accurate responses")
    
    # Session size impact
    size_efficiency_corr = pearson_corr.loc['total_cards', 'efficiency_score']
    if abs(size_efficiency_corr) > 0.2:
        direction = "improves" if size_efficiency_corr > 0 else "declines"
        print(f"   📚 Session size impact: Efficiency {direction} with larger sessions (r={size_efficiency_corr:+.3f})")
        if size_efficiency_corr < 0:
            print(f"      💭 Suggests fatigue effect in longer sessions")
        else:
            print(f"      💭 Suggests better focus/momentum in substantial sessions")
    
    # New card ratio impact
    new_success_corr = pearson_corr.loc['new_card_ratio', 'success_rate'] 
    if abs(new_success_corr) > 0.2:
        direction = "increases" if new_success_corr > 0 else "decreases"
        print(f"   🆕 New card impact: Success rate {direction} with more new cards (r={new_success_corr:+.3f})")
        if new_success_corr < 0:
            print(f"      💭 New cards are more challenging, reducing overall session success")
        else:
            print(f"      💭 New cards might indicate motivated/prepared study sessions")
    
    print(f"\n📋 OPTIMIZATION RECOMMENDATIONS:")
    
    # Hour-based recommendations
    hour_stats = df.groupby('hour').agg({
        'efficiency_score': 'mean',
        'success_rate': 'mean',
        'total_cards': 'count'
    }).reset_index()
    
    if len(hour_stats) > 1:
        best_hours = hour_stats.nlargest(3, 'efficiency_score')
        print(f"   ⏰ OPTIMAL STUDY TIMES:")
        for _, row in best_hours.iterrows():
            if row['total_cards'] >= 3:  # Enough data
                print(f"      {int(row['hour']):02d}:00 - Efficiency: {row['efficiency_score']:.3f}, Success: {row['success_rate']:.1f}%")
    
    # Session size recommendations
    median_cards = df['total_cards'].median()
    small_sessions = df[df['total_cards'] < median_cards]
    large_sessions = df[df['total_cards'] >= median_cards]
    
    if len(small_sessions) > 0 and len(large_sessions) > 0:
        small_eff = small_sessions['efficiency_score'].mean()
        large_eff = large_sessions['efficiency_score'].mean()
        
        print(f"   📊 SESSION SIZE:")
        print(f"      Small sessions (<{median_cards:.0f} cards): Avg efficiency {small_eff:.3f}")
        print(f"      Large sessions (≥{median_cards:.0f} cards): Avg efficiency {large_eff:.3f}")
        
        if abs(large_eff - small_eff) > 0.1:
            better = "larger" if large_eff > small_eff else "smaller"
            print(f"      💡 Consider {better} study sessions for better efficiency")
    
    # Time-based patterns
    if 'avg_time_per_card' in df.columns:
        fast_reviews = df[df['avg_time_per_card'] < df['avg_time_per_card'].median()]
        slow_reviews = df[df['avg_time_per_card'] >= df['avg_time_per_card'].median()]
        
        if len(fast_reviews) > 0 and len(slow_reviews) > 0:
            fast_success = fast_reviews['success_rate'].mean()
            slow_success = slow_reviews['success_rate'].mean()
            
            print(f"   ⚡ REVIEW SPEED:")
            print(f"      Fast reviews: {fast_success:.1f}% success rate")
            print(f"      Slower reviews: {slow_success:.1f}% success rate")
            
            if abs(slow_success - fast_success) > 5:
                better = "slower, more careful" if slow_success > fast_success else "faster"
                print(f"      💡 Consider {better} reviews for better retention")

def main():
    """Main analysis function"""
    print("🔄 Extracting session statistics...")
    df = extract_session_statistics()
    
    if len(df) < 5:
        print("❌ Not enough session data for meaningful correlation analysis.")
        print(f"   Found {len(df)} sessions, need at least 5.")
        return
    
    print(f"✅ Analyzed {len(df)} study sessions")
    
    print("🔄 Calculating correlations...")
    pearson_corr, spearman_corr, numeric_cols = calculate_correlations(df)
    
    print("🔄 Creating visualization...")
    create_session_analysis_visualization(df, pearson_corr, spearman_corr)
    
    print("🔄 Generating insights...")
    print_correlation_insights(df, pearson_corr, spearman_corr)
    
    print("\n" + "="*80)
    print("✅ SESSION CORRELATION ANALYSIS COMPLETE!")
    print("="*80)
    print("\nGenerated files:")
    print("📊 session_correlation_analysis.png - Comprehensive visualization")
    print("📝 Detailed correlation report printed above")

if __name__ == "__main__":
    main()
