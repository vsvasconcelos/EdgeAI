# Cadeia de Raciocínio Multi-Agente

Execução: 23/11/2026 16:19:26
Modelo: `qwen2.5-coder:3b` | Placa: `Raspberry Pi Pico (RP2040)` | Linguagem: `MicroPython`

---

## 🎯 1. Gerente de Projetos (Escopo & Requisitos)

### Documento de Escopo: Monitor Ambiental Simplificado (Raspberry Pi Pico)

#### Plataforma Alvo:
- Raspberry Pi Pico (RP2040)
- Linguagem / SDK: MicroPython

#### Artefatos de Saída:

1. **Código-fonte completo, modularizado e comentado no padrão PEP-8**:
   - `main.py`: Implementação principal do agente.
   - `driver/ssd1306.py`: Módulo separado para a classe SSD1306_I2C.

2. **Arquivo diagram.json válido para o Wokwi Pi Pico**:
   - Contém todas as conexões de hardware mapeadas conforme especificado no pedido, pronto para execução imediata sem sobreposição de componentes.

3. **Mapa de Hardware e Pinagem Obrigatória (Pinout RP2040)**:
   - Lista dos componentes e pinos solicitados no pedido.

#### Componentes Solicitados:

- **Sensor DHT22 (wokwi-dht22)**:
  - Função: Leitura de Temperatura (°C) e Umidade (%).
  - Interface: Digital (1-Wire).
  - Pinos Obrigatórios:
    - VCC -> 3V3
    - GND -> GND.1
    - SDA -> GP15

- **Display OLED SSD1306 (board-ssd1306)**:
  - Função: Exibição do cabeçalho e leituras locais.
  - Interface: I2C0 (addr 0x3c).
  - Pinos Obrigatórios:
    - VCC -> 3V3
    - GND -> GND.2
    - SDA -> GP4
    - SCL -> GP5

- **LED RGB Cátodo Comum (wokwi-rgb-led)**:
  - Função: Sinalização visual por faixas de temperatura e umidade.
  - Interface: Digital Out.
  - Pinos Obrigatórios:
    - COM -> GND.3 (atributo "common": "cathode")
    - R -> GP16
    - G -> GP17
    - B -> GP18

#### Requisitos Funcionais (RF):

- **RF01 – Aquisição de Dados do DHT22**:
  - Ler o sensor DHT22 conectado ao GP15 a cada 2.000 ms.

- **RF02 – Interface Gráfica no Display OLED I2C (GP4/GP5)**:
  - Atualizar o display OLED SSD1306 a cada 1.000 ms.
  - Layout de tela:
    * Linha 1: "MBA-FIAP" centralizado ou alinhado no topo, divisória horizontal.
    * Linha 2: "Temp: XX.X C".
    * Linha 3: "Umid: XX.X %".

- **RF03 – Sinalização Visual via LED RGB (GP16, GP17, GP18)**:
  - Acionar os canais R, G e B em lógica ativa alta conforme a combinação de Temperatura e Umidade.
  - Prioridades:
    1. Alerta Crítico / Desconforto Severo (Vermelho).
    2. Ambiente Frio / Úmido (Azul).
    3. Faixa de Conforto Ideal (Verde).
    4. Faixa de Atenção Moderada (Amarelo).

- **RF04 – Telemetria via Console Serial (USB/UART)**:
  - Imprimir no console serial a cada 2.000 ms, uma linha JSON contendo o estado atual.

#### Requisitos Não Funcionais (RNF):

- **RNF01 – Arquitetura Não-Bloqueante**:
  - Proibido usar `time.sleep()` longo no loop principal.
  - Escalonamento controlado por temporizadores não-bloqueantes com `time.ticks_ms()`, `time.ticks_diff()`.

- **RNF02 – Tratamento de Falha de Sensor**:
  - Exibir "ERRO SENSOR" nas linhas inferiores do OLED.
  - Acender LED RGB na cor Magenta (R=1, G=0, B=1).
  - Registrar `{"temp": null, "hum": null}` no console serial.

- **RNF03 – Fidelidade do diagram.json**:
  - Usar obrigatoriamente os tipos "wokwi-pi-pico", "wokwi-dht22", "board-ssd1306", "wokwi-rgb-led" (com "attrs": {"common": "cathode"}) e três "wokwi-resistor".
  - Pinos de alimentação (3V3 e GND) explicitamente conectados.

#### Restrições de Plataforma:
- Linguagem: MicroPython nativo para Raspberry Pi Pico (RP2040).
- Proibir uso de `Adafruit_*`, `board`, `digitalio` ou `wokwi_gpio`.

---

