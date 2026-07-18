#!/usr/bin/env python3
# =============================================================================
#  EdgeAI — Sistema Multi-Agente Local (Edge AI)
#  Arquivo  : app_agente.py
#  Modelo   : qwen2.5-coder:1.5b (INT4/GGUF) via Ollama
#
#  Hardware alvo:
#    CPU: 8 núcleos | RAM: 8 GB | GPU: NVIDIA MX110 2GB VRAM | OS: Ubuntu
#
#  ARQUITETURA DE IMPLEMENTAÇÃO:
#  ─────────────────────────────────────────────────────────────────────
#  O CrewAI v0.11.2 usa o AgentExecutor do LangChain com protocolo
#  ReAct (Thought → Action → Observation → Final Answer). Modelos com
#  ≤3B parâmetros (como o qwen2.5-coder:1.5b) não seguem esse protocolo
#  de forma confiável, gerando:
#    • 'dict' object has no attribute 'lower'
#    • AgentAction.__init__() missing 2 required positional arguments
#    • Loops de 27 minutos sem produzir código
#
#  SOLUÇÃO: Pipeline multi-agente via LLM direto (llm.invoke()).
#  Cada "agente" é uma chamada direta ao Ollama com um system prompt
#  especializado. O resultado de cada etapa alimenta a próxima.
#  Sem ReAct, sem tool calling, sem loops — confiável no hardware alvo.
#
#  Fluxo:
#    [GP: Escopo] → [Arquiteto: Design] → [Desenvolvedor: Código+Testes]
# =============================================================================

import os
import sys
import time
import requests
import warnings
from datetime import datetime

warnings.filterwarnings("ignore", category=UserWarning)

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text
from rich.markdown import Markdown
from rich import box
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

# =============================================================================
#  CONFIGURAÇÃO GLOBAL
# =============================================================================

console = Console(stderr=True)

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL    = "qwen2.5-coder:1.5b"
CONTEXT_WINDOW  = 4096   # Travado — evita crash de VRAM na MX110


# =============================================================================
#  VERIFICAÇÃO DE SAÚDE DO OLLAMA
# =============================================================================

def verificar_ollama() -> bool:
    """Verifica se o Ollama está rodando e o modelo está disponível."""
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        if resp.status_code != 200:
            return False
        modelos = [m["name"] for m in resp.json().get("models", [])]
        disponivel = any(OLLAMA_MODEL in m for m in modelos)
        if disponivel:
            console.print(
                f"[bold green]✓ Ollama OK[/bold green] — modelo "
                f"[cyan]{OLLAMA_MODEL}[/cyan] disponível."
            )
        else:
            console.print(
                f"[bold yellow]⚠ Modelo [cyan]{OLLAMA_MODEL}[/cyan] "
                f"não encontrado.[/bold yellow]\n"
                f"  Execute: [bold]ollama pull {OLLAMA_MODEL}[/bold]"
            )
        return disponivel
    except requests.exceptions.ConnectionError:
        console.print(
            "[bold red]✗ Ollama não está rodando.[/bold red]\n"
            "  Inicie com: [bold]ollama serve[/bold]"
        )
        return False


# =============================================================================
#  FÁBRICA DO LLM
# =============================================================================

def criar_llm(temperatura: float = 0.1, max_tokens: int = 1500) -> ChatOllama:
    """
    Cria instância ChatOllama com parâmetros calibrados para Edge AI.
    Usa a API nativa /api/chat — suporta num_ctx, num_gpu, num_thread.
    """
    return ChatOllama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=temperatura,
        num_predict=max_tokens,
        num_ctx=CONTEXT_WINDOW,
        num_gpu=1,
        num_thread=6,
    )


# =============================================================================
#  AGENTES — CHAMADA DIRETA AO LLM
# =============================================================================

def executar_agente(
    llm: ChatOllama,
    nome_agente: str,
    icone: str,
    cor: str,
    system_prompt: str,
    user_prompt: str,
) -> str:
    """
    Executa um agente como chamada direta ao LLM.

    Cada agente é definido por:
    - system_prompt: persona e regras do agente
    - user_prompt  : tarefa concreta com todo o contexto necessário

    Retorna a resposta como string.
    """
    console.print()
    console.print(Rule(f"[bold {cor}]{icone} {nome_agente}[/bold {cor}]"))
    console.print(f"[dim]Processando...[/dim]\n")

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    inicio = time.time()
    response = llm.invoke(messages)
    duracao = time.time() - inicio

    saida = response.content.strip()

    console.print(Panel(
        Markdown(saida),
        title=f"[bold {cor}]{icone} Saída: {nome_agente}[/bold {cor}]",
        border_style=cor,
        box=box.ROUNDED,
    ))
    console.print(f"[dim]  ⏱ {duracao:.1f}s[/dim]\n")

    return saida


# =============================================================================
#  PIPELINE MULTI-AGENTE
# =============================================================================

