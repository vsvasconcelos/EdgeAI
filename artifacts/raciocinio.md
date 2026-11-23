# Cadeia de Raciocínio Multi-Agente

Execução: 23/11/2026 16:34:31
Modelo: `qwen2.5-coder:3b` | Placa: `Raspberry Pi Pico (RP2040)` | Linguagem: `MicroPython`

---

## 🎯 1. Gerente de Projetos (Escopo & Requisitos)

### Documento de Escopo Técnico

#### Plataforma Alvo:
- Raspberry Pi Pico (RP2040)
- MicroPython SDK

#### Artefatos de Saída:
1. **Código-fonte completo em MicroPython** (`main.py` e `driver/ssd1306.py`):
   - Modularizado e comentado no padrão PEP-8.
   - Não-bloqueante, usando temporizadores não-bloqueantes com `time.ticks_ms()` e `time.ticks_diff()`.
   - Sem dependências externas não nativas.

2. **Arquivo diagram.json válido para o Wokwi Pi Pico**:
   - Contendo todas as conexões de hardware mapeadas, pronto para execução imediata sem sobreposição de componentes.

3. **Mapa de Hardware e Pinagem Obrigatória (Pinout RP2040)**:
   - Listando todos os componentes e pinos solicitados no pedido.

#### Componentes Solicitados:
- Sensor DHT22 (wokwi-dht22)
  - Função: Leitura de Temperatura (°C) e Umidade (%).
  - Interface: Digital (1-Wire).
  - Pinos Obrigatórios:
    - VCC -> 3V3
    - GND -> GND.1
    - SDA -> GP15

- Display OLED SSD1306 (board-ssd1306)
  - Função: Exibição do cabeçalho e leituras locais.
  - Interface: I2C0 (addr 0x3c).
  - Pinos Obrigatórios:
    - VCC -> 3V3
    - GND -> GND.2
    - SDA -> GP4
    - SCL -> GP5

- LED RGB Cátodo Comum (wokwi-rgb-led)
  - Função: Sinalização visual por faixas de temperatura e umidade.
  - Interface: Digital Out.
  - Pinos Obrigatórios:
    - COM -> GND.3 (atributo "common": "cathode")
    - R -> GP16
    - G -> GP17
    - B -> GP18

#### Requisitos Funcionais (RF):
1. **RF01 – Aquisição de Dados do DHT22**:
   - Ler o sensor DHT22 conectado ao GP15 a cada 2.000 ms.

2. **RF02 – Interface Gráfica no Display OLED I2C (GP4/GP5)**:
   - Atualizar o display OLED SSD1306 a cada 1.000 ms sem causar cintilação excessiva.
   - Layout de tela:
     * Linha 1: "MBA-FIAP" centralizado ou alinhado no topo (y=0), divisória horizontal (y=12).
     * Linha 2: "Temp: XX.X C".
     * Linha 3: "Umid: XX.X %".

3. **RF03 – Sinalização Visual via LED RGB (GP16, GP17, GP18)**:
   - Acionar os canais R, G e B em lógica ativa alta conforme a combinação de Temperatura e Umidade.

4. **RF04 – Telemetria via Console Serial (USB/UART)**:
   - Imprimir no console serial uma linha JSON compacta contendo o estado atual.

#### Requisitos Não Funcionais (RNF):
1. **RNF01 – Arquitetura Não-Bloqueante**:
   - Proibido o uso de `time.sleep()` longo no loop principal.
   - Escalonamento controlado por temporizadores não-bloqueantes.

2. **RNF02 – Tratamento de Falha de Sensor**:
   - Exibir "ERRO SENSOR" nas linhas inferiores do OLED e acender LED RGB na cor Magenta se a leitura falhar.
   - Registrar `temp": null, "hum": null` no console serial.

3. **RNF03 – Fidelidade do diagram.json**:
   - Usar obrigatoriamente os tipos especificados para componentes e pinos.

#### Restrições de Plataforma:
- Linguagem: MicroPython nativo para Raspberry Pi Pico (RP2040).
- Sempre incluir imports usados: `import machine`, `from machine import Pin, I2C`, `import time`, `import json`.
- Se houver DHT22/DHT11: instanciar obrigatoriamente no escopo global com prefixo do módulo `dht.DHT22(Pin(15))` e ler com `.measure()`, `.temperature()` e `.humidity()`.
- Se houver OLED SSD1306: usar `from ssd1306 import SSD1306_I2C` e inicializar o I2C informando o ID do barramento 0.
- Instanciar TODOS os periféricos no escopo global (fora de qualquer função).
- Para LED RGB: use 3 pinos separados (`led_r = Pin(16, Pin.OUT)`, `led_g = Pin(17, Pin.OUT)`, `led_b = Pin(18, Pin.OUT)`).
- NUNCA passe tupla para Pin().
- Inicialize todas as variáveis de telemetria antes do loop while True para evitar UnboundLocalError.
- Use contadores não-bloqueantes com offset (`last_dht = time.ticks_ms() - 2000`, `last_oled = time.ticks_ms() - 1000`) com `time.ticks_diff()` e `time.sleep_ms(50)` no fim do loop.
- Proibir importar `Adafruit_*`, `board`, `digitalio` ou `wokwi_gpio`.

