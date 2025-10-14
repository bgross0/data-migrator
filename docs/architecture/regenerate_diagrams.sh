#!/bin/bash
#
# Regenerate Architecture Diagrams
#
# This script regenerates all architecture diagrams and dependency graphs
# for the Data Migrator codebase.
#
# Usage: ./docs/architecture/regenerate_diagrams.sh
#

set -e  # Exit on error

echo "=== Data Migrator Architecture Diagram Regeneration ==="
echo ""

# Navigate to project root
cd "$(dirname "$0")/../.."
PROJECT_ROOT=$(pwd)

echo "Project root: $PROJECT_ROOT"
echo ""

# Check if venv exists
if [ ! -d "backend/venv" ]; then
    echo "ERROR: Virtual environment not found at backend/venv"
    echo "Please create it first: cd backend && python3 -m venv venv && venv/bin/pip install -r requirements.txt"
    exit 1
fi

# Check if required tools are installed
echo "[1/5] Checking required tools..."
if ! backend/venv/bin/python -c "import pylint" 2>/dev/null; then
    echo "Installing pylint (for pyreverse)..."
    backend/venv/bin/pip install pylint
fi

if ! backend/venv/bin/python -c "import pydeps" 2>/dev/null; then
    echo "Installing pydeps..."
    backend/venv/bin/pip install pydeps
fi

echo "✓ Tools ready"
echo ""

# Create output directory
mkdir -p docs/architecture
cd backend

# Generate UML class diagrams
echo "[2/5] Generating UML class diagrams..."
PYTHONPATH=. venv/bin/pyreverse -o dot -p DataMigrator \
    app/services \
    app/field_mapper \
    app/core \
    app/models \
    2>&1 | grep -v "Analysed"

# Move generated files
if [ -f "classes_DataMigrator.dot" ]; then
    mv classes_DataMigrator.dot ../docs/architecture/
    echo "✓ Generated classes_DataMigrator.dot"
fi

if [ -f "packages_DataMigrator.dot" ]; then
    mv packages_DataMigrator.dot ../docs/architecture/
    echo "✓ Generated packages_DataMigrator.dot"
fi

echo ""

# Generate field_mapper dependency graph
echo "[3/5] Generating field_mapper dependency graph..."
PYTHONPATH=. venv/bin/pydeps app/field_mapper \
    --max-module-depth=3 \
    --cluster \
    --show-dot \
    --nodot \
    2>&1 > ../docs/architecture/field_mapper_deps.dot

if [ -s "../docs/architecture/field_mapper_deps.dot" ]; then
    echo "✓ Generated field_mapper_deps.dot"
fi

echo ""

# Generate services dependency graph
echo "[4/5] Generating services dependency graph..."
PYTHONPATH=. venv/bin/pydeps app/services \
    --max-module-depth=2 \
    --cluster \
    --show-dot \
    --nodot \
    2>&1 > ../docs/architecture/services_deps.dot || true

if [ -s "../docs/architecture/services_deps.dot" ]; then
    echo "✓ Generated services_deps.dot"
else
    echo "⚠ services_deps.dot is empty (this is OK - may not have enough structure)"
    rm -f ../docs/architecture/services_deps.dot
fi

echo ""

# Generate core dependency graph
echo "[5/5] Generating core module dependency graph..."
PYTHONPATH=. venv/bin/pydeps app/core \
    --max-module-depth=2 \
    --show-dot \
    --nodot \
    2>&1 > ../docs/architecture/core_deps.dot || true

if [ -s "../docs/architecture/core_deps.dot" ]; then
    echo "✓ Generated core_deps.dot"
else
    echo "⚠ core_deps.dot is empty (this is OK - may not have enough structure)"
    rm -f ../docs/architecture/core_deps.dot
fi

cd ..

echo ""
echo "=== Summary ==="
echo ""
echo "Generated diagrams:"
ls -lh docs/architecture/*.dot | awk '{print "  " $9 " (" $5 ")"}'
echo ""
echo "Total diagrams: $(ls -1 docs/architecture/*.dot 2>/dev/null | wc -l)"
echo ""
echo "✓ Done! View diagrams at:"
echo "  • Online: https://dreampuf.github.io/GraphvizOnline/"
echo "  • VS Code: Install 'Graphviz Preview' extension"
echo "  • CLI: dot -Tpng <file>.dot -o <file>.png"
echo ""
echo "See docs/architecture/README.md for more viewing options."