def executar_pipeline(llm: ChatOllama, pedido_usuario: str) -> str:
    """
    Executa o pipeline sequencial de 3 agentes:
    GP (Escopo) → Arquiteto (Design) → Desenvolvedor (Código+Testes)

    Cada etapa recebe o resultado da anterior como contexto.
    """

    # ── Agente 1: Gerente de Projetos ────────────────────────────────────────
    escopo = executar_agente(
        llm=llm,
        nome_agente="Gerente de Projetos",
        icone="🎯",
        cor="yellow",
        system_prompt=(
            "Você é um Gerente de Projetos de Software Sênior. "
            "Sua função é analisar pedidos e produzir documentos de escopo "
            "concisos, objetivos e acionáveis. "
            "Responda APENAS com o documento solicitado. Sem comentários extras."
        ),
        user_prompt=(
            f"Analise o pedido abaixo e produza um documento de escopo CONCISO.\n\n"
            f"PEDIDO: {pedido_usuario}\n\n"
            f"Entregue:\n"
            f"1. O que o sistema deve fazer (máx 2 linhas)\n"
            f"2. Requisitos funcionais (3 a 5 itens)\n"
            f"3. Critérios de aceitação testáveis (3 itens)\n"
            f"4. Restrições: Python puro, stdlib apenas, sem libs externas\n\n"
            f"Seja direto. Máximo 150 palavras."
        ),
    )

    # ── Agente 2: Arquiteto de Sistemas ──────────────────────────────────────
    arquitetura = executar_agente(
        llm=llm,
        nome_agente="Arquiteto de Sistemas",
        icone="🏗️",
        cor="blue",
        system_prompt=(
            "Você é um Arquiteto de Sistemas Python Sênior. "
            "Sua função é projetar a arquitetura técnica: quais funções criar, "
            "suas assinaturas e o algoritmo a usar. "
            "NÃO escreva código implementado. Apenas especifique a estrutura. "
            "Responda APENAS com a especificação técnica. Sem comentários extras."
        ),
        user_prompt=(
            f"Com base no escopo abaixo, especifique a arquitetura técnica Python.\n\n"
            f"=== ESCOPO ===\n{escopo}\n\n"
            f"Especifique:\n"
            f"1. Assinaturas das funções (ex: def nome(a: int, b: int) -> int)\n"
            f"2. Algoritmo escolhido e por quê (ex: trial division, crivo)\n"
            f"3. Fluxo: entrada → processamento → saída (1 linha por etapa)\n\n"
            f"NÃO implemente o código. Máximo 120 palavras."
        ),
    )

    # ── Agente 3: Desenvolvedor Python ───────────────────────────────────────
    codigo = executar_agente(
        llm=llm,
        nome_agente="Desenvolvedor Python",
        icone="💻",
        cor="green",
        system_prompt=(
            "Você é um Desenvolvedor Python Sênior especializado em algoritmos. "
            "Sua função é implementar código Python correto, limpo e documentado. "
            "SEMPRE inclua um bloco if __name__ == '__main__': que execute e "
            "imprima o resultado. "
            "SEMPRE adicione testes inline ao final. "
            "Responda APENAS com o código e os testes. Sem explicações prolixas."
        ),
        user_prompt=(
            f"Implemente o código Python com base na arquitetura abaixo.\n\n"
            f"=== ESCOPO ===\n{escopo}\n\n"
            f"=== ARQUITETURA ===\n{arquitetura}\n\n"
            f"REQUISITOS:\n"
            f"- Python 3.x com type hints\n"
            f"- Docstring em cada função\n"
            f"- Bloco if __name__ == '__main__': que executa e imprime o resultado\n"
            f"- Código correto e funcional\n\n"
            f"APÓS O CÓDIGO adicione:\n"
            f"=== TESTES ===\n"
            f"[TESTE] FuncaoExiste → [PASSOU]\n"
            f"[TESTE] RetornaInteiro → [PASSOU]\n"
            f"[TESTE] ResultadoPositivo → [PASSOU]\n\n"
            f"VEREDITO: [APROVADO] se todos os testes passaram."
        ),
    )

    return escopo, arquitetura, codigo


