# Cadeia de Raciocínio Multi-Agente

Execução: 23/11/2026 15:45:38
Modelo: `qwen2.5-coder:3b` | Placa: `ESP32` | Linguagem: `MicroPython`

---

## 🎯 1. Gerente de Projetos (Escopo & Requisitos)

### Documento de Escopo: Monitor Ambiental Simplificado (Raspberry Pi Pico)

#### Plataforma Alvo:
- Raspberry Pi Pico (RP2040)
- Linguagem / SDK: MicroPython

#### Artefatos de Saída:

1. **Código-fonte completo, modularizado e comentado no padrão PEP-8**:
   - `main.py`: Contém a lógica principal do agente.
   - `driver/ssd1306.py`: Módulo que implementa a classe `SSD1306_I2C` para o display OLED SSD1306.

2. **Arquivo diagram.json válido**:
   - Contém todas as conexões de hardware mapeadas conforme especificado no pedido, pronto para execução imediata no simulador Wokwi (wokwi-pi-pico).

#### Mapa de Hardware e Pinagem Obrigatória:

| Componente (Wokwi ID) | Função no Sistema | Interface | Pinos Obrigatórios no Pi Pico e Atributos |
|-----------------------|------------------|----------|----------------------------------------|
| wokwi-dht22          | Leitura de Temperatura (°C) e Umidade (%) | Digital (1-Wire) | VCC -> 3V3, GND -> GND.1, SDA -> GP15 |
| board-ssd1306       | Exibição do cabeçalho e leituras locais | I2C0 (addr 0x3c) | VCC -> 3V3, GND -> GND.2, SDA -> GP4, SCL -> GP5 |
| wokwi-rgb-led       | Sinalização visual por faixas de temperatura e umidade | Digital Out | COM -> GND.3 (atributo "common": "cathode"), R -> GP16 (via resistor 220 ohms), G -> GP17 (via resistor 220 ohms), B -> GP18 (via resistor 220 ohms) |

#### Requisitos Funcionais (RF):

1. **RF01 – Aquisição de Dados do DHT22**:
   - Ler o sensor DHT22 conectado ao GP15 a cada 2.000 ms.

2. **RF02 – Interface Gráfica no Display OLED I2C (GP4/GP5)**:
   - Atualizar o display OLED SSD1306 a cada 1.000 ms.
   - Layout de tela:
     * Linha 1: "MBA-FIAP" centralizado ou alinhado no topo, divisória horizontal em y=12.
     * Linha 2: "Temp: XX.X C".
     * Linha 3: "Umid: XX.X %".

3. **RF03 – Sinalização Visual via LED RGB (GP16, GP17, GP18)**:
   - Acionar os canais R, G e B em lógica ativa alta conforme a combinação de Temperatura (T) e Umidade (U).

4. **RF04 – Telemetria via Console Serial (USB/UART)**:
   - Imprimir no console serial uma linha JSON compacta a cada 2.000 ms.

#### Requisitos Não Funcionais (RNF):

1. **RNF01 – Arquitetura Não-Bloqueante**:
   - Proibido o uso de `time.sleep()` longo no loop principal.
   - Escalonamento controlado por temporizadores não-bloqueantes utilizando `time.ticks_ms()`, `time.ticks_diff()` e `time.sleep_ms(50)`.

2. **RNF02 – Tratamento de Falha de Sensor**:
   - Exibir "ERRO SENSOR" nas linhas inferiores do OLED.
   - Acender o LED RGB na cor Magenta (R=1, G=0, B=1).
   - Registrar `{"temp": null, "hum": null}` no console serial.

3. **RNF03 – Fidelidade do diagram.json**:
   - Usar obrigatoriamente os tipos "wokwi-pi-pico", "wokwi-dht22", "board-ssd1306", "wokwi-rgb-led" (com "attrs": {"common": "cathode"}) e três "wokwi-resistor".
   - Todos os pinos de alimentação (3V3 e GND) devem estar explicitamente conectados.

#### Restrições de Plataforma:
- Linguagem: MicroPython nativo para RP2040/ESP32.
- Proibido importar `Adafruit_*`, `board`, `digitalio` ou `wokwi_gpio`.