#### Placa Alvo (`wokwi-pi-pico`) e Mapa de Hardware:
1. **Placa alvo**:
   - Raspberry Pi Pico (RP2040)

2. **Mapa de Hardware**:
   ```
   Componente (Wokwi ID) | Função no Sistema | Interface | Pinos Obrigatórios no Pi Pico e Atributos
   ---------------------|-------------------|----------|-----------------------------------------
   wokwi-dht22          | DHT22 Sensor      | Digital  | VCC -> 3V3, GND -> GND.1, SDA -> GP15
   board-ssd1306        | OLED SSD1306     | I2C0    | VCC -> 3V3, GND -> GND.2, SDA -> GP4, SCL -> GP5
   wokwi-rgb-led         | RGB LED Cátodo Comum | Digital Out| COM -> GND.3 (attrs: {"common": "cathode"}), R -> GP16, G -> GP17, B -> GP18
   ```

#### Requisitos Funcionais Detalhados:
- **RF01 – Aquisição de Dados do DHT22**:
  - Ler o sensor DHT22 a cada 2.000 ms.

- **RF02 – Interface Gráfica no Display OLED I2C (GP4/GP5)**:
  - Atualizar o display OLED SSD1306 a cada 1.000 ms.
  - Layout de tela:
    * Linha 1: "MBA-FIAP" centralizado ou alinhado no topo (y=0), divisória horizontal (y=12).
    * Linha 2: "Temp: XX.X C".
    * Linha 3: "Umid: XX.X %".

- **RF03 – Sinalização Visual via LED RGB (GP16, GP17, GP18)**:
  - Acionar os canais R, G e B em lógica ativa alta conforme a combinação de Temperatura e Umidade.

- **RF04 – Telemetria via Console Serial (USB/UART)**:
  - Imprimir no console serial uma linha JSON compacta contendo o estado atual.

#### Requisitos Não Funcionais Detalhados:
1. **RNF01 – Arquitetura Não-Bloqueante**:
   - Escalonamento controlado por temporizadores não-bloqueantes (`last_dht = time.ticks_ms() - 2000`, `last_oled = time.ticks_ms() - 1000`) com `time.ticks_diff()` e `time.sleep_ms(50)` no fim do loop.

2. **RNF02 – Tratamento de Falha de Sensor**:
   - Exibir "ERRO SENSOR" nas linhas inferiores do OLED e acender LED RGB na cor Magenta se a leitura falhar.
   - Registrar `temp": null, "hum": null` no console serial.

3. **RNF03 – Fidelidade do diagram.json**:
   - Usar obrigatoriamente os tipos especificados para componentes e pinos.

#### Arquivo diagram.json (Exemplo):
```json
{
  "components": [
    {
      "id": "wokwi-dht22",
      "type": "sensor",
      "pins": ["GND.1", "SDA"]
    },
    {
      "id": "board-ssd1306",
      "type": "display",
      "pins": ["VCC", "GND.2", "SDA", "SCL"]
    },
    {
      "id": "wokwi-rgb-led",
      "type": "led",
      "pins": ["COM", "R", "G", "B"],
      "attributes": {"common": "cathode"}
    }
  ]
}
```

