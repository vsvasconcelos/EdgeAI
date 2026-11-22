#!/bin/bash
# ============================================================
# zed_runner.sh — Executor de Tasks da IDE Zed (compatível com Windows/PowerShell + WSL2 e Linux)
# Projeto: EdgeAI / Embarcatech HBr 2025
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python3"
VENV_PIP="$SCRIPT_DIR/.venv/bin/pip"

export PYTHONIOENCODING="utf-8"
export PYTHONWARNINGS="ignore::UserWarning"

case "$1" in
  agent)
    exec "$VENV_PYTHON" "$SCRIPT_DIR/app_agente.py"
    ;;

  check)
    echo "=== Ollama ==="
    "$SCRIPT_DIR/ollama.sh" list || echo "[Aviso] Servidor Ollama não respondeu."
    echo ""
    echo "=== Python ==="
    "$VENV_PYTHON" --version
    echo ""
    echo "=== CrewAI ==="
    "$VENV_PIP" show crewai | grep -E "Name|Version" || true
    echo ""
    echo "=== Endpoint Ollama ==="
    curl -s http://localhost:11434/api/tags | "$VENV_PYTHON" -m json.tool 2>/dev/null | head -20 || echo "[Aviso] Endpoint http://localhost:11434 offline."
    ;;

  install)
    "$VENV_PIP" install -r "$SCRIPT_DIR/requirements.txt"
    ;;

  serve)
    echo "Iniciando Ollama serve..."
    "$SCRIPT_DIR/ollama.sh" serve
    ;;

  pull)
    "$SCRIPT_DIR/ollama.sh" pull qwen2.5-coder:3b
    ;;

  batch)
    echo "Desenvolva uma calculadora em Python com operações básicas." | "$VENV_PYTHON" "$SCRIPT_DIR/app_agente.py"
    ;;

  *)
    echo "Uso: $0 {agent|check|install|serve|pull|batch}"
    exit 1
    ;;
esac

