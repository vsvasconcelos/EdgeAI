#!/usr/bin/env python3
# =============================================================================
#  EdgeAI — MCP Server para integração com o Zed Agent
#  Arquivo  : mcp_server.py
#  Framework: MCP (Model Context Protocol) via FastMCP
#  
#  Permite disparar o pipeline multi-agente diretamente de dentro
#  do chat do Zed Agent (painel de IA do Zed) e salvar os artefatos
#  locais na pasta artifacts/.
# =============================================================================

import os
import sys

# Garante que o diretório do projeto está no sys.path para importar app_agente
project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.append(project_dir)

from mcp.server.fastmcp import FastMCP
from app_agente import criar_llm, executar_pipeline, salvar_artefatos

# Instancia o servidor MCP chamado "EdgeAI-Agents"
mcp = FastMCP("EdgeAI-Agents")

@mcp.tool()
def rodar_pipeline_agentes(pedido: str) -> str:
    """
    Executa o pipeline multi-agente local (GP -> Arquiteto -> Desenvolvedor)
    para o pedido fornecido.
    
    Salva localmente os artefatos gerados (escopo.md, arquitetura.md e codigo.py)
    na pasta 'artifacts/' do projeto e retorna o código desenvolvido
    diretamente no chat do Zed Agent.
    
    Args:
        pedido: Descrição da funcionalidade ou algoritmo em Python que você quer criar.
    """
    try:
        # Cria a instância do LLM local (Ollama)
        llm = criar_llm(temperatura=0.1)
        
        # Executa o pipeline sequencial
        escopo, arquitetura, codigo = executar_pipeline(llm, pedido)
        
        # Grava os artefatos na pasta local do projeto
        salvar_artefatos(escopo, arquitetura, codigo)
        
        pasta_artifacts = os.path.join(project_dir, "artifacts")
        
        # Prepara a mensagem de retorno estruturada para o chat
        resposta_mcp = (
            f"### 🤖 EdgeAI: Pipeline Multi-Agente Concluído com Sucesso!\n\n"
            f"Os artefatos gerados foram salvos no diretório local do projeto:\n"
            f"📁 `{pasta_artifacts}/`\n\n"
            f"---\n\n"
            f"### 🎯 1. Gerente de Projetos (Escopo & Requisitos)\n"
            f"{escopo}\n\n"
            f"---\n\n"
            f"### 🏗️ 2. Arquiteto de Sistemas (Arquitetura Técnica)\n"
            f"{arquitetura}\n\n"
            f"---\n\n"
            f"### 💻 3. Desenvolvedor Python (Código & Testes Inline)\n\n"
            f"{codigo}"
        )
        return resposta_mcp
        
    except Exception as e:
        return f"❌ Erro durante a execução do pipeline de agentes: {str(e)}"

if __name__ == "__main__":
    mcp.run()