#### Código-fonte completo (`main.py`):
```python
import machine
from ssd1306 import SSD1306_I2C
import dht

# Configurando os pinos dos componentes
led_r = Pin(16, Pin.OUT)
led_g = Pin(17, Pin.OUT)
led_b = Pin(18, Pin.OUT)

scl = Pin(5)
sda = Pin(4)
i2c = I2C(0, scl=scl, sda=sda, freq=400000)

dht_sensor = dht.DHT22(Pin(15))

# Inicializando o display OLED
display = SSD1306_I2C(128, 64, i2c)

# Variáveis de telemetria
temp = None
hum = None
cor_atual = 'OFF'

# Contadores não-bloqueantes
last_dht = time.ticks_ms() - 2000
last_oled = time.ticks_ms() - 1000

while True:
    # Verificando a leitura do sensor DHT22
    if time.ticks_diff(time.ticks_ms(), last_dht) >= 2000:
        dht_sensor.measure()
        temp = dht_sensor.temperature()
        hum = dht_sensor.humidity()

        # Atualizando o display OLED
        display.fill(0)

---

## 🏗️ 2. Arquiteto de Sistemas (Design Técnico)

1. Imports obrigatórios:
   ```python
   import machine
   from ssd1306 import SSD1306_I2C
   import dht
   ```

2. Inicialização dos periféricos e pinos:
   ```python
   led_r = Pin(16, Pin.OUT)
   led_g = Pin(17, Pin.OUT)
   led_b = Pin(18, Pin.OUT)

   scl = Pin(5)
   sda = Pin(4)
   i2c = I2C(0, scl=scl, sda=sda, freq=400000)

   dht_sensor = dht.DHT22(Pin(15))

   display = SSD1306_I2C(128, 64, i2c)
   ```

3. Estrutura de estado do loop principal:
   ```python
   while True:
       # Verificando a leitura do sensor DHT22
       if time.ticks_diff(time.ticks_ms(), last_dht) >= 2000:
           dht_sensor.measure()
           temp = dht_sensor.temperature()
           hum = dht_sensor.humidity()

           # Atualizando o display OLED
           display.fill(0)
   ```

4. Assinaturas das funções:
   ```python
   def update_display():
       display.fill(0)
       display.text("MBA-FIAP", 16, 0, 1)
       display.line(0, 12, 128, 12, 1)
       display.text(f"Temp: {temp:.1f} C", 16, 14, 1)
       display.text(f"Hum: {hum:.1f} %", 16, 30, 1)

   def update_led():
       if temp is not None and hum is not None:
           cor_atual = 'OFF'
           if temp > 25:
               cor_atual = 'RED'
           elif temp < 18:
               cor_atual = 'BLUE'
           elif hum > 60:
               cor_atual = 'GREEN'

           led_r.value(1 if cor_atual == 'RED' else 0)
           led_g.value(1 if cor_atual == 'GREEN' else 0)
           led_b.value(1 if cor_atual == 'BLUE' else 0)

   def handle_sensor_failure():
       display.fill(0)
       display.text("ERRO SENSOR", 16, 0, 1)
       display.line(0, 12, 128, 12, 1)
       led_r.value(1)
       led_g.value(1)
       led_b.value(1)

   def main():
       last_dht = time.ticks_ms() - 2000
       last_oled = time.ticks_ms() - 1000

       while True:
           if time.ticks_diff(time.ticks_ms(), last_dht) >= 2000:
               dht_sensor.measure()
               temp = dht_sensor.temperature()
               hum = dht_sensor.humidity()

               if temp is None or hum is None:
                   handle_sensor_failure()
               else:
                   update_display()
                   update_led()

           time.sleep_ms(50)
   ```

5. Estrutura de estado do loop principal com `time.ticks_diff()` e `time.sleep_ms()`: 
   ```python
   while True:
       if time.ticks_diff(time.ticks_ms(), last_dht) >= 2000:
           dht_sensor.measure()
           temp = dht_sensor.temperature()
           hum = dht_sensor.humidity()

           if temp is None or hum is None:
               handle_sensor_failure()
           else:
               update_display()
               update_led()

       time.sleep_ms(50)
   ```

---

## 💻 3. Desenvolvedor (MicroPython)

```python
import machine
from machine import Pin, I2C
import ssd1306
import time

# Definição dos pinos GPIO
led_r = Pin(16, Pin.OUT)
led_g = Pin(17, Pin.OUT)
led_b = Pin(18, Pin.OUT)

# Configuração do sensor DHT22
dht_sensor = machine.DHT(machine.Pin(15), 0x18)  # Sensor DHT22 com endereço 0x18

# Configuração do display OLED SSD1306
i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=400000)
display = ssd1306.SSD1306_I2C(128, 64, i2c)

# Variáveis para armazenar os valores de temperatura e umidade
temp = None
hum = None

def update_display():
    display.fill(0)
    display.text("MBA-FIAP", 16, 0, 1)
    display.line(0, 12, 128, 12, 1)
    if temp is not None and hum is not None:
        display.text(f"Temp: {temp:.1f} C", 16, 14, 1)
        display.text(f"Hum: {hum:.1f} %", 16, 30, 1)

def update_led():
    if temp is not None and hum is not None:
        cor_atual = 'OFF'
        if temp > 25:
            cor_atual = 'RED'
        elif temp < 18:
            cor_atual = 'BLUE'
        elif hum > 60:
            cor_atual = 'GREEN'

        led_r.value(1 if cor_atual == 'RED' else 0)
        led_g.value(1 if cor_atual == 'GREEN' else 0)
        led_b.value(1 if cor_atual == 'BLUE' else 0)

