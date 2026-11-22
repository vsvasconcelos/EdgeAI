#!/usr/bin/env python3
# =============================================================================
#  EdgeAI — Sistema Multi-Agente Local (Edge AI)
#  Arquivo  : app_agente.py
#  Modelo   : qwen2.5-coder:3b (INT4/GGUF) via Ollama
#
#  Hardware alvo:
#    CPU: 8 núcleos | RAM: 8 GB | GPU: NVIDIA MX110 2GB VRAM | OS: Ubuntu
#
#  ARQUITETURA DE IMPLEMENTAÇÃO:
#  ─────────────────────────────────────────────────────────────────────
#  O CrewAI v0.11.2 usa o AgentExecutor do LangChain com protocolo
#  ReAct (Thought → Action → Observation → Final Answer). Modelos com
#  ≤3B parâmetros não seguem esse protocolo de forma confiável, gerando:
#    • 'dict' object has no attribute 'lower'
#    • AgentAction.__init__() missing 2 required positional arguments
#    • Loops de 27 minutos sem produzir código
#
#  EVOLUÇÃO DO MODELO (1.5B → 3B) E SUPORTE WOKWI:
#  ─────────────────────────────────────────────────────────────────────
#  O modelo inicial (qwen2.5-coder:1.5b) apresentava alucinações severas
#  em código embarcado para o simulador Wokwi (misturando bibliotecas de
#  CPython/CircuitPython como Adafruit_DHT, board, wokwi_gpio com
#  MicroPython e gerando diagram.json fora do schema oficial).
#  A atualização para o qwen2.5-coder:3b combinada com prompts
#  especializados para MicroPython/Wokwi permite gerar main.py,
#  diagram.json e ssd1306.py válidos e prontos para simulação.
#
#  Fluxo:
#    [GP: Escopo] → [Arquiteto: Design] → [Desenvolvedor: Código+Diagrama]
# =============================================================================

import json
import os
import re
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
OLLAMA_MODEL    = "qwen2.5-coder:3b"
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
                f"  Execute: [bold]./ollama.sh pull {OLLAMA_MODEL}[/bold] "
                f"(ou [bold]ollama pull {OLLAMA_MODEL}[/bold])"
            )
        return disponivel
    except requests.exceptions.ConnectionError:
        console.print(
            "[bold red]✗ Ollama não está rodando.[/bold red]\n"
            "  Inicie com: [bold]./ollama.sh serve[/bold] (ou [bold]ollama serve[/bold])"
        )
        return False


# =============================================================================
#  FÁBRICA DO LLM
# =============================================================================

def criar_llm(temperatura: float = 0.1, max_tokens: int = 2500) -> ChatOllama:
    """
    Cria instância ChatOllama com parâmetros calibrados para Edge AI.
    Usa a API nativa /api/chat — suporta num_ctx, num_gpu, num_thread.
    """
    num_gpu_env = int(os.environ.get("OLLAMA_NUM_GPU", "-1"))
    return ChatOllama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=temperatura,
        num_predict=max_tokens,
        num_ctx=CONTEXT_WINDOW,
        num_gpu=num_gpu_env,
        num_thread=6,
    )


