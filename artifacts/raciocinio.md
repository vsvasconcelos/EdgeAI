# Cadeia de Raciocínio Multi-Agente

Execução: 22/11/2026 18:29:35
Modelo: `qwen2.5-coder:3b` | Placa: `Raspberry Pi Pico (RP2040)` | Linguagem: `MicroPython`

---

## 🎯 1. Gerente de Projetos (Escopo & Requisitos)

### Documento de Escopo Técnico

#### Plataforma Alvo:
- Raspberry Pi Pico (RP2040)
- MicroPython

#### Artefatos de Saída:

1. **Código-fonte completo em MicroPython** (`main.py` e `driver/ssd1306.py`):
   - Modularizado e comentado no padrão PEP-8.
   - Não-bloqueante, usando temporizadores não-bloqueantes com `time.ticks_ms()` e `time.ticks_diff()`.
   - Sem dependências externas não nativas.

2. **Arquivo diagram.json válido para o Wokwi Pi Pico**:
   - Contendo todas as conexões de hardware mapeadas, pronto para execução imediata sem sobreposição de componentes.
   - Fidelidade ao diagram.json: Usando obrigatoriamente os tipos "wokwi-pi-pico", "wokwi-dht22", "board-ssd1306", "wokwi-rgb-led" (com "attrs": {"common": "cathode"}) e três "wokwi-resistor" ("value": "220").
   - Pinos de alimentação (3V3 e GND) explicitamente conectados.

#### Mapa de Hardware e Pinagem Obrigatória:

| Componente (Wokwi ID) | Função no Sistema | Interface | Pinos Obrigatórios no Pi Pico e Atributos |
|-----------------------|-------------------|----------|----------------------------------------|
| wokwi-dht22          | Leitura de Temperatura (°C) e Umidade (%) | Digital (1-Wire) | VCC -> 3V3, GND -> GND.1, SDA -> GP15 |
| board-ssd1306        | Exibição do cabeçalho e leituras locais | I2C0 (addr 0x3c) | VCC -> 3V3, GND -> GND.2, SDA -> GP4, SCL -> GP5 |
| wokwi-rgb-led        | Sinalização visual por faixas de temperatura e umidade | Digital Out | COM -> GND.3 (atributo "common": "cathode"), R -> GP16 (via resistor 220 ohms), G -> GP17 (via resistor 220 ohms), B -> GP18 (via resistor 220 ohms) |

#### Requisitos Funcionais:

1. **RF01 – Aquisição de Dados do DHT22**:
   - Ler o sensor DHT22 conectado ao GP15 a cada 2.000 ms.

2. **RF02 – Interface Gráfica no Display OLED I2C (GP4/GP5)**:
   - Atualizar o display OLED SSD1306 (128x64 pixels, endereço I2C 0x3c) a cada 1.000 ms.
   - Layout de tela:
     * Linha 1: "MBA-FIAP" centralizado ou alinhado no topo (y=0), linha horizontal divisória (y=12).
     * Linha 2: "Temp: XX.X C" (y=24).
     * Linha 3: "Umid: XX.X %" (y=42).

3. **RF03 – Sinalização Visual via LED RGB (GP16, GP17, GP18)**:
   - Acionar os canais R, G e B em lógica ativa alta conforme a combinação de Temperatura (T) e Umidade (U), obedecendo à seguinte ordem de prioridade:
     1. Alerta Crítico / Desconforto Severo: Cor Vermelha -> R=1, G=0, B=0.
     2. Ambiente Frio / Úmido: Cor Azul -> R=0, G=0, B=1.
     3. Faixa de Conforto Ideal: Cor Verde -> R=0, G=1, B=0.
     4. Faixa de Atenção Moderada: Cor Amarela -> R=1, G=1, B=0.

4. **RF04 – Telemetria via Console Serial (USB/UART)**:
   - Imprimir no console serial do Wokwi a cada 2.000 ms, uma linha JSON compacta contendo o estado atual: `{"temp": XX.X, "hum": XX.X, "led_color": "COLOR"}`.