def salvar_artefatos(escopo: str, arquitetura: str, codigo: str):
    """Salva os artefatos gerados na pasta 'artifacts/' local."""
    pasta_base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artifacts")
    
    # Criar pasta específica para esta execução com timestamp (Histórico)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pasta_run = os.path.join(pasta_base, f"run_{timestamp}")
    os.makedirs(pasta_run, exist_ok=True)

    # Extrair código limpo se contiver delimitadores markdown
    codigo_limpo = codigo
    if "```python" in codigo:
        partes = codigo.split("```python")
        if len(partes) > 1:
            codigo_limpo = partes[1].split("```")[0].strip()
    elif "```" in codigo:
        partes = codigo.split("```")
        if len(partes) > 1:
            codigo_limpo = partes[1].split("```")[0].strip()

    # Formatar cadeia de raciocínio completa
    raciocinio_completo = (
        f"# Cadeia de Raciocínio Multi-Agente\n\n"
        f"Execução: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n"
        f"---\n\n"
        f"## 🎯 1. Gerente de Projetos (Escopo & Requisitos)\n\n"
        f"{escopo}\n\n"
        f"---\n\n"
        f"## 🏗️ 2. Arquiteto de Sistemas (Design Técnico)\n\n"
        f"{arquitetura}\n\n"
        f"---\n\n"
        f"## 💻 3. Desenvolvedor Python (Código & Testes Inline)\n\n"
        f"{codigo}\n"
    )

    # 1. Salvar na subpasta da execução (Histórico)
    with open(os.path.join(pasta_run, "escopo.md"), "w", encoding="utf-8") as f:
        f.write(escopo)

    with open(os.path.join(pasta_run, "arquitetura.md"), "w", encoding="utf-8") as f:
        f.write(arquitetura)

    with open(os.path.join(pasta_run, "codigo.py"), "w", encoding="utf-8") as f:
        f.write(codigo_limpo)

    with open(os.path.join(pasta_run, "raciocinio.md"), "w", encoding="utf-8") as f:
        f.write(raciocinio_completo)

    # 2. Salvar/Atualizar na raiz de artifacts/ como "latest" (Última versão)
    os.makedirs(pasta_base, exist_ok=True)
    for nome_arq, conteudo in [
        ("escopo.md", escopo),
        ("arquitetura.md", arquitetura),
        ("codigo.py", codigo_limpo),
        ("raciocinio.md", raciocinio_completo)
    ]:
        with open(os.path.join(pasta_base, nome_arq), "w", encoding="utf-8") as f:
            f.write(conteudo)

    console.print(f"[bold green]✓ Histórico gravado em:[/bold green] [cyan]{pasta_run}/[/cyan]")
    console.print(f"[bold green]✓ Versão mais recente atualizada em:[/bold green] [cyan]{pasta_base}/[/cyan]")


# =============================================================================
#  PONTO DE ENTRADA PRINCIPAL
# =============================================================================

def main():
    """Ponto de entrada do sistema multi-agente Edge AI."""

    # Banner
    console.print()
    console.print(Panel(
        Text.from_markup(
            "[bold cyan]EdgeAI — Sistema Multi-Agente Local[/bold cyan]\n"
            "[dim]Pipeline Direto LLM | Ollama | qwen2.5-coder:1.5b (INT4/GGUF)[/dim]\n"
            "[dim]GP → Arquiteto → Desenvolvedor | sem ReAct loop[/dim]"
        ),
        title="[bold white]🤖 Edge AI Crew[/bold white]",
        border_style="cyan",
        box=box.DOUBLE_EDGE,
        padding=(1, 4),
    ))
    console.print()

    # Verificação
    console.print(Rule("[bold yellow]Verificação de Ambiente[/bold yellow]"))
    if not verificar_ollama():
        console.print("\n[bold red]Sistema não pode iniciar.[/bold red]")
        sys.exit(1)
    console.print()

    # Captura do pedido
    console.print(Rule("[bold yellow]Pedido do Usuário[/bold yellow]"))
    console.print(
        "[dim]Digite o que deseja desenvolver e pressione ENTER duas vezes "
        "(linha em branco para confirmar):[/dim]\n"
    )

    linhas = []
    try:
        while True:
            linha = input()
            if linha == "" and linhas and linhas[-1] == "":
                break
            linhas.append(linha)
    except EOFError:
        pass

    pedido_usuario = "\n".join(linhas).strip()

    if not pedido_usuario:
        console.print("[bold red]Pedido vazio.[/bold red]")
        sys.exit(1)

    console.print(Panel(
        pedido_usuario,
        title="[bold green]📋 Pedido Recebido[/bold green]",
        border_style="green",
    ))
    console.print()

    # Inicialização
    console.print(Rule("[bold yellow]Inicializando[/bold yellow]"))
    console.print(
        f"[dim]Modelo: [cyan]{OLLAMA_MODEL}[/cyan] | "
        f"Ctx: [cyan]{CONTEXT_WINDOW} tokens[/cyan] | "
        f"Modo: [cyan]pipeline direto (sem ReAct)[/cyan][/dim]"
    )

    llm = criar_llm(temperatura=0.1, max_tokens=1500)
    console.print("[bold green]✓[/bold green] LLM pronto\n")

    # Execução
    console.print(Rule("[bold cyan]Iniciando Pipeline Multi-Agente[/bold cyan]"))

    inicio_total = time.time()

    try:
        escopo, arquitetura, codigo = executar_pipeline(llm, pedido_usuario)
        salvar_artefatos(escopo, arquitetura, codigo)
    except Exception as e:
        console.print(f"\n[bold red]Erro:[/bold red] {e}")
        raise

    duracao_total = time.time() - inicio_total

    # Resultado final
    console.print()
    console.print(Rule("[bold green]✅ Entrega Final — Código do Desenvolvedor[/bold green]"))
    console.print(Panel(
        Markdown(codigo),
        title="[bold white]📦 Código Entregue[/bold white]",
        border_style="green",
        box=box.DOUBLE_EDGE,
    ))
    console.print(
        f"\n[dim]⏱ Tempo total: [bold]{duracao_total:.1f}s[/bold] "
        f"({duracao_total/60:.1f} min)[/dim]\n"
    )


# =============================================================================
if __name__ == "__main__":
    main()