def detectar_perfil_projeto(pedido: str) -> dict:
    """
    Analisa o pedido do usuário e detecta dinamicamente:
    - modo_wokwi: bool (se é simulação embarcada Wokwi)
    - board_type: tipo do componente da placa no Wokwi (ex: wokwi-pi-pico, wokwi-esp32-devkit-v1, wokwi-arduino-uno)
    - board_id  : id curto da placa no diagram.json (pico, esp, uno, mega, nano, stm32)
    - board_nome: nome legível da placa
    - linguagem : 'MicroPython', 'CircuitPython', 'C/C++ (Arduino)', 'C/C++ (SDK Nativo)' ou 'Python'
    - arq_codigo: nome do arquivo principal ('main.py', 'sketch.ino', 'main.c', 'main.cpp', 'codigo.py')
    - bloco_md  : tag do bloco markdown ('python', 'cpp', 'c')
    """
    texto = pedido.lower()

    palavras_embarcado = (
        "wokwi",
        "micropython",
        "circuitpython",
        "pi pico",
        "raspberry pi pico",
        "rp2040",
        "esp32",
        "esp-idf",
        "arduino",
        "atmega",
        "stm32",
        "diagram.json",
        "ssd1306",
        "dht22",
        "dht11",
        "gpio",
        "pinout",
        "i2c",
        "pwm",
    )
    modo_wokwi = any(k in texto for k in palavras_embarcado)

    # Detecção da placa / microcontrolador
    if "esp32-s3" in texto or "esp32s3" in texto:
        board_type, board_id, board_nome = "board-esp32-s3-devkitc-1", "esp", "ESP32-S3"
    elif "esp32-c3" in texto or "esp32c3" in texto:
        board_type, board_id, board_nome = "board-esp32-c3-devkitm-1", "esp", "ESP32-C3"
    elif "esp32" in texto:
        board_type, board_id, board_nome = "wokwi-esp32-devkit-v1", "esp", "ESP32"
    elif "arduino mega" in texto or "mega 2560" in texto:
        board_type, board_id, board_nome = "wokwi-arduino-mega", "mega", "Arduino Mega"
    elif "arduino nano" in texto:
        board_type, board_id, board_nome = "wokwi-arduino-nano", "nano", "Arduino Nano"
    elif "arduino" in texto or "atmega328" in texto:
        board_type, board_id, board_nome = "wokwi-arduino-uno", "uno", "Arduino Uno"
    elif "stm32" in texto or "nucleo" in texto:
        board_type, board_id, board_nome = "board-stm32-nucleo-c031c6", "stm32", "STM32 Nucleo"
    elif "pico w" in texto or "wokwi-pi-pico-w" in texto:
        board_type, board_id, board_nome = "wokwi-pi-pico-w", "pico", "Raspberry Pi Pico W"
    else:
        board_type, board_id, board_nome = "wokwi-pi-pico", "pico", "Raspberry Pi Pico (RP2040)"

    # Detecção da linguagem / SDK
    tem_cpp_arduino = any(
        k in texto
        for k in ("c++", "c/c++", ".ino", "sketch.ino", "arduino ide", "void setup", "void loop")
    )
    tem_c_sdk = any(k in texto for k in ("esp-idf", "pico-sdk", "linguagem c ", "em c puro", "main.c"))
    tem_micropython = "micropython" in texto or "main.py" in texto
    tem_circuitpython = "circuitpython" in texto

    if modo_wokwi:
        if tem_micropython:
            linguagem, arq_codigo, bloco_md = "MicroPython", "main.py", "python"
        elif tem_circuitpython:
            linguagem, arq_codigo, bloco_md = "CircuitPython", "code.py", "python"
        elif tem_c_sdk:
            linguagem, arq_codigo, bloco_md = "C/C++ (SDK Nativo)", "main.c", "c"
        elif tem_cpp_arduino or board_id in ("uno", "mega", "nano", "stm32") or (board_id == "esp" and not tem_micropython):
            linguagem, arq_codigo, bloco_md = "C/C++ (Arduino)", "sketch.ino", "cpp"
        else:
            linguagem, arq_codigo, bloco_md = "MicroPython", "main.py", "python"
    else:
        if tem_cpp_arduino:
            linguagem, arq_codigo, bloco_md = "C++", "main.cpp", "cpp"
        elif tem_c_sdk:
            linguagem, arq_codigo, bloco_md = "C", "main.c", "c"
        else:
            linguagem, arq_codigo, bloco_md = "Python", "codigo.py", "python"

    return {
        "modo_wokwi": modo_wokwi,
        "board_type": board_type,
        "board_id": board_id,
        "board_nome": board_nome,
        "linguagem": linguagem,
        "arq_codigo": arq_codigo,
        "bloco_md": bloco_md,
    }


def eh_pedido_wokwi(pedido: str) -> bool:
    """Detecta se o pedido do usuário é voltado para simulação Wokwi / Sistemas Embarcados."""
    return detectar_perfil_projeto(pedido)["modo_wokwi"]


DRIVER_SSD1306_MICROPYTHON = '''"""Driver MicroPython I2C para display OLED SSD1306 (compatível com Wokwi)."""
from micropython import const
import framebuf

SET_CONTRAST = const(0x81)
SET_ENTIRE_ON = const(0xA4)
SET_NORM_INV = const(0xA6)
SET_DISP = const(0xAE)
SET_MEM_ADDR = const(0x20)
SET_COL_ADDR = const(0x21)
SET_PAGE_ADDR = const(0x22)
SET_DISP_START_LINE = const(0x40)
SET_SEG_REMAP = const(0xA0)
SET_MUX_RATIO = const(0xA8)
SET_COM_OUT_DIR = const(0xC0)
SET_DISP_OFFSET = const(0xD3)
SET_COM_PIN_CFG = const(0xDA)
SET_DISP_CLK_DIV = const(0xD5)
SET_PRECHARGE = const(0xD9)
SET_VCOM_DESEL = const(0xDB)
SET_CHARGE_PUMP = const(0x8D)


class SSD1306(framebuf.FrameBuffer):
    def __init__(self, width, height, external_vcc):
        self.width = width
        self.height = height
        self.external_vcc = external_vcc
        self.pages = self.height // 8
        self.buffer = bytearray(self.pages * self.width)
        super().__init__(self.buffer, self.width, self.height, framebuf.MONO_VLSB)
        self.init_display()

    def init_display(self):
        for cmd in (
            SET_DISP | 0x00,
            SET_MEM_ADDR, 0x00,
            SET_DISP_START_LINE | 0x00,
            SET_SEG_REMAP | 0x01,
            SET_MUX_RATIO, self.height - 1,
            SET_COM_OUT_DIR | 0x08,
            SET_DISP_OFFSET, 0x00,
            SET_COM_PIN_CFG, 0x02 if self.width > 2 * self.height else 0x12,
            SET_DISP_CLK_DIV, 0x80,
            SET_PRECHARGE, 0x22 if self.external_vcc else 0xF1,
            SET_VCOM_DESEL, 0x30,
            SET_CONTRAST, 0xFF,
            SET_ENTIRE_ON,
            SET_NORM_INV,
            SET_CHARGE_PUMP, 0x10 if self.external_vcc else 0x14,
            SET_DISP | 0x01,
        ):
            self.write_cmd(cmd)
        self.fill(0)
        self.show()

    def show(self):
        self.write_cmd(SET_COL_ADDR)
        self.write_cmd(0)
        self.write_cmd(self.width - 1)
        self.write_cmd(SET_PAGE_ADDR)
        self.write_cmd(0)
        self.write_cmd(self.pages - 1)
        self.write_data(self.buffer)


class SSD1306_I2C(SSD1306):
    def __init__(self, width, height, i2c, addr=0x3C, external_vcc=False):
        self.i2c = i2c
        self.addr = addr
        self.temp = bytearray(2)
        self.write_list = [b"\\x40", None]
        super().__init__(width, height, external_vcc)

    def write_cmd(self, cmd):
        self.temp[0] = 0x80
        self.temp[1] = cmd
        self.i2c.writeto(self.addr, self.temp)

    def write_data(self, buf):
        self.write_list[1] = buf
        self.i2c.writevto(self.addr, self.write_list)
'''


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