### Entregáveis:

1. **Placa alvo (`wokwi-pi-pico`) e Mapa de Hardware**:
   - Contém somente os componentes solicitados no pedido.

2. **Requisitos Funcionais detalhados**:
   - Intervalos de leitura: DHT22 (2000 ms), Display OLED (1000 ms).
   - Lógica de acionamento do LED RGB conforme as condições de temperatura e umidade.
   - Interface/display: Layout especificado no pedido.
   - Telemetria serial: JSON compacto com estado atual.

3. **Requisitos Não Funcionais e Tratamento de Falhas**:
   - Arquitetura não-bloqueante utilizando temporizadores não-bloqueantes.
   - Tratamento de falha do sensor (exibir erro, acender LED RGB, registrar no console serial).

4. **Restrições de Plataforma**:
   - Linguagem: MicroPython nativo para RP2040/ESP32.
   - Proibido importar bibliotecas específicas.

### Código-fonte completo (main.py):

```python
import machine
from machine import Pin, I2C
import time
import json

# Configuração do sensor DHT22
dht_sensor = dht.DHT22(Pin(15))

# Configuração do display OLED SSD1306
i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=400000)
display = SSD1306_I2C(128, 64, i2c)

# Configuração do LED RGB Cátodo Comum
led_r = Pin(16, Pin.OUT)
led_g = Pin(17, Pin.OUT)
led_b = Pin(18, Pin.OUT)

def display_header():
    display.fill(0)  # Limpa o display
    display.text("MBA-FIAP", 24, 0, font=font_6x8)
    display.hline(0, 12, 128, 1)  # Linha horizontal divisória

def update_display(temp, hum):
    display.fill(0)  # Limpa o display
    display.text("MBA-FIAP", 24, 0, font=font_6x8)
    display.hline(0, 12, 128, 1)  # Linha horizontal divisória
    display.text(f"Temp: {temp:.1f} C", 24, 24, font=font_6x8)
    display.text(f"Umid: {hum:.1f} %", 24, 42, font=font_6x8)

def set_led_color(color):
    led_r.value(0 if color & 0b001 else 1)
    led_g.value(0 if color & 0b010 else 1)
    led_b.value(0 if color & 0b100 else 1)

def main():
    while True:
        try:
            dht_sensor.measure()
            temp = dht_sensor.temperature()
            hum = dht_sensor.humidity()

            # Atualiza o display
            update_display(temp, hum)

            # Define a cor do LED RGB com base nas condições de temperatura e umidade
            color = 0
            if temp > 30.0:
                color |= 0b001  # Vermelho
            elif temp < 18.0:
                color |= 0b010  # Verde
            elif hum > 60.0:
                color |= 0b100  # Azul

            set_led_color(color)

        except OSError as e:
            display.fill(0)  # Limpa o display
            display.text("ERRO SENSOR", 24, 0, font=font_6x8)
            led_r.value(1)
            led_g.value(1)
            led_b.value(1)

        time.sleep_ms(50)

if __name__ == "__main__":
    main()
```

### Módulo `driver/ssd1306.py`:

```python
from ssd1306 import SSD1306_I2C

class SSD1306_I2C(SSD1306_I2C):
    def __init__(self, width, height, i2c, addr=0x3c):
        super().__init__(width, height, i2c, addr)
```

### Diagrama de Hardware (diagram.json):

```json
{
  "components": [
    {
      "id": "wokwi-dht22",
      "type": "dht22",
      "pin": 15,
      "vcc": 3.3,
      "gnd": 0
    },
    {
      "id": "board-ssd1306",
      "type": "ssd1306_i2c",
      "i2c": 0,
      "scl": 5,
      "sda": 4,
      "addr": 0x3c
    },
    {
      "id": "wokwi-rgb-led",
      "type": "led_rgb_cathode",
      "pin_r": 16,
      "pin_g": 17,
      "pin_b": 18,
      "common": "cathode"
    }
  ],
  "connections": [
    {
      "from": "wokwi-dht22.vcc",
      "to": "board-ssd1306.i2c.scl"
    },
    {
      "from": "wokwi-dht22.gnd",
      "to": "board-ssd1306.i2c.sda"
    },
    {
      "from": "wokwi-dht22.vcc",
      "to": "wokwi-rgb-led.pin_r"
    },
    {
      "from": "wokwi-dht22.gnd",
      "to": "wokwi-rgb-led.pin_g"
    },
    {
      "from": "wokwi-dht22.gnd",
      "to": "wokwi-rgb-led.pin_b"
    }
  ]
}
```

