#!/bin/bash
# Anki Analysis Runner Script
# Usage: ./run_analysis.sh [script_name]

cd "$(dirname "$0")"

echo "🎯 Anki Core 2K Analysis Toolkit"
echo "================================="

if [ "$1" = "all" ]; then
    echo "🚀 Running all analyses..."
    echo ""
    
    echo "📊 1/4: Main comprehensive analysis..."
    python scripts/visualize_anki_reviews_simple.py
    
    echo "📊 2/4: Advanced learning patterns..."
    python scripts/advanced_anki_analysis.py
    
    echo "📊 3/4: Learning insights..."
    python scripts/learning_insights.py
    
    echo "📊 4/4: Predictive analysis..."
    python scripts/predictive_anki_analysis.py
    
    echo ""
    echo "✅ All analyses complete! Check the visualizations/ folder."
    
elif [ "$1" = "main" ]; then
    echo "📊 Running main analysis..."
    python scripts/visualize_anki_reviews_simple.py
    echo "✅ Main analysis complete!"
    
elif [ "$1" = "advanced" ]; then
    echo "📊 Running advanced analysis..."
    python scripts/advanced_anki_analysis.py
    echo "✅ Advanced analysis complete!"
    
elif [ "$1" = "insights" ]; then
    echo "📊 Running learning insights..."
    python scripts/learning_insights.py
    echo "✅ Learning insights complete!"
    
elif [ "$1" = "predict" ]; then
    echo "📊 Running predictive analysis..."
    python scripts/predictive_anki_analysis.py
    echo "✅ Predictive analysis complete!"
    
else
    echo "Usage: ./run_analysis.sh [option]"
    echo ""
    echo "Options:"
    echo "  main      - Run main comprehensive analysis (recommended first)"
    echo "  advanced  - Run advanced learning pattern analysis"
    echo "  insights  - Run focused learning insights analysis"
    echo "  predict   - Run predictive analysis with recommendations"
    echo "  all       - Run all analyses (takes a few minutes)"
    echo ""
    echo "Example: ./run_analysis.sh main"
fi