def executar_pipeline_wokwi(llm: ChatOllama, pedido_usuario: str) -> tuple[str, str, str]:
    """
    Pipeline especializado para projetos embarcados no simulador Wokwi.
    Suporta múltiplos microcontroladores (Pi Pico, ESP32, Arduino Uno/Mega/Nano, STM32)
    e múltiplas linguagens (MicroPython, C/C++ Arduino, C/C++ SDK Nativo, CircuitPython).
    """
    perfil = detectar_perfil_projeto(pedido_usuario)
    board_nome = perfil["board_nome"]
    board_type = perfil["board_type"]
    linguagem = perfil["linguagem"]
    arq_codigo = perfil["arq_codigo"]
    bloco_md = perfil["bloco_md"]

    if linguagem == "MicroPython":
        diretriz_sdk = (
            "Linguagem: MicroPython nativo (`from machine import ...`, `import time`, `import json`). "
            "Se houver DHT22/DHT11 use `import dht` com `.measure()`, `.temperature()` e `.humidity()`. "
            "Se houver OLED SSD1306 use `from ssd1306 import SSD1306_I2C`. "
            "Use temporização não-bloqueante com `time.ticks_ms()` e `time.ticks_diff()`. "
            "PROIBIDO importar `Adafruit_*`, `board`, `digitalio` ou `wokwi_gpio`."
        )
    elif "Arduino" in linguagem:
        diretriz_sdk = (
            "Linguagem: C/C++ (Arduino Framework - `sketch.ino`). "
            "Estruture com `#include` necessários, `void setup()` e `void loop()`. "
            "Use temporização não-bloqueante com `unsigned long millis()` (evite `delay()` longo). "
            "Use `Serial.begin(115200)` (ou `9600` no Uno) para telemetria serial."
        )
    else:
        diretriz_sdk = (
            f"Linguagem: {linguagem} (arquivo `{arq_codigo}`). "
            "Escreva código limpo, modular e não-bloqueante respeitando os pinos da placa."
        )

    regra_isolamento = (
        "REGRA DE OURO DE ISOLAMENTO DE ESCOPO: Inclua EXCLUSIVAMENTE os componentes, sensores, "
        "atuadores e pinos solicitados no PEDIDO do usuário. É TERMINANTEMENTE PROIBIDO inventar ou "
        "acrescentar servo motor, potenciômetro, LDR, botão ou qualquer outro periférico que NÃO "
        "tenha sido pedido explicitamente pelo usuário."
    )

    escopo = executar_agente(
        llm=llm,
        nome_agente=f"Gerente de Projetos ({board_nome} / {linguagem})",
        icone="🎯",
        cor="yellow",
        system_prompt=(
            f"Você é um Gerente de Projetos Sênior de Sistemas Embarcados especialista no simulador Wokwi "
            f"com a placa {board_nome} (`{board_type}`) utilizando {linguagem}. "
            f"{regra_isolamento} "
            f"Analise o pedido e produza um documento de escopo técnico fiel. Sem comentários extras."
        ),
        user_prompt=(
            f"Analise o pedido abaixo para a plataforma Wokwi ({board_nome} / {linguagem}) "
            f"e produza um Documento de Escopo objetivo:\n\n"
            f"PEDIDO:\n{pedido_usuario}\n\n"
            f"Entregue:\n"
            f"1. Placa alvo (`{board_type}`) e Mapa de Hardware contendo SOMENTE os componentes e pinos solicitados no pedido\n"
            f"2. Requisitos Funcionais detalhados (intervalos de leitura, lógica de acionamento, interface/display e telemetria serial se aplicável)\n"
            f"3. Requisitos Não Funcionais e Tratamento de Falhas\n"
            f"4. Restrições de Plataforma: {diretriz_sdk}"
        ),
    )

    arquitetura = executar_agente(
        llm=llm,
        nome_agente=f"Arquiteto de Sistemas ({board_nome} / {linguagem})",
        icone="🏗️",
        cor="blue",
        system_prompt=(
            f"Você é um Arquiteto de Firmware Sênior para {board_nome} (`{board_type}`) em {linguagem} no Wokwi. "
            f"Sua função é definir APENAS a especificação técnica e as assinaturas das funções para `{arq_codigo}`. "
            f"NÃO implemente o código final completo nesta etapa. "
            f"{regra_isolamento}\n"
            f"{diretriz_sdk}"
        ),
        user_prompt=(
            f"Com base no escopo abaixo, especifique a arquitetura técnica em {linguagem} para {board_nome} no Wokwi.\n\n"
            f"=== ESCOPO ===\n{escopo}\n\n"
            f"Liste de forma concisa (máximo 180 palavras, SEM implementar o código completo):\n"
            f"1. Inicialização APENAS dos periféricos e pinos presentes no escopo (NÃO adicione servo, ADC ou botões se não estiverem no escopo)\n"
            f"2. Assinaturas das funções e regras exatas de negócio/prioridade definidas no escopo\n"
            f"3. Estrutura do loop principal não-bloqueante respeitando os intervalos em milissegundos do escopo."
        ),
    )

    codigo = executar_agente(
        llm=llm,
        nome_agente=f"Desenvolvedor Embarcado ({board_nome} / {linguagem})",
        icone="💻",
        cor="green",
        system_prompt=(
            f"Você é um Desenvolvedor Sênior de Sistemas Embarcados para {board_nome} (`{board_type}`) em {linguagem} no Wokwi. "
            f"Sua tarefa é escrever:\n"
            f"1) O código completo do arquivo `{arq_codigo}` dentro de um único bloco ```{bloco_md} ... ```.\n"
            f"2) Em seguida, o arquivo `diagram.json` válido do Wokwi dentro de um bloco ```json ... ```.\n"
            f"{regra_isolamento}\n"
            f"{diretriz_sdk}"
        ),
        user_prompt=(
            f"Escreva agora o código COMPLETO de `{arq_codigo}` em {linguagem} para {board_nome} (`{board_type}`) "
            f"e o `diagram.json` correspondente no Wokwi, seguindo rigorosamente o pedido e a arquitetura abaixo:\n\n"
            f"=== PEDIDO ORIGINAL ===\n{pedido_usuario}\n\n"
            f"=== ARQUITETURA ===\n{arquitetura}\n\n"
            f"REGRAS OBRIGATÓRIAS:\n"
            f"- Implemente SOMENTE os componentes e pinos do pedido (NÃO adicione servo, LDR, potenciômetro ou botão se não foram pedidos).\n"
            f"- Respeite exatamente os textos de display, limiares de temperatura/umidade, cores de LED e formato JSON serial especificados.\n"
            f"- Entregue primeiro o bloco ```{bloco_md} ... ``` com o código completo de `{arq_codigo}`.\n"
            f"- Depois entregue o bloco ```json ... ``` com o `diagram.json` no formato oficial Wokwi (`\"version\": 1, \"author\": \"EdgeAI\", \"editor\": \"wokwi\", \"parts\": [...], \"connections\": [...]`)."
        ),
    )
    return escopo, arquitetura, codigo


