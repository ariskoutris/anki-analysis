# Quick Start Guide

## 🚀 Running Your First Analysis

### Step 1: Navigate to the project
```bash
cd /Users/ariskoutris/Desktop/anki-analysis
```

### Step 2: Run the main analysis
```bash
python scripts/visualize_anki_reviews_simple.py
```

### Step 3: View your results
Open the generated files in the `visualizations/` folder:
- `anki_review_analysis.png` - Your main overview

### Step 4: Run additional analyses
```bash
# Advanced patterns
python scripts/advanced_anki_analysis.py

# Learning insights  
python scripts/learning_insights.py

# Predictive analysis with recommendations
python scripts/predictive_anki_analysis.py
```

## 📊 What Each Visualization Shows

### Main Analysis (`anki_review_analysis.png`)
1. **Card Types**: New vs Review vs Relearn distribution
2. **Intervals**: How long between reviews
3. **Daily Activity**: When you study most
4. **Ease Factors**: Card difficulty ratings
5. **Repetitions**: How many times you've seen cards
6. **Review Times**: How long each review takes

### Advanced Analysis (`advanced_anki_insights.png`)
1. **Learning Progression**: Your improvement over time
2. **Difficulty Scatter**: Hard vs easy cards
3. **Retention Rates**: Success by interval length
4. **Study Efficiency**: Your learning speed trend
5. **Daily Velocity**: Cards graduated per day
6. **Memory Stages**: Card maturity distribution
7. **Weekly Patterns**: Your best study days
8. **Learning Momentum**: Cumulative success rate

### Learning Insights (`learning_insights.png`)
1. **Forgetting Curve**: Your actual memory retention
2. **Hourly Efficiency**: Best times to study
3. **Difficulty Distribution**: Cards by lapse count
4. **Progress Momentum**: 7-day moving averages
5. **Interval Success**: Performance by review spacing
6. **Session Efficiency**: Cards per minute analysis

### Predictive Analysis (`predictive_analysis.png`)
1. **Workload Forecast**: Reviews due in next 30 days
2. **Optimal Study Times**: When you perform best
3. **Maturation Pipeline**: Card progression stages
4. **Performance Prediction**: Future success trends

## 🎯 Your Personal Results Summary

Based on your Core 2K deck analysis:
- **Total Reviews**: 18,031 completed
- **Success Rate**: 59.4% (room for improvement!)
- **Best Study Times**: 12:00 PM and 8:00 AM
- **Challenge Cards**: 346 cards need extra attention
- **Strong Days**: Monday, Tuesday, Thursday

## 🔧 Troubleshooting

**Problem**: Script doesn't run
**Solution**: Make sure you're in the right directory and have Python packages installed

**Problem**: No images generated
**Solution**: Scripts run in headless mode - check the visualizations/ folder

**Problem**: Database error
**Solution**: The database is already prepared for you in data/ folder