#### Requisitos Não Funcionais:

1. **RNF01 – Arquitetura Não-Bloqueante**:
   - Proibido o uso de `time.sleep()` longo no loop principal.
   - Escalonamento da leitura do DHT22 (2.000 ms) e atualização do display OLED (1.000 ms) controlado por temporizadores não-bloqueantes utilizando `time.ticks_ms()` e `time.ticks_diff()`.

2. **RNF02 – Tratamento de Falha de Sensor**:
   - Caso a leitura do DHT22 lance exceção (`OSError`), o sistema deve exibir "ERRO SENSOR" nas linhas inferiores do OLED (mantendo o cabeçalho "MBA-FIAP"), acender o LED RGB na cor Magenta (R=1, G=0, B=1) e registrar `{"temp": null, "hum": null}` no console serial.

3. **RNF03 – Fidelidade do diagram.json**:
   - O arquivo diagram.json gerado pelo agente deve usar obrigatoriamente os tipos "wokwi-pi-pico", "wokwi-dht22", "board-ssd1306", "wokwi-rgb-led" (com "attrs": {"common": "cathode"}) e três "wokwi-resistor" ("value": "220").
   - Pinos de alimentação (3V3 e GND) explicitamente conectados.

#### Restrições de Plataforma:
- Linguagem: MicroPython nativo (`from machine import ...`, `import time`, `import json`).
- Se houver DHT22/DHT11 use `import dht` com `.measure()`, `.temperature()` e `.humidity()`.
- Se houver OLED SSD1306 use `from ssd1306 import SSD1306_I2C`.
- Use temporização não-bloqueante com `time.ticks_ms()` e `time.ticks_diff()`.
- Proibido importar `Adafruit_*`, `board`, `digitalio` ou `wokwi_gpio`.

---

## 🏗️ 2. Arquiteto de Sistemas (Design Técnico)

### Inicialização dos Periféricos

1. **Inicialização do DHT22**:
   - Importar `dht` e criar um objeto `DHT22` conectado ao GPIO 15.
   ```python
   from dht import DHT22
   dht_sensor = DHT22(machine.Pin(15))
   ```

2. **Inicialização do Display OLED SSD1306**:
   - Importar `SSD1306_I2C` e criar um objeto `SSD1306_I2C` com endereço 0x3c, usando GPIOs 4 e 5.
   ```python
   from ssd1306 import SSD1306_I2C
   display = SSD1306_I2C(128, 64, machine.I2C(scl=machine.Pin(5), sda=machine.Pin(4)))
   ```

3. **Inicialização do LED RGB**:
   - Importar `machine` e criar objetos `Pin` para os canais R, G e B com atributo "common": "cathode".
   ```python
   from machine import Pin
   led_r = Pin(16, Pin.OUT)
   led_g = Pin(17, Pin.OUT)
   led_b = Pin(18, Pin.OUT)
   ```

### Assinaturas das Funções

1. **Função para Ler DHT22**:
   - Retorna um dicionário com as temperaturas e umidades.
   ```python
   def read_dht():
       try:
           dht_sensor.measure()
           temp = dht_sensor.temperature()
           hum = dht_sensor.humidity()
           return {"temp": temp, "hum": hum}
       except OSError:
           return {"temp": None, "hum": None}
   ```

2. **Função para Atualizar Display OLED**:
   - Recebe um dicionário com as temperaturas e umidades e atualiza o display.
   ```python
   def update_display(data):
       display.fill(0)
       display.text("MBA-FIAP", 16, 0, 1)
       display.line(0, 12, 128, 12, 1)
       if data["temp"] is not None and data["hum"] is not None:
           display.text(f"Temp: {data['temp']:.1f} C", 16, 24, 1)
           display.text(f"Hum: {data['hum']:.1f}%", 16, 42, 1)
       else:
           display.text("ERRO SENSOR", 16, 24, 1)
           display.text("ERRO SENSOR", 16, 42, 1)
       display.show()
   ```