def executar_pipeline(llm: ChatOllama, pedido_usuario: str) -> tuple[str, str, str]:
    """
    Executa o pipeline sequencial de 3 agentes:
    GP (Escopo) → Arquiteto (Design) → Desenvolvedor (Código+Testes)

    Cada etapa recebe o resultado da anterior como contexto.
    """
    if eh_pedido_wokwi(pedido_usuario):
        return executar_pipeline_wokwi(llm, pedido_usuario)

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


def sanitizar_codigo_micropython(codigo: str) -> str:
    """
    Corrige deslizes comuns de geração de LLMs para MicroPython no Wokwi:
    - Garante chamada de método em .temperature() e .humidity() do módulo dht.
    - Garante instância de dht_sensor = dht.DHT22(Pin(15)) e tela_atual = 0.
    """
    codigo = re.sub(r"(\bdht\w*\.temperature)(?!\s*\()", r"\1()", codigo)
    codigo = re.sub(r"(\bdht\w*\.humidity)(?!\s*\()", r"\1()", codigo)
    if "dht_sensor" in codigo and not re.search(r"^\s*dht_sensor\s*=", codigo, re.MULTILINE):
        codigo = codigo.replace(
            "import dht",
            "import dht\ndht_sensor = dht.DHT22(Pin(15))",
            1,
        )
    if "tela_atual" in codigo and not re.search(r"^\s*tela_atual\s*=", codigo, re.MULTILINE):
        codigo = "tela_atual = 0\n" + codigo
    return codigo


