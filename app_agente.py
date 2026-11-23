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

import ast
import io
import json
import os
import re
import subprocess
import sys
import time
import traceback
import types
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

OLLAMA_BASE_URL   = "http://localhost:11434"
OLLAMA_MODEL      = "qwen2.5-coder:3b"
CONTEXT_WINDOW    = 4096   # Travado — evita crash de VRAM na MX110
MAX_TENTATIVAS_QA = 3      # Limite de iterações do Loop Dinâmico de Auto-Correção


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
    if "pico w" in texto or "wokwi-pi-pico-w" in texto:
        board_type, board_id, board_nome = "wokwi-pi-pico-w", "pico", "Raspberry Pi Pico W"
    elif any(k in texto for k in ("pi pico", "raspberry pi pico", "rp2040", "wokwi-pi-pico")):
        board_type, board_id, board_nome = "wokwi-pi-pico", "pico", "Raspberry Pi Pico (RP2040)"
    elif "esp32-s3" in texto or "esp32s3" in texto:
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
            f"Linguagem: MicroPython nativo para {board_nome}. "
            "SEMPRE inclua no topo todos os imports usados: `import machine`, `from machine import Pin, I2C`, `import time`, `import json`. "
            "Se houver DHT22/DHT11: faça `import dht` e instancie OBRIGATORIAMENTE no escopo global com prefixo do módulo `dht.DHT22(Pin(15))` (NUNCA use `DHT22(...)` sem `dht.`), lendo com `.measure()`, `.temperature()` e `.humidity()`. "
            "Se houver OLED SSD1306: use `from ssd1306 import SSD1306_I2C` (NUNCA recrie a classe SSD1306_I2C) e inicialize o I2C informando o ID do barramento 0: `I2C(0, scl=Pin(5), sda=Pin(4), freq=400000)`. "
            "Instancie TODOS os periféricos (Pin, I2C, DHT, OLED, LED RGB) no escopo global (fora de qualquer função). "
            "Para LED RGB: use 3 pinos separados (`led_r = Pin(16, Pin.OUT)`, `led_g = Pin(17, Pin.OUT)`, `led_b = Pin(18, Pin.OUT)`). NUNCA passe tupla para Pin(). "
            "SEMPRE inicialize todas as variáveis de telemetria (ex: `temp = None`, `hum = None`, `cor_atual = 'OFF'`) ANTES do loop while True para evitar UnboundLocalError. "
            "Use contadores não-bloqueantes com offset (`last_dht = time.ticks_ms() - 2000`, `last_oled = time.ticks_ms() - 1000`) com `time.ticks_diff()` e `time.sleep_ms(50)` no fim do loop. "
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
            f"NÃO escreva blocos de código implementados e NUNCA altere os limiares numéricos ou textos do escopo. "
            f"{regra_isolamento}\n"
            f"{diretriz_sdk}"
        ),
        user_prompt=(
            f"Com base no escopo abaixo, especifique a arquitetura técnica em {linguagem} para {board_nome} no Wokwi.\n\n"
            f"=== ESCOPO ===\n{escopo}\n\n"
            f"Liste de forma concisa (máximo 200 palavras, SEM escrever blocos de código implementados):\n"
            f"1. Imports obrigatórios e inicialização APENAS dos periféricos e pinos presentes no escopo (`dht.DHT22(Pin(...))`, `I2C(0, scl=Pin(...), sda=Pin(...))`, `Pin(..., Pin.OUT)`)\n"
            f"2. Assinaturas das funções preservando EXATAMENTE todas as faixas numéricas de temperatura/umidade, textos do OLED e chaves do JSON serial definidos no escopo\n"
            f"3. Estrutura de estado do loop principal não-bloqueante com `time.ticks_ms()` e `time.ticks_diff()` respeitando cada intervalo independente em ms."
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
            f"1) O código completo, funcional e sem erros de importação do arquivo `{arq_codigo}` dentro de um único bloco ```{bloco_md} ... ```.\n"
            f"2) Em seguida, o arquivo `diagram.json` válido do Wokwi dentro de um bloco ```json ... ```.\n"
            f"{regra_isolamento}\n"
            f"{diretriz_sdk}"
        ),
        user_prompt=(
            f"Escreva agora o código COMPLETO de `{arq_codigo}` em {linguagem} para {board_nome} (`{board_type}`) "
            f"e o `diagram.json` correspondente no Wokwi, seguindo rigorosamente o PEDIDO ORIGINAL abaixo:\n\n"
            f"=== PEDIDO ORIGINAL ===\n{pedido_usuario}\n\n"
            f"=== ARQUITETURA ===\n{arquitetura}\n\n"
            f"REGRAS OBRIGATÓRIAS:\n"
            f"- Inclua todos os imports no topo (`import machine`, `from machine import Pin, I2C`, `import dht`, `import time`, `import json`, `from ssd1306 import SSD1306_I2C`).\n"
            f"- Instancie TODOS os periféricos no ESCOPO GLOBAL logo após os imports: `dht_sensor = dht.DHT22(Pin(15))`, `i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=400000)`, `display = SSD1306_I2C(128, 64, i2c)`, e três pinos separados para o LED RGB: `led_r = Pin(16, Pin.OUT)`, `led_g = Pin(17, Pin.OUT)`, `led_b = Pin(18, Pin.OUT)`. NUNCA passe tupla para Pin().\n"
            f"- NUNCA reimplemente a classe SSD1306_I2C no main.py (use apenas `from ssd1306 import SSD1306_I2C`).\n"
            f"- Inicialize SEMPRE variáveis de leitura ANTES do while True: `temp = None`, `hum = None`, `cor_atual = 'OFF'`, e timers com offset: `last_dht = time.ticks_ms() - 2000`, `last_oled = time.ticks_ms() - 1000` (evita UnboundLocalError na primeira iteração).\n"
            f"- Implemente SOMENTE os componentes e pinos do pedido (NÃO adicione servo, LDR, potenciômetro ou botão se não foram pedidos).\n"
            f"- Respeite EXATAMENTE os textos de display (`MBA-FIAP`, `Temp: XX.X C`, `Umid: XX.X %`, `ERRO SENSOR`), todas as 4 faixas de temperatura/umidade e cores do LED RGB (`RED`, `BLUE`, `GREEN`, `YELLOW`, e `MAGENTA` em erro) e o formato JSON serial (`{{\"temp\": ..., \"hum\": ..., \"led_color\": ...}}`) do PEDIDO ORIGINAL.\n"
            f"- Use escalonamento não-bloqueante real com `time.ticks_ms()`, `time.ticks_diff()` e `time.sleep_ms(50)`.\n"
            f"- Entregue primeiro o bloco ```{bloco_md} ... ``` com o código completo de `{arq_codigo}`.\n"
            f"- Depois entregue o bloco ```json ... ``` com o `diagram.json` no formato oficial Wokwi (`\"version\": 1, \"author\": \"EdgeAI\", \"editor\": \"wokwi\", \"parts\": [...], \"connections\": [...]`)."
        ),
    )
    codigo = executar_loop_qa_e_correcao(llm, pedido_usuario, escopo, arquitetura, codigo)
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

    codigo = executar_loop_qa_e_correcao(llm, pedido_usuario, escopo, arquitetura, codigo)
    return escopo, arquitetura, codigo


