#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# UC-04 Investigation Plan — Start Script
# Usage: bash run.sh
# ─────────────────────────────────────────────────────────────────────────────

BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
RESET="\033[0m"

info()  { echo -e "${GREEN}[INFO]${RESET}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error() { echo -e "${RED}[ERROR]${RESET} $*"; exit 1; }

echo -e "${BOLD}"
echo "╔══════════════════════════════════════════════╗"
echo "║      UC-04 Investigation Plan — Starting Up      ║"
echo "╚══════════════════════════════════════════════╝"
echo -e "${RESET}"

# ── Check setup was run ──────────────────────────────────────────────────────
if [ ! -d ".venv" ]; then
    error "Virtual environment not found. Run setup first:  bash setup.sh"
fi
if [ ! -f ".env" ]; then
    error ".env not found. Run setup first:  bash setup.sh"
fi

# ── Activate venv ────────────────────────────────────────────────────────────
source .venv/bin/activate

# ── Start Streamlit ───────────────────────────────────────────────────────────
info "Launching Enterprise Investigation Assistant..."
echo ""
echo -e "  ${BOLD}App URL:${RESET}  http://localhost:8501"
echo -e "  ${BOLD}Services:${RESET} VerseAPI & Azure Directory (Mocked)"
echo -e "  ${BOLD}Logs:${RESET}     ./planning.log"
echo -e "  ${BOLD}Stop:${RESET}     Ctrl+C"
echo ""

streamlit run app.py --server.port 8501 --server.headless true

# ── Finished ──────────────────────────────────────────────────────────────────
info "Application stopped."