def gerar_firmware_uf2_wokwi(codigo_main: str, codigo_ssd1306: str, destino_uf2: str) -> bool:
    """
    Empacota main.py e ssd1306.py em uma partição LittleFS2 (0x100A0000) anexada ao
    firmware MicroPython base do Raspberry Pi Pico (firmware_base.uf2).
    Permite que a extensão Wokwi Simulator do VS Code execute main.py automaticamente no boot.
    """
    import struct
    pasta_base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artifacts")
    caminho_base_uf2 = os.path.join(pasta_base, "firmware_base.uf2")
    if not os.path.exists(caminho_base_uf2):
        return False

    try:
        from littlefs import LittleFS

        # Inicializa buffer com 0xFF (estado apagado da memória Flash NOR)
        fs = LittleFS(
            block_size=4096,
            block_count=352,
            read_size=256,
            prog_size=256,
            cache_size=256,
            lookahead_size=32,
        )
        with fs.open("ssd1306.py", "w") as f:
            f.write(codigo_ssd1306)
        with fs.open("main.py", "w") as f:
            f.write(codigo_main)

        lfs_buf = bytes(fs.context.buffer)
        blocos_usados = [
            blk_idx
            for blk_idx in range(352)
            if any(b != 0xFF and b != 0x00 for b in lfs_buf[blk_idx * 4096 : (blk_idx + 1) * 4096])
        ]

        raw_base = open(caminho_base_uf2, "rb").read()
        num_base_blocks = len(raw_base) // 512

        novos_payloads = []
        base_lfs_addr = 0x100A0000
        for blk_idx in blocos_usados:
            bloco_4k = lfs_buf[blk_idx * 4096 : (blk_idx + 1) * 4096]
            for page in range(16):  # 16 páginas de 256 bytes por setor de 4096 bytes
                addr = base_lfs_addr + blk_idx * 4096 + page * 256
                chunk = bloco_4k[page * 256 : (page + 1) * 256]
                novos_payloads.append((addr, chunk))

        total_blocks = num_base_blocks + len(novos_payloads)
        out = bytearray()

        # Regrava os blocos do firmware base atualizando total_blocks
        for i in range(num_base_blocks):
            blk = bytearray(raw_base[i * 512 : (i + 1) * 512])
            struct.pack_into("<II", blk, 20, i, total_blocks)
            out.extend(blk)

        # Anexa os blocos UF2 da partição LittleFS2
        for idx, (addr, chunk) in enumerate(novos_payloads):
            seq = num_base_blocks + idx
            header = struct.pack(
                "<IIIIIIII",
                0x0A324655,
                0x9E5D5157,
                0x00002000,
                addr,
                256,
                seq,
                total_blocks,
                0xE48BFF56,
            )
            padding = b"\x00" * (476 - 256)
            footer = struct.pack("<I", 0x0AB16F30)
            out.extend(header + chunk + padding + footer)

        with open(destino_uf2, "wb") as f_out:
            f_out.write(out)
        return True
    except Exception:
        return False


def extrair_libraries_txt(codigo: str) -> str:
    """Detecta headers C/C++ (#include) e gera o conteúdo de libraries.txt para o Wokwi."""
    mapa_libs = {
        "DHT.h": ["DHT sensor library", "Adafruit Unified Sensor"],
        "DHTesp.h": ["DHT sensor library for ESPx"],
        "Adafruit_SSD1306.h": ["Adafruit SSD1306", "Adafruit GFX Library"],
        "U8g2lib.h": ["U8g2"],
        "LiquidCrystal_I2C.h": ["LiquidCrystal I2C"],
        "ESP32Servo.h": ["ESP32Servo"],
        "Servo.h": ["Servo"],
        "OneWire.h": ["OneWire"],
        "DallasTemperature.h": ["DallasTemperature"],
        "ArduinoJson.h": ["ArduinoJson"],
        "PubSubClient.h": ["PubSubClient"],
    }
    libs = []
    for header, nomes in mapa_libs.items():
        if header.lower() in codigo.lower():
            for n in nomes:
                if n not in libs:
                    libs.append(n)
    return "\n".join(libs) + ("\n" if libs else "")


def construir_diagram_dinamico(
    pedido_usuario: str, escopo: str, arquitetura: str, codigo: str, perfil: dict
) -> dict:
    """
    Constrói ou valida o diagram.json de forma 100% dinâmica com base APENAS nos
    componentes solicitados no pedido do usuário e na placa selecionada.
    Nunca adiciona componentes que não foram solicitados no pedido.
    """
    board_type = perfil["board_type"]
    board_id = perfil["board_id"]
    texto_pedido = (pedido_usuario if pedido_usuario.strip() else f"{escopo}\n{codigo}").lower()

    # 1. Tenta aproveitar JSON gerado pelo LLM se já estiver 100% no schema Wokwi
    padrao_json = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)
    for fonte in (codigo, arquitetura, escopo):
        for match in padrao_json.findall(fonte):
            try:
                obj = json.loads(match)
                if (
                    isinstance(obj, dict)
                    and isinstance(obj.get("parts"), list)
                    and isinstance(obj.get("connections"), list)
                    and obj["parts"]
                    and obj["connections"]
                    and isinstance(obj["parts"][0], dict)
                    and "type" in obj["parts"][0]
                    and "id" in obj["parts"][0]
                    and isinstance(obj["connections"][0], list)
                    and len(obj["connections"][0]) >= 2
                ):
                    for idx, p in enumerate(obj["parts"]):
                        p.setdefault("top", 0 if idx == 0 else -120 + (idx * 65))
                        p.setdefault("left", 0 if idx == 0 else (-160 if idx % 2 == 1 else 160))
                        p.setdefault("attrs", {})
                    obj.setdefault("version", 1)
                    obj.setdefault("author", "EdgeAI")
                    obj.setdefault("editor", "wokwi")
                    obj.setdefault("dependencies", {})
                    return obj
            except Exception:
                continue

    return _montar_partes_dinamicas(texto_pedido, board_type, board_id)


