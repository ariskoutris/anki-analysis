# Anki Core 2K Deck Analysis Toolkit

A comprehensive Python-based analysis toolkit for examining Anki flashcard learning patterns, performance metrics, and predictive insights. This project analyzes the Core 2K Japanese vocabulary deck to provide deep insights into learning efficiency and optimization opportunities.

## 📁 Project Structure

```
anki-analysis/
├── README.md                    # This file
├── scripts/                     # Python analysis scripts
├── visualizations/              # Generated charts and graphs
├── data/                       # Raw and processed data files
└── docs/                       # Additional documentation
```

## 🚀 Quick Start

### Prerequisites
- Python 3.7+
- Required packages: `matplotlib`, `numpy`, `sqlite3`, `zstandard`

### Installation
```bash
# Install required packages
pip install matplotlib numpy zstandard

# Navigate to project directory
cd anki-analysis
```

### Basic Usage
```bash
# Run comprehensive analysis (recommended starting point)
python scripts/visualize_anki_reviews_simple.py

# Generate advanced insights
python scripts/advanced_anki_analysis.py

# Create learning-focused visualizations
python scripts/learning_insights.py

# Generate predictive analysis
python scripts/predictive_anki_analysis.py
```

## 📊 Generated Visualizations

### 1. **anki_review_analysis.png** - Comprehensive Overview (6 panels)
- Card type distribution
- Review intervals analysis
- Daily review activity patterns
- Ease factor distributions
- Repetition count analysis
- Review time patterns

### 2. **advanced_anki_insights.png** - Advanced Learning Patterns (8 panels)
- Learning progression over time
- Difficulty distribution scatter plot
- Retention rates by interval
- Study efficiency trends
- Daily learning velocity
- Memory strength distribution
- Weekly study patterns
- Learning momentum curve

### 3. **learning_insights.png** - Focused Learning Analysis (6 panels)
- Forgetting curve analysis with trend line
- Study efficiency by hour of day
- Card difficulty distribution by lapses
- Learning momentum (7-day moving averages)
- Success rates by interval length
- Study session efficiency metrics

### 4. **predictive_analysis.png** - Future Learning Predictions (4 panels)
- Upcoming review workload forecast
- Optimal study time recommendations
- Card maturation pipeline
- Performance prediction model

## 🛠️ Script Descriptions

### Core Analysis Scripts

#### **`visualize_anki_reviews_simple.py`** ⭐ *Start Here*
- **Purpose**: Main comprehensive analysis script
- **Output**: `anki_review_analysis.png`
- **Features**: 6-panel overview of all key metrics
- **Use Case**: First-time analysis, general overview

#### **`advanced_anki_analysis.py`** 
- **Purpose**: Deep-dive advanced analysis
- **Output**: `advanced_anki_insights.png`
- **Features**: 8-panel advanced learning patterns
- **Use Case**: Detailed learning pattern analysis

#### **`learning_insights.py`**
- **Purpose**: Learning-focused visualizations
- **Output**: `learning_insights.png`
- **Features**: Forgetting curves, efficiency analysis
- **Use Case**: Understanding memory and efficiency patterns

#### **`predictive_anki_analysis.py`**
- **Purpose**: Future performance prediction
- **Output**: `predictive_analysis.png` + console recommendations
- **Features**: Workload forecasting, optimization suggestions
- **Use Case**: Planning future study sessions

### Utility Scripts

#### **`decompress_anki21b.py`**
- **Purpose**: Extract and decompress Anki database files
- **Input**: `Core 2K.apkg` → `Core 2K.zip` → SQLite database
- **Use Case**: Initial data preparation

#### **`inspect_anki_db.py`**
- **Purpose**: Database structure exploration
- **Features**: Table schemas, record counts, sample data
- **Use Case**: Understanding database structure

#### **`simple_analyze_anki.py`**
- **Purpose**: Basic statistical analysis
- **Features**: Console output of key statistics
- **Use Case**: Quick stats without visualizations

#### **`minimal_anki_analysis.py`**
- **Purpose**: Lightweight analysis script
- **Features**: Essential metrics only
- **Use Case**: Fast overview, troubleshooting

## 📈 Key Insights from Analysis

### Performance Metrics
- **Total Cards**: 2,007 (Core 2K vocabulary)
- **Reviews Completed**: 18,031 total reviews
- **Success Rate**: 59.4% overall
- **Average Review Time**: 14.6 seconds
- **Cards with Lapses**: 614 cards (30.6%)

### Optimal Study Patterns
- **Best Study Hours**: 12:00 PM (71.8% success), 8:00 AM (71.6% success)
- **Most Productive Days**: Monday, Tuesday, Thursday
- **Recommended Focus**: Cards with 3+ lapses (17.2% of deck)

### Learning Insights
- **Forgetting Curve**: Custom analysis of your retention patterns
- **Memory Stages**: Distribution across learning phases
- **Efficiency Trends**: Time vs. success rate optimization

## 🎯 Personalized Recommendations

Based on your data analysis:

1. **📚 Focus Areas**: 346 cards need extra attention (3+ lapses)
2. **⏰ Optimal Timing**: Study at 12:00 PM or 8:00 AM for best results
3. **📊 Performance**: Success rate has room for improvement (target: 75%+)
4. **🔄 Strategy**: Consider shorter intervals for struggling cards

## 🔧 Customization

### Modifying Analysis Parameters
Edit the SQL queries in scripts to:
- Change time ranges for analysis
- Adjust success rate thresholds
- Modify interval groupings
- Add new metrics

### Adding New Visualizations
1. Create new script in `scripts/` folder
2. Follow existing patterns for database connection
3. Save output to `visualizations/` folder
4. Update this README

### Working with Different Decks
1. Replace `Core 2K.apkg` in `data/` folder
2. Run `decompress_anki21b.py` to extract new database
3. Execute analysis scripts normally

## 📋 Troubleshooting

### Common Issues

**Script won't run:**
```bash
# Check Python version
python --version  # Should be 3.7+

# Install missing packages
pip install matplotlib numpy zstandard
```

**No visualizations generated:**
- Check that script completed without errors
- Verify database file exists in `data/decompressed_anki21b.db`
- Run in headless mode (scripts designed for this)

**Database errors:**
- Re-run `decompress_anki21b.py` to recreate database
- Check that original `.apkg` file is valid

### File Paths
All scripts use absolute paths relative to the project structure. If you move the project, update the database path in each script:
```python
return sqlite3.connect('/path/to/anki-analysis/data/decompressed_anki21b.db')
```

## 📊 Data Flow

```
Core 2K.apkg → decompress → SQLite DB → Analysis Scripts → Visualizations
     ↓              ↓           ↓              ↓              ↓
  Raw Anki      Extraction   Database    Python Analysis    PNG Charts
   Package                   Tables        & Stats
```

## 🤝 Contributing

To extend this analysis:
1. Add new scripts to `scripts/` folder
2. Document new visualizations in this README
3. Follow existing naming conventions
4. Test with the provided Core 2K dataset

## 📄 License

This toolkit is for educational and personal use. Anki data analysis follows Anki's terms of service.

---

**Generated**: June 5, 2025  
**Dataset**: Core 2K Japanese Vocabulary Deck  
**Total Analysis Time**: ~18,000 reviews across multiple study sessions  
**Visualization Count**: 4 comprehensive analysis files with 23 total charts  

*Happy learning! 📚✨*
