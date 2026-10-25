#!/bin/bash
set -e

echo "=========================================================="
echo "    SIH SURVEILLANCE & COMPLIANCE FULL TEST RUNNER        "
echo "=========================================================="

echo ""
echo "--> [1/4] Running Backend Unit & Functional Tests (backend/tests/)..."
source backend/.venv/bin/activate
PYTHONPATH=. pytest backend/tests/ -q

echo ""
echo "--> [2/4] Running Integration, E2E, and AI Tests (tests/)..."
PYTHONPATH=. pytest tests/ -q

echo ""
echo "--> [3/4] Running Frontend Lint and Typechecks..."
npm --prefix frontend run lint

echo ""
echo "--> [4/4] Running Frontend Production Build (Turbopack)..."
npm --prefix frontend run build

echo ""
echo "=========================================================="
echo "  ✓ ALL 166 TESTS & PRODUCTION BUILDS PASSED SUCCESSFULLY "
echo "=========================================================="
