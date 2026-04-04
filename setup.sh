#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# UC-04 Investigation Plan — One-time Setup Script
# Run once before first use: bash setup.sh
# ─────────────────────────────────────────────────────────────────────────────
set -e

BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
RESET="\033[0m"

info()    { echo -e "${GREEN}[INFO]${RESET}  $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*"; exit 1; }
section() { echo -e "\n${BOLD}──── $* ────${RESET}"; }

echo -e "${BOLD}"
echo "╔══════════════════════════════════════════════╗"
echo "║      UC-04 Investigation Plan — Setup            ║"
echo "╚══════════════════════════════════════════════╝"
echo -e "${RESET}"

# ── 1. Python check ──────────────────────────────────────────────────────────
section "1 / 5  Python"
if command -v python3 &>/dev/null; then
    PY=$(python3 --version)
    info "Found: $PY"
else
    error "Python 3 is not installed. Install Python 3.9+ and re-run."
fi

# ── 2. Pip / virtual-env ─────────────────────────────────────────────────────
section "2 / 5  Python Dependencies"
if [ ! -d ".venv" ]; then
    info "Creating virtual environment (.venv)..."
    python3 -m venv .venv
fi
info "Activating .venv and installing packages..."
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
info "Python packages installed."

# ── 3. .env file ────────────────────────────────────────────────────────────
section "3 / 5  Environment Config"
if [ ! -f ".env" ]; then
    cp .env.example .env
    info "Created .env from .env.example"
else
    info ".env already exists — skipping"
fi

# ── 4. Enterprise Services Setup ─────────────────────────────────────────────
section "4 / 4  Enterprise Services"
info "VerseAPI (Dataverse) & Azure Directory (Search) configured (Mocked)."
info "Setup complete."

# ── Done ─────────────────────────────────────────────────────────────────────
echo -e "\n${GREEN}${BOLD}✔  Setup complete!${RESET}"
echo -e "   Run the app with:  ${BOLD}bash run.sh${RESET}\n"