**Placa alvo (`wokwi-pi-pico`) e Mapa de Hardware**:
- Componentes: Sensor DHT22, Display OLED SSD1306, LED RGB Cátodo Comum.
- Pinos: GP15 (DHT22), GP4 (SDA), GP5 (SCL) para OLED, GND.1, GND.2, GND.3 para alimentação e comum do LED RGB.

**Requisitos Funcionais detalhados**:
- Intervalo de leitura DHT22: 2000 ms.
- Intervalo de atualização display OLED: 1000 ms.
- Layout de tela no display OLED:
  * Linha 1: "MBA-FIAP" centralizado, divisória horizontal.
  * Linha 2: "Temp: XX.X C".
  * Linha 3: "Umid: XX.X %".

**Requisitos Não Funcionais e Tratamento de Falhas**:
- Arquitetura não-bloqueante usando `time.ticks_ms()` e `time.sleep_ms(50)`.
- Exibir "ERRO SENSOR" nas linhas inferiores do OLED.
- Acender LED RGB na cor Magenta (R=1, G=0, B=1).
- Registrar `{"temp": null, "hum": null}` no console serial.

---

**Imports necessários**:
```python
import machine
from machine import Pin, I2C
import time
import json

# Importar DHT22 se necessário
# from dht import DHT22
```

Este documento de escopo detalha todas as especificações e requisitos solicitados para o projeto utilizando a plataforma Wokwi com o Raspberry Pi Pico (RP2040) e MicroPython, garantindo que todos os componentes e pinos solicitados estejam explicitamente mencionados.

---

## 🏗️ 2. Arquiteto de Sistemas (Design Técnico)

1. Imports obrigatórios:
```python
import machine
from machine import Pin, I2C
import time
import json

# Importar DHT22 se necessário
# from dht import DHT22
```

2. Assinaturas das funções:
```python
def read_dht():
    # Função para ler o sensor DHT22 e retornar temperatura e umidade
    pass

def update_display(temp, hum):
    # Função para atualizar o display OLED com a temperatura e umidade
    pass

def set_led_color(temp, hum):
    # Função para definir a cor do LED RGB com base na temperatura e umidade
    pass

def main():
    dht_sensor = dht.DHT22(Pin(15))
    i2c_display = I2C(0, scl=Pin(5), sda=Pin(4), freq=400000)
    led_rgb = Pin((16, 17, 18), Pin.OUT)

    while True:
        temp, hum = read_dht()
        
        if temp is not None and hum is not None:
            update_display(temp, hum)
            set_led_color(temp, hum)
        else:
            print("ERRO SENSOR")
            led_rgb.value(7)  # Magenta (R=1, G=0, B=1)

        json_state = {"temp": temp, "hum": hum}
        print(json.dumps(json_state))

        time.sleep_ms(2000)
```

3. Estrutura de estado do loop principal:
```python
while True:
    temp, hum = read_dht()
    
    if temp is not None and hum is not None:
        update_display(temp, hum)
        set_led_color(temp, hum)
    else:
        print("ERRO SENSOR")
        led_rgb.value(7)  # Magenta (R=1, G=0, B=1)

    json_state = {"temp": temp, "hum": hum}
    print(json.dumps(json_state))

    time.sleep_ms(2000)
```

---

## 💻 3. Desenvolvedor (MicroPython)

