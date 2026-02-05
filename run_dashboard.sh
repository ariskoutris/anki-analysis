#!/bin/bash
#
# Launch the Anki Learning Dashboard
#

cd "$(dirname "$0")"

echo "=========================================="
echo "  Anki Learning Dashboard"
echo "=========================================="
echo ""
echo "Starting the dashboard server..."
echo "Open http://127.0.0.1:8050 in your browser"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=========================================="
echo ""

# Run the dashboard
cd dashboard
python app.py