3. **Função para Sinalização Visual via LED RGB**:
   - Recebe um dicionário com as temperaturas e umidades e aciona os canais R, G e B.
   ```python
   def set_led_color(data):
       if data["temp"] is not None and data["hum"] is not None:
           temp = data["temp"]
           hum = data["hum"]
           if temp < 15 or hum > 60:
               led_r.value(1)
               led_g.value(0)
               led_b.value(0)
           elif temp >= 20 and temp <= 30 and hum >= 40 and hum <= 70:
               led_r.value(0)
               led_g.value(1)
               led_b.value(0)
           else:
               led_r.value(1)
               led_g.value(1)
               led_b.value(0)
       else:
           led_r.value(1)
           led_g.value(0)
           led_b.value(1)
   ```

4. **Função para Telemetria via Console Serial**:
   - Imprime um dicionário JSON no console serial.
   ```python
   def send_telemetry(data):
       print(json.dumps(data))
   ```

### Estrutura do Loop Principal

```python
import time

while True:
    current_time = time.ticks_ms()
    
    # RF01 – Aquisição de Dados do DHT22
    dht_data = read_dht()
    
    # RF02 – Interface Gráfica no Display OLED I2C (GP4/GP5)
    update_display(dht_data)
    
    # RF03 – Sinalização Visual via LED RGB (GP16, GP17, GP18)
    set_led_color(dht_data)
    
    # RF04 – Telemetria via Console Serial (USB/UART)
    send_telemetry(dht_data)
    
    # RNF01 – Arquitetura Não-Bloqueante
    next_time = current_time + 2000
    while time.ticks_diff(next_time, time.ticks_ms()) > 0:
        pass
```

### Diagram.json

```json
{
  "components": [
    {
      "id": "wokwi-pi-pico",
      "type": "wokwi-pi-pico"
    },
    {
      "id": "wokwi-dht22",
      "type": "wokwi-dht22",
      "attrs": {
        "pin": 15
      }
    },
    {
      "id": "board-ssd1306",
      "type": "board-ssd1306",
      "attrs": {
        "i2c_addr": 0x3c,
        "sda_pin": 4,
        "scl_pin": 5
      }
    },
    {
      "id": "wokwi-rgb-led",
      "type": "wokwi-rgb-led",
      "attrs": {
        "common": "cathode"
      }
    },
    {
      "id": "wokwi-resistor_1",
      "type": "wokwi-resistor",
      "value": 220
    },
    {
      "id": "wokwi-resistor_2",
      "type": "wokwi-resistor",
      "value": 220
    },
    {
      "id": "wokwi-resistor_3",
      "type": "wokwi-resistor",
      "value": 220
    }
  ],
  "connections": [
    {
      "from": "wokwi-pi-pico:3V3",
      "to": "wokwi-rgb-led:COM"
    },
    {
      "from": "wokwi-pi-pico:GND",
      "to": "wokwi-dht22:GND.1"
    },
    {
      "from": "wokwi-pi-pico:GND",
      "to": "wokwi-rgb-led:GND.3"
    },
    {
      "from": "wokwi-pi-pico:GND",
      "to": "board-ssd1306:GND.2"
    },
    {
      "from": "wokwi-pi-pico:GP15",
      "to": "wokwi-dht22:SDA"
    },
    {
      "from": "wokwi-pi-pico:GP4",
      "to": "board-ssd1306:SDA"
    },
    {
      "from": "wokwi-pi-pico:GP5",
      "to": "board-ssd1306:SCL"
    }
  ]
}
```

---

## 💻 3. Desenvolvedor (MicroPython)