def _montar_partes_dinamicas(texto_pedido: str, board_type: str, board_id: str) -> dict:
    """Monta parts e connections no schema oficial do Wokwi apenas para os componentes do pedido."""
    parts = [{"type": board_type, "id": board_id, "top": 0, "left": 0, "attrs": {}}]
    connections = []

    if board_id == "pico":
        vcc_pin = f"{board_id}:3V3"
        gnd_pins = [f"{board_id}:GND.{i}" for i in range(1, 8)]
        sda_default, scl_default = "GP4", "GP5"
    elif board_id == "esp":
        vcc_pin = f"{board_id}:3V3"
        gnd_pins = [f"{board_id}:GND.1", f"{board_id}:GND.2", f"{board_id}:GND.3"]
        sda_default, scl_default = "21", "22"
    else:
        vcc_pin = f"{board_id}:5V"
        gnd_pins = [f"{board_id}:GND.1", f"{board_id}:GND.2", f"{board_id}:GND.3"]
        sda_default, scl_default = "A4", "A5"

    gnd_idx = 0

    def proximo_gnd() -> str:
        nonlocal gnd_idx
        p = gnd_pins[gnd_idx % len(gnd_pins)]
        gnd_idx += 1
        return p

    # DHT22 / DHT11
    if "dht22" in texto_pedido or "dht11" in texto_pedido:
        dht_type = "wokwi-dht22" if "dht22" in texto_pedido else "wokwi-dht11"
        m_dht = re.search(r"dht.*?(gp\d+|d\d+|\b\d+\b)", texto_pedido)
        pino_dht = m_dht.group(1).upper() if m_dht else ("GP15" if board_id == "pico" else "4")
        if board_id == "pico" and pino_dht.isdigit():
            pino_dht = f"GP{pino_dht}"
        parts.append({"type": dht_type, "id": "dht1", "top": -130, "left": -140, "attrs": {}})
        connections.extend([
            ["dht1:VCC", vcc_pin, "red", []],
            ["dht1:GND", proximo_gnd(), "black", []],
            ["dht1:SDA", f"{board_id}:{pino_dht}", "green", []],
        ])

    # OLED SSD1306
    if "ssd1306" in texto_pedido or "oled" in texto_pedido:
        parts.append(
            {"type": "board-ssd1306", "id": "oled1", "top": 120, "left": -160, "attrs": {"i2cAddress": "0x3c"}}
        )
        connections.extend([
            ["oled1:VCC", vcc_pin, "red", []],
            ["oled1:GND", proximo_gnd(), "black", []],
            ["oled1:SDA", f"{board_id}:{sda_default}", "blue", []],
            ["oled1:SCL", f"{board_id}:{scl_default}", "cyan", []],
        ])

    # LED RGB (wokwi-rgb-led)
    if "wokwi-rgb-led" in texto_pedido or "led rgb" in texto_pedido or "rgb" in texto_pedido:
        com_attr = "cathode" if ("cathode" in texto_pedido or "cátodo" in texto_pedido or "catodo" in texto_pedido) else "anode"
        parts.extend([
            {"type": "wokwi-rgb-led", "id": "rgb1", "top": 40, "left": 150, "attrs": {"common": com_attr}},
            {"type": "wokwi-resistor", "id": "r_red", "top": 110, "left": 110, "attrs": {"value": "220"}},
            {"type": "wokwi-resistor", "id": "r_green", "top": 110, "left": 150, "attrs": {"value": "220"}},
            {"type": "wokwi-resistor", "id": "r_blue", "top": 110, "left": 190, "attrs": {"value": "220"}},
        ])
        pin_r = "GP16" if board_id == "pico" else "9"
        pin_g = "GP17" if board_id == "pico" else "10"
        pin_b = "GP18" if board_id == "pico" else "11"
        connections.extend([
            ["rgb1:COM", proximo_gnd() if com_attr == "cathode" else vcc_pin, "black", []],
            [f"{board_id}:{pin_r}", "r_red:1", "red", []],
            ["r_red:2", "rgb1:R", "red", []],
            [f"{board_id}:{pin_g}", "r_green:1", "green", []],
            ["r_green:2", "rgb1:G", "green", []],
            [f"{board_id}:{pin_b}", "r_blue:1", "blue", []],
            ["r_blue:2", "rgb1:B", "blue", []],
        ])
    elif "wokwi-led" in texto_pedido or re.search(r"\bled\b", texto_pedido):
        cores_leds = []
        if "verde" in texto_pedido or "green" in texto_pedido:
            cores_leds.append(("led_g", "green", "GP16" if board_id == "pico" else "12"))
        if "amarelo" in texto_pedido or "yellow" in texto_pedido:
            cores_leds.append(("led_y", "yellow", "GP17" if board_id == "pico" else "13"))
        if "vermelho" in texto_pedido or "red" in texto_pedido:
            cores_leds.append(("led_r", "red", "GP18" if board_id == "pico" else "14"))
        if not cores_leds:
            cores_leds.append(("led1", "red", "GP16" if board_id == "pico" else "13"))
        gnd_led = proximo_gnd()
        for idx, (lid, cor, pino) in enumerate(cores_leds):
            rid = f"r_{lid}"
            left_pos = -150 + idx * 45
            parts.append({"type": "wokwi-led", "id": lid, "top": 40, "left": left_pos, "attrs": {"color": cor}})
            parts.append({"type": "wokwi-resistor", "id": rid, "top": 90, "left": left_pos, "attrs": {"value": "220"}})
            connections.extend([
                [f"{board_id}:{pino}", f"{rid}:1", cor, []],
                [f"{rid}:2", f"{lid}:A", cor, []],
                [f"{lid}:C", gnd_led, "black", []],
            ])

    # Photoresistor / LDR (somente se pedido)
    if "photoresistor" in texto_pedido or "ldr" in texto_pedido or "fotoresistor" in texto_pedido:
        pino_ldr = "GP26" if board_id == "pico" else ("34" if board_id == "esp" else "A0")
        parts.append({"type": "wokwi-photoresistor-sensor", "id": "ldr1", "top": -120, "left": 130, "attrs": {}})
        connections.extend([
            ["ldr1:VCC", vcc_pin, "red", []],
            ["ldr1:GND", proximo_gnd(), "black", []],
            ["ldr1:AO", f"{board_id}:{pino_ldr}", "orange", []],
        ])

    # Potenciômetro (somente se pedido)
    if "potentiometer" in texto_pedido or "potenciômetro" in texto_pedido or "potenciometro" in texto_pedido:
        pino_pot = "GP27" if board_id == "pico" else ("35" if board_id == "esp" else "A1")
        parts.append({"type": "wokwi-potentiometer", "id": "pot1", "top": -20, "left": 170, "attrs": {}})
        connections.extend([
            ["pot1:VCC", vcc_pin, "red", []],
            ["pot1:GND", proximo_gnd(), "black", []],
            ["pot1:SIG", f"{board_id}:{pino_pot}", "purple", []],
        ])

    # Servo Motor (somente se pedido)
    if "wokwi-servo" in texto_pedido or "servo" in texto_pedido:
        pino_servo = "GP13" if board_id == "pico" else ("18" if board_id == "esp" else "9")
        v_servo = f"{board_id}:VBUS" if board_id == "pico" else vcc_pin
        parts.append({"type": "wokwi-servo", "id": "servo1", "top": 120, "left": 150, "attrs": {}})
        connections.extend([
            ["servo1:V+", v_servo, "red", []],
            ["servo1:GND", proximo_gnd(), "black", []],
            ["servo1:PWM", f"{board_id}:{pino_servo}", "orange", []],
        ])

    # Pushbutton (somente se pedido)
    if "pushbutton" in texto_pedido or "botão" in texto_pedido or "botao" in texto_pedido:
        pino_btn = "GP14" if board_id == "pico" else ("4" if board_id == "esp" else "2")
        parts.append({"type": "wokwi-pushbutton", "id": "btn1", "top": -80, "left": -40, "attrs": {"color": "blue"}})
        connections.extend([
            ["btn1:1.l", f"{board_id}:{pino_btn}", "blue", []],
            ["btn1:2.r", proximo_gnd(), "black", []],
        ])

    return {
        "version": 1,
        "author": "EdgeAI",
        "editor": "wokwi",
        "parts": parts,
        "connections": connections,
        "dependencies": {},
    }


