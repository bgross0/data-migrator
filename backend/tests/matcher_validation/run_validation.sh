#!/bin/bash
# Quick validation runner script

set -e

echo "======================================================================"
echo "MATCHER VALIDATION TEST SUITE"
echo "======================================================================"

# Check if we're in the right directory
if [ ! -f "test_harness.py" ]; then
    echo "Error: Must run from tests/matcher_validation directory"
    exit 1
fi

# Check for dependencies
echo ""
echo "Checking dependencies..."
python3 -c "import pandas; import networkx; import pygtrie" 2>/dev/null || {
    echo "Missing dependencies. Installing..."
    pip3 install pandas networkx pygtrie openpyxl
}

echo "✓ Dependencies OK"

# Run full test suite
echo ""
echo "======================================================================"
echo "Running Full Test Suite"
echo "======================================================================"
python3 test_harness.py --verbose

# Run strategy analyzer
echo ""
echo "======================================================================"
echo "Running Strategy Analyzer"
echo "======================================================================"
python3 strategy_analyzer.py

echo ""
echo "======================================================================"
echo "VALIDATION COMPLETE"
echo "======================================================================"
echo ""
echo "Reports saved to: ./reports/"
echo ""
echo "Next steps:"
echo "  1. Open the HTML report in your browser"
echo "  2. Review strategy recommendations"
echo "  3. Tune weights in backend/app/field_mapper/config/settings.py"
echo "  4. Re-run validation to confirm improvements"
echo ""
