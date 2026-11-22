#!/bin/bash
# ============================================================
# ollama.sh — Wrapper de conveniência para o Ollama local
# Projeto: EdgeAI / Embarcatech HBr 2025
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$SCRIPT_DIR/ollama_install"
OLLAMA_BIN="$INSTALL_DIR/bin/ollama"

export OLLAMA_MODELS="$INSTALL_DIR/models"
export OLLAMA_HOST="127.0.0.1:11434"
export LD_LIBRARY_PATH="$INSTALL_DIR/lib/ollama:$LD_LIBRARY_PATH"

usage() {
  echo "Uso: $0 [comando]"
  echo ""
  echo "Comandos disponíveis:"
  echo "  serve          Inicia o servidor Ollama em background"
  echo "  stop           Para o servidor Ollama"
  echo "  pull [modelo]  Baixa um modelo no Ollama local (padrão: qwen2.5-coder:3b)"
  echo "  rm [modelo]    Remove um modelo do Ollama local"
  echo "  run [prompt]   Executa uma consulta ao modelo Qwen2.5-Coder:3b"
  echo "  list           Lista os modelos instalados"
  echo "  ps             Lista os modelos carregados em memória"
  echo "  status         Verifica se o servidor está rodando"
  echo "  logs           Exibe os logs do servidor"
  echo "  chat           Abre chat interativo com Qwen2.5-Coder:3b"
  echo ""
}

case "$1" in
  serve)
    if curl -s http://127.0.0.1:11434/ > /dev/null 2>&1; then
      echo "[Ollama] ✅ Servidor já está ONLINE em http://127.0.0.1:11434"
      exit 0
    fi
    echo "[Ollama] Iniciando servidor em background..."
    "$OLLAMA_BIN" serve > "$INSTALL_DIR/ollama_server.log" 2>&1 &
    SERVO_PID=$!
    echo "$SERVO_PID" > "$INSTALL_DIR/ollama.pid"
    echo "[Ollama] Servidor iniciado com PID=$SERVO_PID"
    echo "[Ollama] Aguardando 3 segundos para confirmar inicialização..."
    sleep 3
    if kill -0 "$SERVO_PID" 2>/dev/null; then
      echo "[Ollama] ✅ Servidor rodando em http://127.0.0.1:11434"
    else
      echo "[Ollama] ❌ Falha ao iniciar o servidor. Veja os logs:"
      cat "$INSTALL_DIR/ollama_server.log"
    fi
    ;;

  stop)
    if [ -f "$INSTALL_DIR/ollama.pid" ]; then
      PID=$(cat "$INSTALL_DIR/ollama.pid")
      kill "$PID" 2>/dev/null && echo "[Ollama] Servidor PID=$PID parado." || echo "[Ollama] Processo não encontrado."
      rm -f "$INSTALL_DIR/ollama.pid"
    else
      pkill -f "ollama serve" && echo "[Ollama] Servidor parado." || echo "[Ollama] Nenhum servidor encontrado."
    fi
    ;;

  run)
    shift
    if [ -z "$*" ]; then
      echo "[Ollama] Erro: forneça um prompt."
      exit 1
    fi
    "$OLLAMA_BIN" run qwen2.5-coder:3b "$*"
    ;;

  chat)
    echo "[Ollama] Abrindo chat interativo com qwen2.5-coder:3b"
    echo "[Ollama] Digite /bye para sair."
    "$OLLAMA_BIN" run qwen2.5-coder:3b
    ;;

  list)
    "$OLLAMA_BIN" list
    ;;

  ps)
    "$OLLAMA_BIN" ps
    ;;

  rm)
    shift
    if [ -z "$1" ]; then
      echo "[Ollama] Erro: informe o nome do modelo a remover."
      exit 1
    fi
    "$OLLAMA_BIN" rm "$1"
    ;;

  status)
    if curl -s http://127.0.0.1:11434/ > /dev/null 2>&1; then
      echo "[Ollama] ✅ Servidor ONLINE em http://127.0.0.1:11434"
    else
      echo "[Ollama] ❌ Servidor OFFLINE"
    fi
    ;;

  logs)
    if [ -f "$INSTALL_DIR/ollama_server.log" ]; then
      tail -50 "$INSTALL_DIR/ollama_server.log"
    else
      echo "[Ollama] Nenhum log encontrado."
    fi
    ;;

  pull)
    shift
    MODEL="${1:-qwen2.5-coder:3b}"
    "$OLLAMA_BIN" pull "$MODEL"
    ;;

  *)
    usage
    ;;
esac