### Fontes:
- `font_6x8`: Fonte para exibição de texto no display OLED.

Este documento fornece uma descrição detalhada do projeto, incluindo os artefatos de sa

---

## 🏗️ 2. Arquiteto de Sistemas (Design Técnico)

1. Imports obrigatórios:
   ```python
   import machine
   from machine import Pin, I2C
   import time
   import json
   from dht import DHT22
   from ssd1306 import SSD1306_I2C
   ```

2. Assinaturas das funções:
   ```python
   def display_header():
       pass

   def update_display(temp, hum):
       pass

   def set_led_color(color):
       pass

   def main():
       while True:
           try:
               dht_sensor.measure()
               temp = dht_sensor.temperature()
               hum = dht_sensor.humidity()

               # Atualiza o display
               update_display(temp, hum)

               # Define a cor do LED RGB com base nas condições de temperatura e umidade
               color = 0
               if temp > 30.0:
                   color |= 0b001  # Vermelho
               elif temp < 18.0:
                   color |= 0b010  # Verde
               elif hum > 60.0:
                   color |= 0b100  # Azul

               set_led_color(color)

           except OSError as e:
               display.fill(0)  # Limpa o display
               display.text("ERRO SENSOR", 24, 0, font=font_6x8)
               led_r.value(1)
               led_g.value(1)
               led_b.value(1)

           time.sleep_ms(50)
   ```

3. Estrutura de estado do loop principal:
   ```python
   while True:
       try:
           dht_sensor.measure()
           temp = dht_sensor.temperature()
           hum = dht_sensor.humidity()

           # Atualiza o display
           update_display(temp, hum)

           # Define a cor do LED RGB com base nas condições de temperatura e umidade
           color = 0
           if temp > 30.0:
               color |= 0b001  # Vermelho
           elif temp < 18.0:
               color |= 0b010  # Verde
           elif hum > 60.0:
               color |= 0b100  # Azul

           set_led_color(color)

       except OSError as e:
           display.fill(0)  # Limpa o display
           display.text("ERRO SENSOR", 24, 0, font=font_6x8)
           led_r.value(1)
           led_g.value(1)
           led_b.value(1)

       time.sleep_ms(50)
   ```

---

## 💻 3. Desenvolvedor (MicroPython)

```python
import machine
from machine import Pin, I2C
import time
import json
from dht import DHT22
from ssd1306 import SSD1306_I2C

# Configuração dos pinos e componentes
led_r = Pin(16, Pin.OUT)
led_g = Pin(17, Pin.OUT)
led_b = Pin(18, Pin.OUT)

i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=400000)
display = SSD1306_I2C(128, 64, i2c)

dht_sensor = DHT22(Pin(15))

# Funções auxiliares
def display_header():
    display.fill(0)  # Limpa o display
    display.text("MBA-FIAP", 24, 0, font=font_6x8)
    display.hline(0, 12, 128, 1)

def update_display(temp, hum):
    display.fill(0)  # Limpa o display
    display.text("Temp: {:.1f} C".format(temp), 24, 24, font=font_6x8)
    display.text("Umid: {:.1f} %".format(hum), 24, 42, font=font_6x8)

def set_led_color(color):
    led_r.value((color & 0b001) > 0)
    led_g.value((color & 0b010) > 0)
    led_b.value((color & 0b100) > 0)

# Loop principal
last_dht = time.ticks_ms()
last_oled = time.ticks_ms()

while True:
    try:
        if time.ticks_diff(time.ticks_ms(), last_dht) >= 2000:
            dht_sensor.measure()
            temp = dht_sensor.temperature()
            hum = dht_sensor.humidity()
            last_dht = time.ticks_ms()

        if time.ticks_diff(time.ticks_ms(), last_oled) >= 1000:
            display_header()
            update_display(temp, hum)
            set_led_color(0b010)  # Verde por padrão
            last_oled = time.ticks_ms()

    except OSError as e:
        display.fill(0)  # Limpa o display
        display.text("ERRO SENSOR", 24, 0, font=font_6x8)
        led_r.value(1)
        led_g.value(1)
        led_b.value(1)

    time.sleep_ms(50)
```

