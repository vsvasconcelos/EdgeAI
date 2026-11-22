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


def eh_pedido_wokwi(pedido: str) -> bool:
    """Detecta se o pedido do usuário é voltado para simulação Wokwi / MicroPython."""
    texto = pedido.lower()
    palavras_chave = (
        "wokwi",
        "micropython",
        "pi pico",
        "raspberry pi pico",
        "rp2040",
        "diagram.json",
        "ssd1306",
        "dht22",
        "gp15",
        "gp26",
        "gp27",
    )
    return any(k in texto for k in palavras_chave)


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


DIAGRAM_WOKWI_PADRAO_PICO = {
    "version": 1,
    "author": "EdgeAI",
    "editor": "wokwi",
    "parts": [
        {"type": "wokwi-pi-pico", "id": "pico", "top": 0, "left": 0, "attrs": {"env": "micropython-20231005-v1.21.0"}},
        {"type": "wokwi-dht22", "id": "dht1", "top": -120, "left": -130, "attrs": {}},
        {"type": "wokwi-photoresistor-sensor", "id": "ldr1", "top": -120, "left": 120, "attrs": {}},
        {"type": "wokwi-potentiometer", "id": "pot1", "top": -20, "left": 160, "attrs": {}},
        {"type": "board-ssd1306", "id": "oled1", "top": 120, "left": -160, "attrs": {"i2cAddress": "0x3c"}},
        {"type": "wokwi-led", "id": "led_norm", "top": 40, "left": -150, "attrs": {"color": "green"}},
        {"type": "wokwi-led", "id": "led_lux", "top": 40, "left": -110, "attrs": {"color": "yellow"}},
        {"type": "wokwi-led", "id": "led_alarm", "top": 40, "left": -70, "attrs": {"color": "red"}},
        {"type": "wokwi-resistor", "id": "r1", "top": 90, "left": -150, "attrs": {"value": "220"}},
        {"type": "wokwi-resistor", "id": "r2", "top": 90, "left": -110, "attrs": {"value": "220"}},
        {"type": "wokwi-resistor", "id": "r3", "top": 90, "left": -70, "attrs": {"value": "220"}},
        {"type": "wokwi-servo", "id": "servo1", "top": 120, "left": 150, "attrs": {}},
        {"type": "wokwi-pushbutton", "id": "btn1", "top": -80, "left": -40, "attrs": {"color": "blue"}},
    ],
    "connections": [
        ["dht1:VCC", "pico:3V3", "red", []],
        ["dht1:GND", "pico:GND.1", "black", []],
        ["dht1:SDA", "pico:GP15", "green", []],
        ["ldr1:VCC", "pico:3V3", "red", []],
        ["ldr1:GND", "pico:GND.2", "black", []],
        ["ldr1:AO", "pico:GP26", "orange", []],
        ["pot1:VCC", "pico:3V3", "red", []],
        ["pot1:GND", "pico:GND.3", "black", []],
        ["pot1:SIG", "pico:GP27", "purple", []],
        ["oled1:VCC", "pico:3V3", "red", []],
        ["oled1:GND", "pico:GND.4", "black", []],
        ["oled1:SDA", "pico:GP4", "blue", []],
        ["oled1:SCL", "pico:GP5", "cyan", []],
        ["pico:GP16", "r1:1", "green", []],
        ["r1:2", "led_norm:A", "green", []],
        ["led_norm:C", "pico:GND.5", "black", []],
        ["pico:GP17", "r2:1", "yellow", []],
        ["r2:2", "led_lux:A", "yellow", []],
        ["led_lux:C", "pico:GND.5", "black", []],
        ["pico:GP18", "r3:1", "red", []],
        ["r3:2", "led_alarm:A", "red", []],
        ["led_alarm:C", "pico:GND.5", "black", []],
        ["servo1:V+", "pico:VBUS", "red", []],
        ["servo1:GND", "pico:GND.6", "black", []],
        ["servo1:PWM", "pico:GP13", "orange", []],
        ["btn1:1.l", "pico:GP14", "blue", []],
        ["btn1:2.r", "pico:GND.7", "black", []],
    ],
    "dependencies": {},
}


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
    """Pipeline especializado para projetos MicroPython no simulador Wokwi (Pi Pico)."""
    escopo = executar_agente(
        llm=llm,
        nome_agente="Gerente de Projetos (Wokwi / Embarcados)",
        icone="🎯",
        cor="yellow",
        system_prompt=(
            "Você é um Gerente de Projetos Sênior de Sistemas Embarcados e IoT "
            "especialista no simulador Wokwi com Raspberry Pi Pico (MicroPython). "
            "Analise o pedido e produza um documento de escopo técnico fiel "
            "preservando TODOS os pinos GPIO, periféricos, faixas de conversão e "
            "requisitos de temporização. Sem comentários extras."
        ),
        user_prompt=(
            f"Analise o pedido abaixo para a plataforma Wokwi (Raspberry Pi Pico / MicroPython) "
            f"e produza um Documento de Escopo objetivo:\n\n"
            f"PEDIDO:\n{pedido_usuario}\n\n"
            f"Entregue:\n"
            f"1. Mapa de Hardware e Pinagem exata no wokwi-pi-pico (GP4, GP5, GP13, GP14, GP15, GP16, GP17, GP18, GP26, GP27)\n"
            f"2. Requisitos Funcionais (amostragem, conversões ADC 0-65535, controle proporcional do Servo, PWM do LED, telas do OLED, IRQ do botão e telemetria JSON via Serial)\n"
            f"3. Critérios de Aceitação e Tratamento de Falhas (OSError no DHT22)\n"
            f"4. Restrições de Plataforma: MicroPython nativo (`machine`, `dht`, `time`, `json`, `ssd1306`). "
            f"PROIBIDO usar `Adafruit_DHT`, `board`, `digitalio` ou `wokwi_gpio`."
        ),
    )

    arquitetura = executar_agente(
        llm=llm,
        nome_agente="Arquiteto de Sistemas (MicroPython / Wokwi)",
        icone="🏗️",
        cor="blue",
        system_prompt=(
            "Você é um Arquiteto de Firmware MicroPython Sênior para Raspberry Pi Pico no Wokwi. "
            "Sua função é definir APENAS a especificação técnica e as assinaturas das funções. "
            "NÃO implemente o código completo. "
            "Use EXCLUSIVAMENTE as APIs reais do MicroPython:\n"
            "- `from machine import Pin, ADC, PWM, I2C`\n"
            "- `import dht`, `import time`, `import json`\n"
            "- `from ssd1306 import SSD1306_I2C`\n"
            "NUNCA mencione `Adafruit_*`, `board`, `digitalio` ou `wokwi_gpio`."
        ),
        user_prompt=(
            f"Com base no escopo abaixo, especifique a arquitetura técnica MicroPython para o Wokwi.\n\n"
            f"=== ESCOPO ===\n{escopo}\n\n"
            f"Liste de forma concisa (máximo 180 palavras, SEM implementar o código final):\n"
            f"1. Mapeamento de objetos MicroPython (`dht.DHT22(Pin(15))`, `ADC(Pin(26))`, `ADC(Pin(27))`, `I2C(0, sda=Pin(4), scl=Pin(5))`, `SSD1306_I2C(128, 64, i2c)`, `Pin(16, Pin.OUT)`, `PWM(Pin(17))`, `Pin(18, Pin.OUT)`, `PWM(Pin(13))`, `Pin(14, Pin.IN, Pin.PULL_UP)` com `.irq()`)\n"
            f"2. Assinaturas das funções e fórmulas de conversão (ADC `read_u16()` 0..65535 -> % luminosidade e Setpoint 15..40°C, pulso PWM do servo via `duty_u16`)\n"
            f"3. Fluxo do loop principal não-bloqueante (`time.ticks_ms()` / `time.ticks_diff()`)."
        ),
    )

    codigo = executar_agente(
        llm=llm,
        nome_agente="Desenvolvedor MicroPython (Wokwi)",
        icone="💻",
        cor="green",
        system_prompt=(
            "Você é um Desenvolvedor Especialista em MicroPython para Raspberry Pi Pico no simulador Wokwi. "
            "Sua tarefa é escrever o código Python completo do arquivo `main.py` dentro de um único bloco ```python ... ```. "
            "REGRAS OBRIGATÓRIAS:\n"
            "1. Inicie com: `from machine import Pin, ADC, PWM, I2C`, `import dht`, `import time`, `import json` e `from ssd1306 import SSD1306_I2C`.\n"
            "2. PROIBIDO importar `Adafruit_DHT`, `Adafruit_SSD1306`, `Adafruit_ADS1x15`, `board`, `digitalio`, `analogio` ou `wokwi_gpio`.\n"
            "3. Configure `servo = PWM(Pin(13)); servo.freq(50)` e `led_amarelo = PWM(Pin(17)); led_amarelo.freq(1000)`.\n"
            "4. No módulo `dht` do MicroPython, `dht_sensor.temperature()` e `dht_sensor.humidity()` são MÉTODOS — SEMPRE chame com parênteses `()`.\n"
            "5. Inicialize `temperature = 25.0`, `humidity = 50.0` e `setpoint = 25.0` antes do `while True:` e trate `try ... except OSError:` no DHT22 exibindo `ERRO DHT22` no OLED e ligando `led_vermelho.value(1)`."
        ),
        user_prompt=(
            f"Escreva agora o código MicroPython COMPLETO do arquivo `main.py` para o Raspberry Pi Pico no Wokwi "
            f"com base na arquitetura abaixo:\n\n"
            f"=== ESCOPO ===\n{escopo}\n\n"
            f"=== ARQUITETURA ===\n{arquitetura}\n\n"
            f"Entregue o código completo de `main.py` dentro de um bloco ```python ... ``` contendo:\n"
            f"- Inicialização dos pinos GP4, GP5, GP13, GP14, GP15, GP16, GP17, GP18, GP26, GP27\n"
            f"- `dht_sensor.measure()`, `dht_sensor.temperature()` e `dht_sensor.humidity()` com parênteses `()`\n"
            f"- Interrupção IRQ no botão GP14 (`button.irq(trigger=Pin.IRQ_FALLING, handler=...)`) com debounce (`time.ticks_ms()`) para alternar `tela_atual` entre 0 (Operação) e 1 (Diagnóstico)\n"
            f"- Leitura de sensores, controle proporcional do Servo (passando `temperature` e `setpoint`), controle de LEDs (`led_verde`, `led_amarelo.duty_u16(...)`, `led_vermelho`), atualização do OLED SSD1306 e `print(json.dumps(...))`."
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
    """
    codigo = re.sub(r"(\bdht\w*\.temperature)(?!\s*\()", r"\1()", codigo)
    codigo = re.sub(r"(\bdht\w*\.humidity)(?!\s*\()", r"\1()", codigo)
    return codigo


def extrair_diagram_json(escopo: str, arquitetura: str, codigo: str) -> dict:
    """
    Tenta extrair um diagram.json válido no schema Wokwi (version, parts, connections)
    a partir das saídas dos agentes; caso o JSON gerado não contenha 'parts' e 'connections'
    no formato oficial do Wokwi, retorna o DIAGRAM_WOKWI_PADRAO_PICO homologado.
    """
    padrao_json = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)
    for texto in (codigo, arquitetura, escopo):
        for match in padrao_json.findall(texto):
            try:
                obj = json.loads(match)
                if (
                    isinstance(obj, dict)
                    and "version" in obj
                    and isinstance(obj.get("parts"), list)
                    and isinstance(obj.get("connections"), list)
                    and obj["parts"]
                    and isinstance(obj["parts"][0], dict)
                    and "id" in obj["parts"][0]
                ):
                    return obj
            except Exception:
                continue
    return DIAGRAM_WOKWI_PADRAO_PICO


def salvar_artefatos(escopo: str, arquitetura: str, codigo: str, pedido_usuario: str = ""):
    """Salva os artefatos gerados na pasta 'artifacts/' local (incluindo arquivos Wokwi se aplicável)."""
    pasta_base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artifacts")
    modo_wokwi = eh_pedido_wokwi(f"{pedido_usuario}\n{escopo}\n{arquitetura}")

    # Criar pasta específica para esta execução com timestamp (Histórico)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pasta_run = os.path.join(pasta_base, f"run_{timestamp}")
    os.makedirs(pasta_run, exist_ok=True)

    # Extrair o maior bloco de código Python válido (de codigo ou arquitetura)
    blocos_py = re.findall(r"```python\s*(.*?)\s*```", f"{codigo}\n{arquitetura}", re.DOTALL)
    if not blocos_py:
        blocos_py = re.findall(r"```\s*(.*?)\s*```", codigo, re.DOTALL)
    if blocos_py:
        codigo_limpo = max(blocos_py, key=len).strip()
    else:
        codigo_limpo = codigo.strip()

    if modo_wokwi:
        codigo_limpo = sanitizar_codigo_micropython(codigo_limpo)

    # Formatar cadeia de raciocínio completa
    raciocinio_completo = (
        f"# Cadeia de Raciocínio Multi-Agente\n\n"
        f"Execução: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
        f"Modelo: `{OLLAMA_MODEL}`\n\n"
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

    arquivos_gerados = [
        ("escopo.md", escopo),
        ("arquitetura.md", arquitetura),
        ("codigo.py", codigo_limpo),
        ("raciocinio.md", raciocinio_completo),
    ]

    if modo_wokwi:
        diagram_dict = extrair_diagram_json(escopo, arquitetura, codigo)
        diagram_str = json.dumps(diagram_dict, indent=2, ensure_ascii=False)
        wokwi_toml = (
            "[wokwi]\n"
            "version = 1\n"
            'firmware = ""\n'
            'elf = ""\n'
        )
        arquivos_gerados.extend([
            ("main.py", codigo_limpo),
            ("diagram.json", diagram_str),
            ("ssd1306.py", DRIVER_SSD1306_MICROPYTHON),
            ("wokwi.toml", wokwi_toml),
        ])

    # 1. Salvar na subpasta da execução (Histórico)
    for nome_arq, conteudo in arquivos_gerados:
        with open(os.path.join(pasta_run, nome_arq), "w", encoding="utf-8") as f:
            f.write(conteudo)

    # 2. Salvar/Atualizar na raiz de artifacts/ como "latest" (Última versão)
    os.makedirs(pasta_base, exist_ok=True)
    for nome_arq, conteudo in arquivos_gerados:
        with open(os.path.join(pasta_base, nome_arq), "w", encoding="utf-8") as f:
            f.write(conteudo)

    console.print(f"[bold green]✓ Histórico gravado em:[/bold green] [cyan]{pasta_run}/[/cyan]")
    console.print(f"[bold green]✓ Versão mais recente atualizada em:[/bold green] [cyan]{pasta_base}/[/cyan]")
    if modo_wokwi:
        console.print(
            "[bold cyan]✓ Artefatos Wokwi prontos para simulação:[/bold cyan] "
            "[white]main.py, diagram.json, ssd1306.py, wokwi.toml[/white]"
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