MAPA_SIMBOLOS_MICROPYTHON = {
    "machine": "import machine",
    "Pin": "from machine import Pin",
    "I2C": "from machine import I2C",
    "SoftI2C": "from machine import SoftI2C",
    "SPI": "from machine import SPI",
    "SoftSPI": "from machine import SoftSPI",
    "PWM": "from machine import PWM",
    "ADC": "from machine import ADC",
    "UART": "from machine import UART",
    "Timer": "from machine import Timer",
    "RTC": "from machine import RTC",
    "WDT": "from machine import WDT",
    "time_pulse_us": "from machine import time_pulse_us",
    "dht": "import dht",
    "DHT22": "from dht import DHT22",
    "DHT11": "from dht import DHT11",
    "SSD1306_I2C": "from ssd1306 import SSD1306_I2C",
    "SSD1306_SPI": "from ssd1306 import SSD1306_SPI",
    "OneWire": "from onewire import OneWire",
    "DS18X20": "from ds18x20 import DS18X20",
    "NeoPixel": "from neopixel import NeoPixel",
    "const": "from micropython import const",
    "micropython": "import micropython",
    "framebuf": "import framebuf",
    "time": "import time",
    "utime": "import time as utime",
    "json": "import json",
    "ujson": "import json as ujson",
    "math": "import math",
    "random": "import random",
    "urandom": "import random as urandom",
    "struct": "import struct",
    "ustruct": "import struct as ustruct",
    "sys": "import sys",
    "gc": "import gc",
}


def extrair_bloco_codigo(codigo: str, arquitetura: str = "") -> str:
    """Extrai o bloco principal de código-fonte da resposta do agente Desenvolvedor."""
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
        return max(blocos_cod, key=len).strip()
    return codigo.strip()