```python
import time
import dht
from ssd1306 import SSD1306_I2C

# Inicialização dos periféricos
dht_sensor = DHT22(machine.Pin(15))
display = SSD1306_I2C(128, 64, machine.I2C(scl=machine.Pin(5), sda=machine.Pin(4)))
led_r = Pin(16, Pin.OUT)
led_g = Pin(17, Pin.OUT)
led_b = Pin(18, Pin.OUT)

# Funções
def read_dht():
    try:
        dht_sensor.measure()
        temp = dht_sensor.temperature()
        hum = dht_sensor.humidity()
        return {"temp": temp, "hum": hum}
    except OSError:
        return {"temp": None, "hum": None}

def update_display(data):
    display.fill(0)
    display.text("MBA-FIAP", 16, 0, 1)
    display.line(0, 12, 128, 12, 1)
    if data["temp"] is not None and data["hum"] is not None:
        display.text(f"Temp: {data['temp']:.1f} C", 16, 24, 1)
        display.text(f"Hum: {data['hum']:.1f}%", 16, 42, 1)
    else:
        display.text("ERRO SENSOR", 16, 24, 1)
        display.text("ERRO SENSOR", 16, 42, 1)
    display.show()

def set_led_color(data):
    if data["temp"] is not None and data["hum"] is not None:
        temp = data["temp"]
        hum = data["hum"]
        if temp < 15 or hum > 60:
            led_r.value(1)
            led_g.value(0)
            led_b.value(0)
        elif temp >= 20 and temp <= 30 and hum >= 40 and hum <= 70:
            led_r.value(0)
            led_g.value(1)
            led_b.value(0)
        else:
            led_r.value(1)
            led_g.value(1)
            led_b.value(0)
    else:
        led_r.value(1)
        led_g.value(0)
        led_b.value(1)

def send_telemetry(data):
    print(json.dumps(data))

# Estrutura do loop principal
while True:
    current_time = time.ticks_ms()
    
    # RF01 – Aquisição de Dados do DHT22
    dht_data = read_dht()
    
    # RF02 – Interface Gráfica no Display OLED I2C (GP4/GP5)
    update_display(dht_data)
    
    # RF03 – Sinalização Visual via LED RGB (GP16, GP17, GP18)
    set_led_color(dht_data)
    
    # RF04 – Telemetria via Console Serial (USB/UART)
    send_telemetry(dht_data)
    
    # RNF01 – Arquitetura Não-Bloqueante
    next_time = current_time + 2000
    while time.ticks_diff(next_time, time.ticks_ms()) > 0:
        pass
```

```json
{
  "version": 1,
  "author": "EdgeAI",
  "editor": "wokwi",
  "parts": [
    {
      "id": "wokwi-pi-pico",
      "type": "wokwi-pi-pico"
    },
    {
      "id": "wokwi-dht22",
      "type": "wokwi-dht22",
      "attrs": {
        "pin": 15
      }
    },
    {
      "id": "board-ssd1306",
      "type": "board-ssd1306",
      "attrs": {
        "i2c_addr": 0x3c,
        "sda_pin": 4,
        "scl_pin": 5
      }
    },
    {
      "id": "wokwi-rgb-led",
      "type": "wokwi-rgb-led",
      "attrs": {
        "common": "cathode"
      }
    },
    {
      "id": "wokwi-resistor_1",
      "type": "wokwi-resistor",
      "value": 220
    },
    {
      "id": "wokwi-resistor_2",
      "type": "wokwi-resistor",
      "value": 220
    },
    {
      "id": "wokwi-resistor_3",
      "type": "wokwi-resistor",
      "value": 220
    }
  ],
  "connections": [
    {
      "from": "wokwi-pi-pico:3V3",
      "to": "wokwi-rgb-led:COM"
    },
    {
      "from": "wokwi-pi-pico:GND",
      "to": "wokwi-dht22:GND.1"
    },
    {
      "from": "wokwi-pi-pico:GND",
      "to": "wokwi-rgb-led:GND.3"
    },
    {
      "from": "wokwi-pi-pico:GND",
      "to": "board-ssd1306:GND.2"
    },
    {
      "from": "wokwi-pi-pico:GP15",
      "to": "wokwi-dht22:SDA"
    },
    {
      "from": "wokwi-pi-pico:GP4",
      "to": "board-ssd1306:SDA"
    },
    {
      "from": "wokwi-pi-pico:GP5",
      "to": "board-ssd1306:SCL"
    }
  ]
}
```
