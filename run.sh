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

# ── 3. Handle Arguments ──────────────────────────────────────────────────────
MODE=${1:-"--app"}

start_app() {
    info "Launching Streamlit Frontend (Port 8501)..."
    streamlit run app.py --server.port 8501 --server.headless true
}

start_api() {
    cd UC04_Assistant && python3 -m uvicorn main_api:app --host 0.0.0.0 --port 8000
}

start_tester() {
    python3 -m http.server 8080 --directory UC04_Assistant/api_tester
}

show_dashboard() {
    echo -e "${BOLD}${YELLOW}┌──────────────────────────────────────────────────────────┐${RESET}"
    echo -e "${BOLD}${YELLOW}│${RESET}  ${BOLD}ACCESS URLS${RESET}                                            ${BOLD}${YELLOW}│${RESET}"
    echo -e "${BOLD}${YELLOW}├──────────────────────────────────────────────────────────┤${RESET}"
    echo -e "${BOLD}${YELLOW}│${RESET}  ${GREEN}Streamlit Frontend:${RESET}  http://localhost:8501            ${BOLD}${YELLOW}│${RESET}"
    echo -e "${BOLD}${YELLOW}│${RESET}  ${GREEN}Chatbot API Docs:${RESET}    http://localhost:8000/docs       ${BOLD}${YELLOW}│${RESET}"
    echo -e "${BOLD}${YELLOW}│${RESET}  ${GREEN}API Test UI:${RESET}         http://localhost:8080/api_test_ui.html ${BOLD}${YELLOW}│${RESET}"
    echo -e "${BOLD}${YELLOW}└──────────────────────────────────────────────────────────┘${RESET}"
    echo ""
}

case "$MODE" in
    "--app")
        echo -e "${BOLD}${GREEN}Streamlit Frontend:${RESET} http://localhost:8501"
        start_app
        ;;
    "--api")
        echo -e "${BOLD}${GREEN}Chatbot API Docs:${RESET} http://localhost:8000/docs"
        start_api
        ;;
    "--tester")
        echo -e "${BOLD}${GREEN}API Test UI:${RESET} http://localhost:8080/api_test_ui.html"
        start_tester
        ;;
    "--both")
        info "Starting all services concurrently..."
        
        # Start API
        start_api > api_server.log 2>&1 &
        API_PID=$!
        
        # Start Tester
        start_tester > tester.log 2>&1 &
        TESTER_PID=$!
        
        # Give services a second to initialize logs
        sleep 1
        
        # Show the dashboard
        show_dashboard
        
        # Start App (Foreground)
        start_app
        ;;
    *)
        error "Invalid mode: $MODE. Use --app, --api, --tester, or --both."
        ;;
esac

# ── Finished ──────────────────────────────────────────────────────────────────
info "Services stopped."