def analisar_ast_codigo_python(codigo_limpo: str) -> dict:
    """Analisa estaticamente a AST do código Python/MicroPython (SyntaxError e nomes indefinidos)."""
    try:
        arvore = ast.parse(codigo_limpo)
    except SyntaxError as e:
        return {
            "ok": False,
            "erro_sintaxe": f"SyntaxError na linha {e.lineno}: {e.msg}",
            "indefinidos": [],
        }

    import builtins
    definidos = set(dir(builtins))
    definidos.update({"__name__", "__file__", "__doc__", "self", "cls"})
    usados = {}

    for node in ast.walk(arvore):
        if isinstance(node, ast.Import):
            for alias in node.names:
                definidos.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name != "*":
                    definidos.add(alias.asname or alias.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            definidos.add(node.name)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
                    definidos.add(arg.arg)
                if node.args.vararg:
                    definidos.add(node.args.vararg.arg)
                if node.args.kwarg:
                    definidos.add(node.args.kwarg.arg)
        elif isinstance(node, ast.Lambda):
            for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
                definidos.add(arg.arg)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            definidos.add(node.name)
        elif isinstance(node, ast.comprehension):
            for t in ast.walk(node.target):
                if isinstance(t, ast.Name):
                    definidos.add(t.id)
        elif isinstance(node, ast.NamedExpr) and isinstance(node.target, ast.Name):
            definidos.add(node.target.id)
        elif isinstance(node, ast.Name):
            if isinstance(node.ctx, (ast.Store, ast.Del)):
                definidos.add(node.id)
            elif isinstance(node.ctx, ast.Load):
                usados.setdefault(node.id, getattr(node, "lineno", 0))

    indefinidos = [
        (nome, linha)
        for nome, linha in sorted(usados.items(), key=lambda x: x[1])
        if nome not in definidos
    ]
    return {"ok": len(indefinidos) == 0, "erro_sintaxe": None, "indefinidos": indefinidos}


def _inferir_barramento_i2c_rp2040(match_i2c: re.Match) -> str:
    """Infere o ID do barramento I2C (0 ou 1) no RP2040 a partir dos pinos SDA/SCL."""
    prefixo = match_i2c.group(1)
    args = match_i2c.group(2)
    pinos_i2c1_sda = {2, 6, 10, 14, 18, 26}
    pinos_i2c1_scl = {3, 7, 11, 15, 19, 27}
    m_sda = re.search(r"sda\s*=\s*(?:machine\.)?Pin\s*\(\s*(\d+)", args)
    m_scl = re.search(r"scl\s*=\s*(?:machine\.)?Pin\s*\(\s*(\d+)", args)
    bus_id = 0
    if (m_sda and int(m_sda.group(1)) in pinos_i2c1_sda) or (
        m_scl and int(m_scl.group(1)) in pinos_i2c1_scl
    ):
        bus_id = 1
    return f"{prefixo}{bus_id}, {args}"


def sanitizar_codigo_micropython(codigo: str) -> str:
    """
    Normaliza e corrige deslizes de geração de LLMs para MicroPython no Wokwi:
    - Remove argumentos font=... alucinados por LLMs em display.text().
    - Garante parênteses em .temperature() e .humidity() do módulo dht.
    - Corrige DHT22(...) / DHT11(...) desqualificados para dht.DHT22(...) / dht.DHT11(...).
    - Infere automaticamente o ID do barramento I2C (0 ou 1) no RP2040 quando omitido.
    - Analisa a AST do código e injeta automaticamente qualquer import nativo ausente.
    """
    # Remove parâmetro inválido font=... em text() do framebuf/ssd1306
    codigo = re.sub(r",\s*font\s*=\s*[\w.]+", "", codigo)

    # Remove reimplementação dummy de SSD1306_I2C se o modelo inventou uma classe incompleta
    if re.search(r"class\s+SSD1306_I2C\b", codigo) and "framebuf.FrameBuffer" not in codigo:
        codigo = re.sub(
            r"class\s+SSD1306_I2C.*?(?=\ndef\s+|\n[a-zA-Z_]\w*\s*=|\Z)",
            "from ssd1306 import SSD1306_I2C\n",
            codigo,
            flags=re.DOTALL,
        )

    # Corrige tentativa de passar tupla para Pin()
    codigo = re.sub(
        r"Pin\s*\(\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)\s*,\s*Pin\.OUT\s*\)",
        r"Pin(\1, Pin.OUT)",
        codigo,
    )

    # Garante inicialização de temp e hum antes do while True para evitar UnboundLocalError
    m_while = re.search(r"^([ \t]*)while\s+True\s*:", codigo, re.MULTILINE)
    if m_while:
        ind = m_while.group(1)
        trecho_loop = codigo[m_while.start():]
        trecho_antes = codigo[:m_while.start()]
        if "temp" in trecho_loop and not re.search(rf"^{ind}temp\s*=", trecho_antes, re.MULTILINE):
            codigo = (
                codigo[:m_while.start()]
                + f"{ind}temp = None\n{ind}hum = None\n"
                + codigo[m_while.start():]
            )

    # Garante que timers não comecem com atraso desnecessário
    codigo = re.sub(r"last_dht\s*=\s*time\.ticks_ms\(\)(?!\s*-\s*\d+)", "last_dht = time.ticks_ms() - 2000", codigo)
    codigo = re.sub(r"last_oled\s*=\s*time\.ticks_ms\(\)(?!\s*-\s*\d+)", "last_oled = time.ticks_ms() - 1000", codigo)

    codigo = re.sub(r"(\bdht\w*\.temperature)(?!\s*\()", r"\1()", codigo)
    codigo = re.sub(r"(\bdht\w*\.humidity)(?!\s*\()", r"\1()", codigo)

    if not re.search(r"from\s+dht\s+import\s+.*?\bDHT(?:22|11)\b", codigo):
        codigo = re.sub(r"(?<![.\w])(DHT(?:22|11))\s*\(", r"dht.\1(", codigo)

    codigo = re.sub(
        r"(\bI2C\s*\()(\s*(?:scl|sda)\s*=[^)]+)",
        _inferir_barramento_i2c_rp2040,
        codigo,
    )

    analise = analisar_ast_codigo_python(codigo)
    imports_para_injetar = []

    for nome_indef, _ in analise.get("indefinidos", []):
        if nome_indef in MAPA_SIMBOLOS_MICROPYTHON:
            stmt = MAPA_SIMBOLOS_MICROPYTHON[nome_indef]
            if stmt not in imports_para_injetar and stmt not in codigo:
                imports_para_injetar.append(stmt)

    for padrao_mod, stmt_mod in (
        (r"\bmachine\.", "import machine"),
        (r"\bdht\.", "import dht"),
        (r"\bjson\.", "import json"),
        (r"\btime\.", "import time"),
    ):
        if re.search(padrao_mod, codigo) and not re.search(rf"^\s*{stmt_mod}\b", codigo, re.MULTILINE):
            if stmt_mod not in imports_para_injetar:
                imports_para_injetar.append(stmt_mod)

    if imports_para_injetar:
        codigo = "\n".join(imports_para_injetar) + "\n" + codigo

    if "dht_sensor" in codigo and not re.search(r"^dht_sensor\s*=", codigo, re.MULTILINE):
        if not re.search(r"\bimport\s+dht\b", codigo):
            codigo = "import dht\n" + codigo
        imps = [m.end() for m in re.finditer(r"^(?:import|from)\s+.*$", codigo, re.MULTILINE)]
        pos = imps[-1] if imps else 0
        codigo = codigo[:pos] + "\n\ndht_sensor = dht.DHT22(Pin(15))\n" + codigo[pos:]
    if "tela_atual" in codigo and not re.search(r"^\s*tela_atual\s*=", codigo, re.MULTILINE):
        codigo = "tela_atual = 0\n" + codigo
    return codigo


class _FimSimulacaoSandbox(BaseException):
    """Exceção interna (BaseException) para encerrar o while True do Sandbox após N ciclos."""


def executar_sandbox_micropython(codigo_limpo: str, board_id: str = "pico") -> dict:
    """
    Executa o código MicroPython em um Sandbox Real em memória que simula o
    firmware MicroPython v1.29 (RP2040 / ESP32):
    - Testa inicialização de Pin, I2C (validando id 0/1 no RP2040), PWM, ADC, DHT22/11 e SSD1306.
    - Executa múltiplos ciclos do loop principal avançando ticks_ms() automaticamente.
    - Simula leituras normais do DHT22 e injeta 1 falha OSError para validar resiliência (RNF02).
    """
    pinos_usados = set()
    textos_oled = []
    relogio_ms = [0]
    chamadas_ticks = [0]
    chamadas_sleep = [0]
    leituras_dht = [0]

    modulos_mock_nomes = (
        "machine", "dht", "ssd1306", "framebuf", "micropython",
        "onewire", "ds18x20", "neopixel", "utime", "ujson",
    )
    backup_sys_modules = {m: sys.modules.get(m) for m in modulos_mock_nomes}
    backup_time_attrs = {
        a: getattr(time, a)
        for a in ("ticks_ms", "ticks_us", "ticks_diff", "ticks_add", "sleep", "sleep_ms", "sleep_us")
        if hasattr(time, a)
    }

    class MockPin:
        IN, OUT, OPEN_DRAIN = 0, 1, 2
        PULL_UP, PULL_DOWN = 1, 2
        IRQ_RISING, IRQ_FALLING = 1, 2

        def __init__(self, pin_id, mode=-1, pull=-1, value=0):
            if isinstance(pin_id, (tuple, list)):
                raise TypeError(
                    f"Pin() não aceita tupla/lista {pin_id}. "
                    "Instancie cada pino separadamente (ex.: led_r = Pin(16, Pin.OUT), led_g = Pin(17, Pin.OUT), led_b = Pin(18, Pin.OUT))."
                )
            if isinstance(pin_id, int):
                pinos_usados.add(f"GP{pin_id}" if board_id == "pico" else str(pin_id))
            elif isinstance(pin_id, str):
                pinos_usados.add(pin_id.upper())
            self.id = pin_id
            self._val = value

        def value(self, x=None):
            if x is None:
                return self._val
            self._val = int(bool(x))

        def on(self):
            self._val = 1

        def off(self):
            self._val = 0

        def irq(self, handler=None, trigger=3):
            return None

    class MockI2C:
        def __init__(self, *args, **kwargs):
            if board_id == "pico" and (not args or not isinstance(args[0], int)):
                raise TypeError(
                    "I2C() no Raspberry Pi Pico (RP2040) exige o ID do barramento (0 ou 1) "
                    "como primeiro argumento posicional: I2C(0, scl=Pin(5), sda=Pin(4))"
                )
            self.args = args
            self.kwargs = kwargs

        def scan(self):
            return [0x3C, 0x27]

        def writeto(self, addr, buf, stop=True):
            return len(buf)

        def writevto(self, addr, vector, stop=True):
            return sum(len(b) for b in vector if b)

        def writeto_mem(self, addr, memaddr, buf):
            return None

        def readfrom_mem(self, addr, memaddr, nbytes):
            return bytes(nbytes)

    class MockPWM:
        def __init__(self, pin, freq=50, duty_u16=0):
            self.pin = pin
            self._freq = freq
            self._duty_u16 = duty_u16
            self._duty = 0

        def freq(self, val=None):
            if val is None:
                return self._freq
            self._freq = val

        def duty_u16(self, val=None):
            if val is None:
                return self._duty_u16
            self._duty_u16 = val

        def duty(self, val=None):
            if val is None:
                return self._duty
            self._duty = val

        def deinit(self):
            pass

    class MockADC:
        def __init__(self, pin):
            if isinstance(pin, int):
                pinos_usados.add(f"GP{pin}" if board_id == "pico" else str(pin))
            self.pin = pin

        def read_u16(self):
            return 32768

        def read(self):
            return 2048

    class MockTimer:
        ONE_SHOT, PERIODIC = 0, 1

        def __init__(self, id=-1):
            self.id = id

        def init(self, mode=1, period=-1, callback=None):
            if callable(callback):
                callback(self)

        def deinit(self):
            pass

    class MockDHTBase:
        CENARIOS = [
            (24.5, 55.0),
            (32.5, 25.0),
            (15.0, 80.0),
            (28.0, 50.0),
            "OSERROR",
        ]

        def __init__(self, pin):
            self.pin = pin
            self._temp = 24.5
            self._hum = 55.0

        def measure(self):
            idx = leituras_dht[0]
            leituras_dht[0] += 1
            cenario = self.CENARIOS[idx % len(self.CENARIOS)]
            if cenario == "OSERROR":
                raise OSError(110, "ETIMEDOUT: Simulated DHT sensor read failure")
            self._temp, self._hum = cenario

        def temperature(self):
            return self._temp

        def humidity(self):
            return self._hum

    class MockSSD1306:
        def __init__(self, width, height, i2c, addr=0x3C, external_vcc=False):
            self.width, self.height, self.i2c, self.addr = width, height, i2c, addr

        def fill(self, col):
            pass

        def pixel(self, x, y, col=1):
            pass

        def line(self, x1, y1, x2, y2, col=1):
            pass

        def hline(self, x, y, w, col=1):
            pass

        def vline(self, x, y, h, col=1):
            pass

        def rect(self, x, y, w, h, col=1):
            pass

        def fill_rect(self, x, y, w, h, col=1):
            pass

        def text(self, string, x, y, col=1):
            textos_oled.append(str(string))

        def show(self):
            pass

    def mock_ticks_ms():
        chamadas_ticks[0] += 1
        relogio_ms[0] += 500
        if chamadas_ticks[0] > 45:
            raise _FimSimulacaoSandbox()
        return relogio_ms[0]

    def mock_ticks_diff(end, start):
        return int(end) - int(start)

    def mock_ticks_add(ticks, delta):
        return int(ticks) + int(delta)

    def mock_sleep(segundos):
        chamadas_sleep[0] += 1
        relogio_ms[0] += int(float(segundos) * 1000)
        if chamadas_sleep[0] > 8:
            raise _FimSimulacaoSandbox()

    def mock_sleep_ms(ms):
        chamadas_sleep[0] += 1
        relogio_ms[0] += max(int(ms), 500)
        if chamadas_sleep[0] > 12:
            raise _FimSimulacaoSandbox()

    def mock_sleep_us(us):
        relogio_ms[0] += 1

    mod_machine = types.ModuleType("machine")
    mod_machine.Pin = MockPin
    mod_machine.I2C = MockI2C
    mod_machine.SoftI2C = MockI2C
    mod_machine.PWM = MockPWM
    mod_machine.ADC = MockADC
    mod_machine.Timer = MockTimer
    mod_machine.time_pulse_us = lambda pin, level, timeout=1000000: 1500
    mod_machine.reset = lambda: None
    mod_machine.freq = lambda f=None: 125000000

    mod_dht = types.ModuleType("dht")
    mod_dht.DHT22 = MockDHTBase
    mod_dht.DHT11 = MockDHTBase

    mod_ssd1306 = types.ModuleType("ssd1306")
    mod_ssd1306.SSD1306_I2C = MockSSD1306
    mod_ssd1306.SSD1306_SPI = MockSSD1306
    mod_ssd1306.SSD1306 = MockSSD1306

    mod_micropython = types.ModuleType("micropython")
    mod_micropython.const = lambda x: x

    mod_framebuf = types.ModuleType("framebuf")
    mod_framebuf.MONO_VLSB = 0
    mod_framebuf.FrameBuffer = object

    mod_onewire = types.ModuleType("onewire")
    mod_onewire.OneWire = lambda pin: pin

    mod_ds18x20 = types.ModuleType("ds18x20")
    mod_ds18x20.DS18X20 = type(
        "DS18X20", (), {
            "__init__": lambda self, ow: None,
            "scan": lambda self: [b"\x28\x00"],
            "convert_temp": lambda self: None,
            "read_temp": lambda self, rom: 25.0,
        },
    )

    mod_neopixel = types.ModuleType("neopixel")
    mod_neopixel.NeoPixel = type(
        "NeoPixel", (), {
            "__init__": lambda self, pin, n: setattr(self, "_buf", [(0, 0, 0)] * n),
            "__setitem__": lambda self, idx, val: None,
            "__getitem__": lambda self, idx: (0, 0, 0),
            "write": lambda self: None,
            "fill": lambda self, val: None,
        },
    )

    sys.modules["machine"] = mod_machine
    sys.modules["dht"] = mod_dht
    sys.modules["ssd1306"] = mod_ssd1306
    sys.modules["micropython"] = mod_micropython
    sys.modules["framebuf"] = mod_framebuf
    sys.modules["onewire"] = mod_onewire
    sys.modules["ds18x20"] = mod_ds18x20
    sys.modules["neopixel"] = mod_neopixel
    sys.modules["utime"] = time
    sys.modules["ujson"] = json

    time.ticks_ms = mock_ticks_ms
    time.ticks_us = lambda: relogio_ms[0] * 1000
    time.ticks_diff = mock_ticks_diff
    time.ticks_add = mock_ticks_add
    time.sleep = mock_sleep
    time.sleep_ms = mock_sleep_ms
    time.sleep_us = mock_sleep_us

    buffer_stdout = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buffer_stdout

    sucesso = True
    erro_execucao = None
    tb_resumido = ""

    try:
        ns = {"__name__": "__main__"}
        compilado = compile(codigo_limpo, "main.py", "exec")
        exec(compilado, ns)
    except _FimSimulacaoSandbox:
        sucesso = True
    except Exception as exc:
        sucesso = False
        tb_linhas = traceback.format_exception(type(exc), exc, exc.__traceback__)
        tb_filtrado = [l for l in tb_linhas if 'File "main.py"' in l or l == tb_linhas[-1]]
        tb_resumido = "".join(tb_filtrado).strip() or f"{type(exc).__name__}: {exc}"
        erro_execucao = f"{type(exc).__name__}: {exc}"
    finally:
        sys.stdout = old_stdout
        for m, orig in backup_sys_modules.items():
            if orig is None:
                sys.modules.pop(m, None)
            else:
                sys.modules[m] = orig
        for attr in ("ticks_ms", "ticks_us", "ticks_diff", "ticks_add", "sleep", "sleep_ms", "sleep_us"):
            if attr in backup_time_attrs:
                setattr(time, attr, backup_time_attrs[attr])
            elif hasattr(time, attr):
                delattr(time, attr)

    return {
        "ok": sucesso,
        "erro": erro_execucao,
        "traceback": tb_resumido,
        "stdout": buffer_stdout.getvalue().strip(),
        "pinos_usados": sorted(pinos_usados),
        "textos_oled": textos_oled,
        "ciclos_dht": leituras_dht[0],
    }


def executar_sandbox_python_desktop(codigo_limpo: str) -> dict:
    """Executa código Python desktop em subprocesso isolado com timeout para validar execução real."""
    try:
        proc = subprocess.run(
            [sys.executable, "-c", codigo_limpo],
            capture_output=True,
            text=True,
            timeout=5,
        )
        ok = proc.returncode == 0
        return {
            "ok": ok,
            "erro": None if ok else (proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "Erro de execução"),
            "traceback": proc.stderr.strip(),
            "stdout": proc.stdout.strip(),
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "erro": "TimeoutExpired: O código entrou em loop infinito ou demorou mais de 5s.",
            "traceback": "TimeoutExpired após 5 segundos",
            "stdout": "",
        }


def executar_verificacao_qa(
    codigo_bruto: str,
    pedido_usuario: str,
    escopo: str,
    arquitetura: str,
    perfil: dict,
) -> dict:
    """
    Executa a bateria completa de testes de QA sobre o código gerado:
    1. Análise Estática AST (SyntaxError e variáveis/imports indefinidos).
    2. Execução Real em Sandbox (MicroPython Mock RP2040/ESP32 ou Subprocesso Python).
    3. Validação Cruzada de Hardware e Requisitos (pinos no diagram.json, OLED e JSON serial).
    """
    codigo_limpo = extrair_bloco_codigo(codigo_bruto, arquitetura)
    linguagem = perfil["linguagem"]
    modo_wokwi = perfil["modo_wokwi"]
    board_id = perfil["board_id"]

    testes = []
    erros_detalhados = []

    if linguagem in ("MicroPython", "CircuitPython", "Python"):
        res_ast = analisar_ast_codigo_python(codigo_limpo)
        if res_ast["erro_sintaxe"]:
            testes.append(("AST & Sintaxe", False, res_ast["erro_sintaxe"]))
            erros_detalhados.append(res_ast["erro_sintaxe"])
        elif res_ast["indefinidos"]:
            nomes_str = ", ".join(f"'{n}' (linha {ln})" for n, ln in res_ast["indefinidos"])
            msg = f"NameError potencial — Símbolos usados sem import/definição: {nomes_str}"
            testes.append(("AST & Escopo de Imports", False, msg))
            erros_detalhados.append(msg)
        else:
            testes.append(("AST & Escopo de Imports", True, "Sintaxe válida e todos os símbolos/imports definidos"))

        if modo_wokwi and linguagem == "MicroPython":
            proibidas = [
                lib
                for lib in ("Adafruit_", "board", "digitalio", "analogio", "wokwi_gpio")
                if re.search(rf"\b{lib}", codigo_limpo)
            ]
            if proibidas:
                msg = f"Importação incompatível com MicroPython Wokwi: {', '.join(proibidas)}"
                testes.append(("Compatibilidade SDK MicroPython", False, msg))
                erros_detalhados.append(msg)
            else:
                testes.append(("Compatibilidade SDK MicroPython", True, "Apenas módulos nativos MicroPython utilizados"))

            res_sb = executar_sandbox_micropython(codigo_limpo, board_id=board_id)
            if not res_sb["ok"]:
                msg = f"Erro em tempo de execução no Sandbox MicroPython:\n{res_sb['traceback']}"
                testes.append(("Sandbox MicroPython (Execução + Falha Sensor)", False, res_sb["erro"]))
                erros_detalhados.append(msg)
            else:
                testes.append((
                    "Sandbox MicroPython (Execução + Falha Sensor)",
                    True,
                    f"Executou ciclos normais e sobreviveu a OSError sem travar (pinos: {', '.join(res_sb['pinos_usados']) or 'nenhum'})",
                ))

            diagram_dict = construir_diagram_dinamico(
                pedido_usuario, escopo, arquitetura, codigo_limpo, perfil
            )
            conns_str = json.dumps(diagram_dict.get("connections", []))
            pinos_faltando_diag = [
                p for p in res_sb["pinos_usados"] if f"{board_id}:{p}" not in conns_str
            ]
            if pinos_faltando_diag:
                msg = f"Pinos usados no main.py mas ausentes no diagram.json: {', '.join(pinos_faltando_diag)}"
                testes.append(("Consistência main.py ↔ diagram.json", False, msg))
                erros_detalhados.append(msg)
            else:
                testes.append((
                    "Consistência main.py ↔ diagram.json",
                    True,
                    "Todos os pinos instanciados no código estão conectados no diagram.json",
                ))

            if "json" in pedido_usuario.lower() and res_sb["ok"]:
                linhas_out = [l.strip() for l in res_sb["stdout"].splitlines() if l.strip()]
                jsons_validos = []
                for l in linhas_out:
                    if l.startswith("{") and l.endswith("}"):
                        try:
                            jsons_validos.append(json.loads(l))
                        except Exception:
                            pass
                if not jsons_validos:
                    msg = "O requisito exige telemetria JSON no console serial (print(json.dumps(...))), mas nenhuma linha JSON válida foi impressa."
                    testes.append(("Telemetria Serial JSON", False, msg))
                    erros_detalhados.append(msg)
                else:
                    chaves_pedidas = [k for k in ("temp", "hum", "led_color") if f'"{k}"' in pedido_usuario]
                    chaves_ausentes = [k for k in chaves_pedidas if k not in jsons_validos[0]]
                    if chaves_ausentes:
                        msg = f"JSON serial impresso não contém as chaves obrigatórias do requisito: {chaves_ausentes}. Recebido: {jsons_validos[0]}"
                        testes.append(("Telemetria Serial JSON", False, msg))
                        erros_detalhados.append(msg)
                    else:
                        testes.append((
                            "Telemetria Serial JSON",
                            True,
                            f"JSON serial válido verificado ({len(jsons_validos)} mensagens capturadas)",
                        ))
        else:
            res_sb = executar_sandbox_python_desktop(codigo_limpo)
            if not res_sb["ok"]:
                msg = f"Erro de execução Python:\n{res_sb['traceback']}"
                testes.append(("Sandbox Python (Execução Real)", False, res_sb["erro"]))
                erros_detalhados.append(msg)
            else:
                testes.append((
                    "Sandbox Python (Execução Real)",
                    True,
                    f"Código executou com returncode 0 (saída: {res_sb['stdout'][:80]})",
                ))
    else:
        tem_setup = "void setup" in codigo_limpo or "int main" in codigo_limpo
        chaves_ok = codigo_limpo.count("{") == codigo_limpo.count("}") and codigo_limpo.count("{") > 0
        if not tem_setup or not chaves_ok:
            msg = "Estrutura C/C++ incompleta (ausência de setup()/loop() ou chaves desbalanceadas)."
            testes.append(("Validação Estrutural C/C++", False, msg))
            erros_detalhados.append(msg)
        else:
            testes.append(("Validação Estrutural C/C++", True, "Funções principais e blocos C/C++ balanceados"))

    return {
        "aprovado": len(erros_detalhados) == 0,
        "codigo_limpo": codigo_limpo,
        "testes": testes,
        "erros": erros_detalhados,
    }


def formatar_relatorio_qa_markdown(res_qa: dict, tentativa: int) -> str:
    """Formata o resultado dos testes do Verificador QA em Markdown."""
    status_global = "✅ [APROVADO]" if res_qa["aprovado"] else f"❌ [REPROVADO — Tentativa {tentativa}/{MAX_TENTATIVAS_QA}]"
    linhas = [f"### 🧪 Relatório do Verificador QA & Sandbox — {status_global}\n"]
    for nome_teste, passou, detalhe in res_qa["testes"]:
        icone = "PASSOU" if passou else "FALHOU"
        marcador = "✓" if passou else "✗"
        linhas.append(f"- **[{icone}]** `{nome_teste}`: {marcador} {detalhe}")
    if res_qa["erros"]:
        linhas.append("\n**Erros capturados para correção automática:**")
        for err in res_qa["erros"]:
            linhas.append(f"```text\n{err}\n```")
    return "\n".join(linhas)


def executar_loop_qa_e_correcao(
    llm: ChatOllama,
    pedido_usuario: str,
    escopo: str,
    arquitetura: str,
    codigo_bruto: str,
) -> str:
    """
    Implementa o Loop Dinâmico de Verificação e Correção Automática (Stateless Feedback Loop):
    1. Executa o Verificador QA & Sandbox sobre o código gerado pelo Desenvolvedor.
    2. Se qualquer teste falhar (NameError, SyntaxError, TypeError de I2C, falha em OSError,
       JSON serial inválido ou pino desconectado), aciona o Agente Corretor enviando o código +
       o Traceback exato sem acumular histórico na VRAM.
    3. Repete até aprovar ou atingir MAX_TENTATIVAS_QA, aplicando sanitização determinística
       como garantia final.
    """
    perfil = detectar_perfil_projeto(pedido_usuario if pedido_usuario.strip() else escopo)
    board_nome = perfil["board_nome"]
    linguagem = perfil["linguagem"]
    arq_codigo = perfil["arq_codigo"]
    bloco_md = perfil["bloco_md"]

    codigo_atual = codigo_bruto
    historico_qa_md = []
    res_qa = {"aprovado": False}

    for tentativa in range(1, MAX_TENTATIVAS_QA + 1):
        res_qa = executar_verificacao_qa(
            codigo_atual, pedido_usuario, escopo, arquitetura, perfil
        )
        relatorio_md = formatar_relatorio_qa_markdown(res_qa, tentativa)
        historico_qa_md.append(relatorio_md)

        cor_painel = "green" if res_qa["aprovado"] else "red"
        titulo_painel = (
            f"[bold green]🧪 Verificador QA & Sandbox — Tentativa {tentativa}/{MAX_TENTATIVAS_QA}: APROVADO[/bold green]"
            if res_qa["aprovado"]
            else f"[bold red]🧪 Verificador QA & Sandbox — Tentativa {tentativa}/{MAX_TENTATIVAS_QA}: FALHA DETECTADA[/bold red]"
        )
        console.print()
        console.print(Panel(Markdown(relatorio_md), title=titulo_painel, border_style=cor_painel, box=box.ROUNDED))

        if res_qa["aprovado"]:
            break

        if tentativa < MAX_TENTATIVAS_QA:
            erros_texto = "\n\n".join(res_qa["erros"])
            codigo_atual = executar_agente(
                llm=llm,
                nome_agente=f"Agente Corretor QA — Tentativa {tentativa}/{MAX_TENTATIVAS_QA - 1} ({linguagem})",
                icone="🔄",
                cor="magenta",
                system_prompt=(
                    f"Você é um Engenheiro de QA e Firmware Sênior especialista em {board_nome} ({linguagem}). "
                    f"O código anterior falhou na execução real do Sandbox com os erros abaixo. "
                    f"Sua única função é corrigir TODOS os erros apontados no Traceback e devolver o código "
                    f"completo e funcional de `{arq_codigo}` dentro de um bloco ```{bloco_md} ... ```."
                ),
                user_prompt=(
                    f"Corrija o código abaixo que falhou nos testes automatizados do Sandbox.\n\n"
                    f"=== ERROS REAIS CAPTURADOS NO SANDBOX ===\n{erros_texto}\n\n"
                    f"=== CÓDIGO COM DEFEITO ===\n```{bloco_md}\n{res_qa['codigo_limpo']}\n```\n\n"
                    f"=== REQUISITOS ORIGINAIS ===\n{pedido_usuario}\n\n"
                    f"INSTRUÇÕES DE CORREÇÃO OBRIGATÓRIAS:\n"
                    f"1. Se o erro for `UnboundLocalError` (ex: 'temp' ou 'hum'): inicialize `temp = None` e `hum = None` ANTES do loop `while True:`, e defina `last_dht = time.ticks_ms() - 2000`.\n"
                    f"2. Declare TODOS os objetos de hardware (`dht_sensor`, `i2c`, `display`, `led_r`, `led_g`, `led_b`) no ESCOPO GLOBAL fora de funções.\n"
                    f"3. NUNCA passe tuplas para Pin (ex: `Pin((16,17,18))` é proibido); declare 3 pinos separados: `led_r = Pin(16, Pin.OUT)`, `led_g = Pin(17, Pin.OUT)`, `led_b = Pin(18, Pin.OUT)`.\n"
                    f"4. NUNCA reimplemente a classe `SSD1306_I2C`; use `from ssd1306 import SSD1306_I2C`.\n"
                    f"5. Se usar I2C no Raspberry Pi Pico, passe o ID do barramento 0: `I2C(0, scl=Pin(5), sda=Pin(4), freq=400000)`.\n"
                    f"6. Devolva o código COMPLETO corrigido dentro de ```{bloco_md} ... ```."
                ),
            )

    if perfil["modo_wokwi"] and linguagem == "MicroPython":
        cod_extraido = extrair_bloco_codigo(codigo_atual, arquitetura)
        cod_sanitizado = sanitizar_codigo_micropython(cod_extraido)
        if cod_sanitizado != cod_extraido or not res_qa["aprovado"]:
            codigo_atual = f"```{bloco_md}\n{cod_sanitizado}\n```"
            res_final = executar_verificacao_qa(
                codigo_atual, pedido_usuario, escopo, arquitetura, perfil
            )
            if not res_qa["aprovado"] and res_final["aprovado"]:
                rel_final = formatar_relatorio_qa_markdown(res_final, MAX_TENTATIVAS_QA)
                historico_qa_md.append(rel_final)
                console.print(
                    Panel(
                        Markdown(rel_final),
                        title="[bold green]🧪 Verificador QA & Sandbox — Pós-Sanitização AST: APROVADO[/bold green]",
                        border_style="green",
                        box=box.ROUNDED,
                    )
                )

    resumo_qa = "\n\n---\n\n".join(historico_qa_md)
    return f"{codigo_atual}\n\n---\n\n{resumo_qa}"


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

    # 1. Monta o diagrama determinístico com pinagem oficial do Wokwi para os componentes solicitados
    diagrama_dinamico = _montar_partes_dinamicas(texto_pedido, board_type, board_id)
    if len(diagrama_dinamico.get("parts", [])) > 1:
        return diagrama_dinamico

    # 2. Fallback: aproveita JSON gerado pelo LLM caso o pedido use apenas componentes não mapeados acima
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

    return diagrama_dinamico


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
        m_dht = (
            re.search(r"dht[^\n]*?\b(gp\d+)\b", texto_pedido)
            or re.search(r"dht[^\n]*?(?:sda|data|pino|pin)\s*(?:->|:|=)?\s*(gp\d+|d\d+|\b\d+\b)", texto_pedido)
            or re.search(r"\b(gp15)\b", texto_pedido)
        )
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

    # Ultrassônico HC-SR04 (somente se pedido)
    if "hc-sr04" in texto_pedido or "hcsr04" in texto_pedido or "ultrass" in texto_pedido:
        p_trig = "GP2" if board_id == "pico" else ("5" if board_id == "esp" else "7")
        p_echo = "GP3" if board_id == "pico" else ("18" if board_id == "esp" else "6")
        parts.append({"type": "wokwi-hc-sr04", "id": "ultrasonic1", "top": -140, "left": 20, "attrs": {}})
        connections.extend([
            ["ultrasonic1:VCC", vcc_pin, "red", []],
            ["ultrasonic1:GND", proximo_gnd(), "black", []],
            ["ultrasonic1:TRIG", f"{board_id}:{p_trig}", "yellow", []],
            ["ultrasonic1:ECHO", f"{board_id}:{p_echo}", "green", []],
        ])

    # Buzzer (somente se pedido)
    if "wokwi-buzzer" in texto_pedido or "buzzer" in texto_pedido:
        p_buz = "GP12" if board_id == "pico" else ("19" if board_id == "esp" else "8")
        parts.append({"type": "wokwi-buzzer", "id": "bz1", "top": 130, "left": 20, "attrs": {"volume": "0.1"}})
        connections.extend([
            ["bz1:1", proximo_gnd(), "black", []],
            ["bz1:2", f"{board_id}:{p_buz}", "red", []],
        ])

    # Sensor PIR (somente se pedido)
    if "wokwi-pir-motion-sensor" in texto_pedido or "sensor pir" in texto_pedido or re.search(r"\bpir\b", texto_pedido):
        p_pir = "GP11" if board_id == "pico" else ("23" if board_id == "esp" else "3")
        parts.append({"type": "wokwi-pir-motion-sensor", "id": "pir1", "top": -140, "left": -40, "attrs": {}})
        connections.extend([
            ["pir1:VCC", vcc_pin, "red", []],
            ["pir1:GND", proximo_gnd(), "black", []],
            ["pir1:OUT", f"{board_id}:{p_pir}", "yellow", []],
        ])

    # Relé (somente se pedido)
    if "wokwi-relay-module" in texto_pedido or "relé" in texto_pedido or "rele" in texto_pedido:
        p_rel = "GP10" if board_id == "pico" else ("16" if board_id == "esp" else "4")
        parts.append({"type": "wokwi-relay-module", "id": "relay1", "top": 140, "left": -40, "attrs": {}})
        connections.extend([
            ["relay1:VCC", vcc_pin, "red", []],
            ["relay1:GND", proximo_gnd(), "black", []],
            ["relay1:IN", f"{board_id}:{p_rel}", "green", []],
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
    perfil = detectar_perfil_projeto(pedido_usuario if pedido_usuario.strip() else escopo)
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