```python
import machine
from machine import Pin, I2C
import time
import json

# Importar DHT22 se necessário
from dht import DHT22

class SSD1306_I2C:
    def __init__(self, width, height, i2c):
        self.width = width
        self.height = height
        self.i2c = i2c
        self.buffer = bytearray(width * height // 8)

    def fill(self, color):
        if color == 0:
            self.buffer.fill(0)
        else:
            self.buffer.fill(255)

    def text(self, string, x, y, font_size=1):
        # Implementação simplificada de texto para SSD1306
        pass

    def hline(self, x, y, length, color):
        if color == 0:
            for i in range(length):
                self.buffer[x + i] = 0
        else:
            for i in range(length):
                self.buffer[x + i] = 255

    def show(self):
        # Implementação simplificada de exibição para SSD1306
        pass

def read_dht():
    try:
        dht_sensor.measure()
        temp = dht_sensor.temperature()
        hum = dht_sensor.humidity()
        return temp, hum
    except OSError as e:
        print("ERRO SENSOR")
        return None, None

def update_display(temp, hum):
    i2c_display = I2C(0, scl=Pin(5), sda=Pin(4), freq=400000)
    oled = SSD1306_I2C(128, 64, i2c_display)
    
    oled.fill(0)
    oled.text("MBA-FIAP", 0, 0, 1)
    oled.hline(0, 12, 128, 1)
    if temp is not None and hum is not None:
        oled.text(f"Temp: {temp:.1f} C", 0, 24, 1)
        oled.text(f"Umid: {hum:.1f} %", 0, 42, 1)
    else:
        oled.text("ERRO SENSOR", 0, 24, 1)
    
    oled.show()

def set_led_color(temp, hum):
    led_rgb = Pin((16, 17, 18), Pin.OUT)
    
    if temp is not None and hum is not None:
        if temp > 30.0 or hum < 30.0:
            led_rgb.value(7)  # Magenta (R=1, G=0, B=1)
        elif temp < 18.0 or hum > 75.0:
            led_rgb.value(2)  # Blue (R=0, G=0, B=1)
        elif 18.0 <= temp <= 26.0 and 40.0 <= hum <= 70.0:
            led_rgb.value(3)  # Green (R=0, G=1, B=0)
        else:
            led_rgb.value(4)  # Yellow (R=1, G=1, B=0)
    else:
        led_rgb.value(0)  # Off

def main():
    dht_sensor = DHT22(Pin(15))
    i2c_display = I2C(0, scl=Pin(5), sda=Pin(4), freq=400000)
    led_rgb = Pin((16, 17, 18), Pin.OUT)

    last_dht = time.ticks_ms()
    last_oled = time.ticks_ms()

    while True:
        if time.ticks_diff(time.ticks_ms(), last_dht) >= 2000:
            temp, hum = read_dht()
            last_dht = time.ticks_ms()
        
        if time.ticks_diff(time.ticks_ms(), last_oled) >= 1000:
            update_display(temp, hum)
            set_led_color(temp, hum)
            last_oled = time.ticks_ms()

        json_state = {"temp": temp, "hum": hum}
        print(json.dumps(json_state))

        time.sleep_ms(50)

if __name__ == "__main__":
    main()
```

---

### 🧪 Relatório do Verificador QA & Sandbox — ❌ [REPROVADO — Tentativa 1/3]

- **[PASSOU]** `AST & Escopo de Imports`: ✓ Sintaxe válida e todos os símbolos/imports definidos
- **[PASSOU]** `Compatibilidade SDK MicroPython`: ✓ Apenas módulos nativos MicroPython utilizados
- **[FALHOU]** `Sandbox MicroPython (Execução + Falha Sensor)`: ✗ UnboundLocalError: cannot access local variable 'temp' where it is not associated with a value
- **[PASSOU]** `Consistência main.py ↔ diagram.json`: ✓ Todos os pinos instanciados no código estão conectados no diagram.json

**Erros capturados para correção automática:**
```text
Erro em tempo de execução no Sandbox MicroPython:
File "main.py", line 69, in <module>
  File "main.py", line 59, in main
UnboundLocalError: cannot access local variable 'temp' where it is not associated with a value
```

---

### 🧪 Relatório do Verificador QA & Sandbox — ❌ [REPROVADO — Tentativa 2/3]

- **[PASSOU]** `AST & Escopo de Imports`: ✓ Sintaxe válida e todos os símbolos/imports definidos
- **[PASSOU]** `Compatibilidade SDK MicroPython`: ✓ Apenas módulos nativos MicroPython utilizados
- **[FALHOU]** `Sandbox MicroPython (Execução + Falha Sensor)`: ✗ UnboundLocalError: cannot access local variable 'temp' where it is not associated with a value
- **[PASSOU]** `Consistência main.py ↔ diagram.json`: ✓ Todos os pinos instanciados no código estão conectados no diagram.json

**Erros capturados para correção automática:**
```text
Erro em tempo de execução no Sandbox MicroPython:
File "main.py", line 75, in <module>
  File "main.py", line 65, in main
UnboundLocalError: cannot access local variable 'temp' where it is not associated with a value
```

---

### 🧪 Relatório do Verificador QA & Sandbox — ❌ [REPROVADO — Tentativa 3/3]

- **[PASSOU]** `AST & Escopo de Imports`: ✓ Sintaxe válida e todos os símbolos/imports definidos
- **[PASSOU]** `Compatibilidade SDK MicroPython`: ✓ Apenas módulos nativos MicroPython utilizados
- **[FALHOU]** `Sandbox MicroPython (Execução + Falha Sensor)`: ✗ UnboundLocalError: cannot access local variable 'temp' where it is not associated with a value
- **[PASSOU]** `Consistência main.py ↔ diagram.json`: ✓ Todos os pinos instanciados no código estão conectados no diagram.json

**Erros capturados para correção automática:**
```text
Erro em tempo de execução no Sandbox MicroPython:
File "main.py", line 102, in <module>
  File "main.py", line 92, in main
UnboundLocalError: cannot access local variable 'temp' where it is not associated with a value
```