def handle_sensor_failure():
    display.fill(0)
    display.text("ERRO SENSOR", 16, 0, 1)
    display.line(0, 12, 128, 12, 1)
    led_r.value(1)
    led_g.value(1)
    led_b.value(1)

def main():
    last_dht = time.ticks_ms() - 2000
    last_oled = time.ticks_ms() - 1000

    temp = None
    hum = None
    while True:
        if time.ticks_diff(time.ticks_ms(), last_dht) >= 2000:
            try:
                dht_sensor.measure()
                temp = dht_sensor.temperature()
                hum = dht_sensor.humidity()

                if temp is None or hum is None:
                    handle_sensor_failure()
                else:
                    update_display()
                    update_led()

            except OSError as e:
                print(f"Erro no sensor: {e}")
                handle_sensor_failure()

        time.sleep_ms(50)

# Código para o diagram.json
diagram_json = {
    "components": [
        {"id": "wokwi-pi-pico", "type": "wokwi-pi-pico"},
        {"id": "wokwi-dht22", "type": "wokwi-dht22", "attrs": {"pin": 15}},
        {"id": "board-ssd1306", "type": "board-ssd1306", "attrs": {"i2c_id": 0, "width": 128, "height": 64}},
        {"id": "wokwi-rgb-led", "type": "wokwi-rgb-led", "attrs": {"common": "cathode"}}
    ],
    "connections": [
        {"from": "wokwi-pi-pico:15", "to": "wokwi-dht22"},
        {"from": "wokwi-pi-pico:3V3", "to": "board-ssd1306:vcc"},
        {"from": "wokwi-pi-pico:gnd", "to": "board-ssd1306:gnd"}
    ]
}

# Retornar o código corrigido dentro de
```

---

### 🧪 Relatório do Verificador QA & Sandbox — ❌ [REPROVADO — Tentativa 1/3]

- **[FALHOU]** `AST & Sintaxe`: ✗ SyntaxError na linha 8: unindent does not match any outer indentation level
- **[PASSOU]** `Compatibilidade SDK MicroPython`: ✓ Apenas módulos nativos MicroPython utilizados
- **[FALHOU]** `Sandbox MicroPython (Execução + Falha Sensor)`: ✗ IndentationError: unindent does not match any outer indentation level (main.py, line 8)
- **[PASSOU]** `Consistência main.py ↔ diagram.json`: ✓ Todos os pinos instanciados no código estão conectados no diagram.json

**Erros capturados para correção automática:**
```text
SyntaxError na linha 8: unindent does not match any outer indentation level
```
```text
Erro em tempo de execução no Sandbox MicroPython:
File "main.py", line 8
IndentationError: unindent does not match any outer indentation level
```

---

### 🧪 Relatório do Verificador QA & Sandbox — ❌ [REPROVADO — Tentativa 2/3]

- **[FALHOU]** `AST & Escopo de Imports`: ✗ NameError potencial — Símbolos usados sem import/definição: 'machine' (linha 11)
- **[FALHOU]** `Compatibilidade SDK MicroPython`: ✗ Importação incompatível com MicroPython Wokwi: board
- **[FALHOU]** `Sandbox MicroPython (Execução + Falha Sensor)`: ✗ NameError: name 'machine' is not defined
- **[PASSOU]** `Consistência main.py ↔ diagram.json`: ✓ Todos os pinos instanciados no código estão conectados no diagram.json

**Erros capturados para correção automática:**
```text
NameError potencial — Símbolos usados sem import/definição: 'machine' (linha 11)
```
```text
Importação incompatível com MicroPython Wokwi: board
```
```text
Erro em tempo de execução no Sandbox MicroPython:
File "main.py", line 11, in <module>
NameError: name 'machine' is not defined
```

---

### 🧪 Relatório do Verificador QA & Sandbox — ❌ [REPROVADO — Tentativa 3/3]

- **[FALHOU]** `AST & Escopo de Imports`: ✗ NameError potencial — Símbolos usados sem import/definição: 'machine' (linha 11)
- **[FALHOU]** `Compatibilidade SDK MicroPython`: ✗ Importação incompatível com MicroPython Wokwi: board
- **[FALHOU]** `Sandbox MicroPython (Execução + Falha Sensor)`: ✗ NameError: name 'machine' is not defined
- **[PASSOU]** `Consistência main.py ↔ diagram.json`: ✓ Todos os pinos instanciados no código estão conectados no diagram.json

**Erros capturados para correção automática:**
```text
NameError potencial — Símbolos usados sem import/definição: 'machine' (linha 11)
```
```text
Importação incompatível com MicroPython Wokwi: board
```
```text
Erro em tempo de execução no Sandbox MicroPython:
File "main.py", line 11, in <module>
NameError: name 'machine' is not defined
```