---

### 🧪 Relatório do Verificador QA & Sandbox — ❌ [REPROVADO — Tentativa 1/3]

- **[FALHOU]** `AST & Escopo de Imports`: ✗ NameError potencial — Símbolos usados sem import/definição: 'font_6x8' (linha 21)
- **[PASSOU]** `Compatibilidade SDK MicroPython`: ✓ Apenas módulos nativos MicroPython utilizados
- **[FALHOU]** `Sandbox MicroPython (Execução + Falha Sensor)`: ✗ NameError: name 'font_6x8' is not defined
- **[FALHOU]** `Consistência main.py ↔ diagram.json`: ✗ Pinos usados no main.py mas ausentes no diagram.json: 15, 16, 17, 18, 4, 5

**Erros capturados para correção automática:**
```text
NameError potencial — Símbolos usados sem import/definição: 'font_6x8' (linha 21)
```
```text
Erro em tempo de execução no Sandbox MicroPython:
File "main.py", line 47, in <module>
  File "main.py", line 21, in display_header
NameError: name 'font_6x8' is not defined
```
```text
Pinos usados no main.py mas ausentes no diagram.json: 15, 16, 17, 18, 4, 5
```

---

### 🧪 Relatório do Verificador QA & Sandbox — ❌ [REPROVADO — Tentativa 2/3]

- **[FALHOU]** `AST & Escopo de Imports`: ✗ NameError potencial — Símbolos usados sem import/definição: 'font_6x8' (linha 21)
- **[PASSOU]** `Compatibilidade SDK MicroPython`: ✓ Apenas módulos nativos MicroPython utilizados
- **[FALHOU]** `Sandbox MicroPython (Execução + Falha Sensor)`: ✗ NameError: name 'font_6x8' is not defined
- **[FALHOU]** `Consistência main.py ↔ diagram.json`: ✗ Pinos usados no main.py mas ausentes no diagram.json: 15, 16, 17, 18, 4, 5

**Erros capturados para correção automática:**
```text
NameError potencial — Símbolos usados sem import/definição: 'font_6x8' (linha 21)
```
```text
Erro em tempo de execução no Sandbox MicroPython:
File "main.py", line 47, in <module>
  File "main.py", line 21, in display_header
NameError: name 'font_6x8' is not defined
```
```text
Pinos usados no main.py mas ausentes no diagram.json: 15, 16, 17, 18, 4, 5
```

---

### 🧪 Relatório do Verificador QA & Sandbox — ❌ [REPROVADO — Tentativa 3/3]

- **[FALHOU]** `AST & Escopo de Imports`: ✗ NameError potencial — Símbolos usados sem import/definição: 'font_6x8' (linha 21)
- **[PASSOU]** `Compatibilidade SDK MicroPython`: ✓ Apenas módulos nativos MicroPython utilizados
- **[FALHOU]** `Sandbox MicroPython (Execução + Falha Sensor)`: ✗ NameError: name 'font_6x8' is not defined
- **[FALHOU]** `Consistência main.py ↔ diagram.json`: ✗ Pinos usados no main.py mas ausentes no diagram.json: 15, 16, 17, 18, 4, 5

**Erros capturados para correção automática:**
```text
NameError potencial — Símbolos usados sem import/definição: 'font_6x8' (linha 21)
```
```text
Erro em tempo de execução no Sandbox MicroPython:
File "main.py", line 47, in <module>
  File "main.py", line 21, in display_header
NameError: name 'font_6x8' is not defined
```
```text
Pinos usados no main.py mas ausentes no diagram.json: 15, 16, 17, 18, 4, 5
```