def salvar_artefatos(escopo: str, arquitetura: str, codigo: str, pedido_usuario: str = ""):
    """Salva os artefatos gerados na pasta 'artifacts/' local (multi-MCU e multi-linguagem)."""
    pasta_base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artifacts")
    perfil = detectar_perfil_projeto(f"{pedido_usuario}\n{escopo}")
    modo_wokwi = perfil["modo_wokwi"]
    arq_codigo = perfil["arq_codigo"]
    linguagem = perfil["linguagem"]
    board_id = perfil["board_id"]

    # Criar pasta específica para esta execução com timestamp (Histórico)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pasta_run = os.path.join(pasta_base, f"run_{timestamp}")
    os.makedirs(pasta_run, exist_ok=True)

    # Extrair o maior bloco de código (python, cpp, c, ino) de codigo ou arquitetura
    blocos_cod = re.findall(
        r"```(?:python|cpp|c\+\+|c|ino|arduino)\s*(.*?)\s*```",
        f"{codigo}\n{arquitetura}",
        re.DOTALL | re.IGNORECASE,
    )
    if not blocos_cod:
        blocos_cod = [
            b
            for b in re.findall(r"```\s*(.*?)\s*```", codigo, re.DOTALL)
            if not b.strip().startswith("{")
        ]
    if blocos_cod:
        codigo_limpo = max(blocos_cod, key=len).strip()
    else:
        codigo_limpo = codigo.strip()

    if modo_wokwi and linguagem == "MicroPython":
        codigo_limpo = sanitizar_codigo_micropython(codigo_limpo)

    # Formatar cadeia de raciocínio completa
    raciocinio_completo = (
        f"# Cadeia de Raciocínio Multi-Agente\n\n"
        f"Execução: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
        f"Modelo: `{OLLAMA_MODEL}` | Placa: `{perfil['board_nome']}` | Linguagem: `{linguagem}`\n\n"
        f"---\n\n"
        f"## 🎯 1. Gerente de Projetos (Escopo & Requisitos)\n\n"
        f"{escopo}\n\n"
        f"---\n\n"
        f"## 🏗️ 2. Arquiteto de Sistemas (Design Técnico)\n\n"
        f"{arquitetura}\n\n"
        f"---\n\n"
        f"## 💻 3. Desenvolvedor ({linguagem})\n\n"
        f"{codigo}\n"
    )

    arquivos_gerados = [
        ("escopo.md", escopo),
        ("arquitetura.md", arquitetura),
        ("codigo.py", codigo_limpo),
        ("raciocinio.md", raciocinio_completo),
    ]

    usa_ssd1306 = "ssd1306" in f"{pedido_usuario}\n{codigo_limpo}".lower()

    if modo_wokwi:
        diagram_dict = construir_diagram_dinamico(pedido_usuario, escopo, arquitetura, codigo, perfil)
        diagram_str = json.dumps(diagram_dict, indent=2, ensure_ascii=False)
        arquivos_gerados.append((arq_codigo, codigo_limpo))
        arquivos_gerados.append(("diagram.json", diagram_str))

        if linguagem == "MicroPython" and usa_ssd1306:
            arquivos_gerados.append(("ssd1306.py", DRIVER_SSD1306_MICROPYTHON))

        if "Arduino" in linguagem or arq_codigo.endswith((".ino", ".cpp", ".c")):
            libs_txt = extrair_libraries_txt(codigo_limpo)
            if libs_txt:
                arquivos_gerados.append(("libraries.txt", libs_txt))

        wokwi_toml = (
            "[wokwi]\n"
            "version = 1\n"
            'firmware = "firmware.uf2"\n'
            'elf = "firmware.uf2"\n'
            "rfc2217ServerPort = 4000\n"
        )
        arquivos_gerados.append(("wokwi.toml", wokwi_toml))

    # 1. Salvar na subpasta da execução (Histórico)
    for nome_arq, conteudo in arquivos_gerados:
        with open(os.path.join(pasta_run, nome_arq), "w", encoding="utf-8") as f:
            f.write(conteudo)

    # 2. Salvar/Atualizar na raiz de artifacts/ como "latest" (Última versão)
    os.makedirs(pasta_base, exist_ok=True)
    for nome_arq, conteudo in arquivos_gerados:
        with open(os.path.join(pasta_base, nome_arq), "w", encoding="utf-8") as f:
            f.write(conteudo)

    if modo_wokwi and linguagem == "MicroPython" and board_id == "pico":
        uf2_run = os.path.join(pasta_run, "firmware.uf2")
        uf2_latest = os.path.join(pasta_base, "firmware.uf2")
        ssd_code = DRIVER_SSD1306_MICROPYTHON if usa_ssd1306 else ""
        if gerar_firmware_uf2_wokwi(codigo_limpo, ssd_code, uf2_run):
            import shutil
            shutil.copyfile(uf2_run, uf2_latest)

    console.print(f"[bold green]✓ Histórico gravado em:[/bold green] [cyan]{pasta_run}/[/cyan]")
    console.print(f"[bold green]✓ Versão mais recente atualizada em:[/bold green] [cyan]{pasta_base}/[/cyan]")
    if modo_wokwi:
        nomes_wokwi = ", ".join(n for n, _ in arquivos_gerados if n not in ("escopo.md", "arquitetura.md", "raciocinio.md"))
        console.print(
            f"[bold cyan]✓ Artefatos Wokwi ({perfil['board_nome']} / {linguagem}):[/bold cyan] "
            f"[white]{nomes_wokwi}[/white]"
        )


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
            f"[dim]Pipeline Direto LLM | Ollama | {OLLAMA_MODEL} (INT4/GGUF)[/dim]\n"
            "[dim]GP → Arquiteto → Desenvolvedor | Suporte Nativo Wokwi / MicroPython[/dim]"
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

    llm = criar_llm(temperatura=0.1, max_tokens=2500)
    console.print("[bold green]✓[/bold green] LLM pronto\n")

    # Execução
    console.print(Rule("[bold cyan]Iniciando Pipeline Multi-Agente[/bold cyan]"))

    inicio_total = time.time()

    try:
        escopo, arquitetura, codigo = executar_pipeline(llm, pedido_usuario)
        salvar_artefatos(escopo, arquitetura, codigo, pedido_usuario)
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
