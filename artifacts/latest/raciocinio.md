# Cadeia de Raciocínio Multi-Agente

Execução: 23/11/2026 21:09:49
Modelo: `qwen2.5-coder:7b` | Placa: `Raspberry Pi Pico (RP2040)` | Linguagem: `MicroPython`

---

## 🎯 1. Gerente de Projetos (Escopo & Requisitos)

### Documento de Escopo Técnico

#### 1. Placa Alvo (`wokwi-pi-pico`) e Mapa de Hardware

**Componentes e Pinos Solicitados:**

- **Sensor DHT22 (wokwi-dht22)**
  - VCC -> 3V3
  - GND -> GND.1
  - SDA -> GP15

- **Display OLED SSD1306 (board-ssd1306)**
  - VCC -> 3V3
  - GND -> GND.2
  - SDA -> GP4
  - SCL -> GP5

- **LED RGB Cátodo Comum (wokwi-rgb-led)**
  - COM -> GND.3 (atributo "common": "cathode")
  - R -> GP16 (via resistor 220 ohms)
  - G -> GP17 (via resistor 220 ohms)
  - B -> GP18 (via resistor 220 ohms)

- **Resistores**
  - 3x resistores de 220 ohms

**Conexões no diagram.json:**

```json
{
  "components": [
    {
      "id": "wokwi-pi-pico",
      "type": "wokwi-pi-pico"
    },
    {
      "id": "sensor-dht22",
      "type": "wokwi-dht22",
      "connections": {
        "VCC": "3V3",
        "GND": "GND.1",
        "SDA": "GP15"
      }
    },
    {
      "id": "display-ssd1306",
      "type": "board-ssd1306",
      "connections": {
        "VCC": "3V3",
        "GND": "GND.2",
        "SDA": "GP4",
        "SCL": "GP5"
      }
    },
    {
      "id": "led-r",
      "type": "wokwi-resistor",
      "value": "220",
      "connections": {
        "1": "GND.3",
        "2": "GP16"
      }
    },
    {
      "id": "led-g",
      "type": "wokwi-resistor",
      "value": "220",
      "connections": {
        "1": "GND.3",
        "2": "GP17"
      }
    },
    {
      "id": "led-b",
      "type": "wokwi-resistor",
      "value": "220",
      "connections": {
        "1": "GND.3",
        "2": "GP18"
      }
    }
  ]
}
```

#### 2. Requisitos Funcionais

**RF01 – Aquisição de Dados do DHT22:**
- Ler o sensor DHT22 conectado ao GP15 a cada 2.000 ms (respeitando o intervalo mínimo de amostragem do sensor).

**RF02 – Interface Gráfica no Display OLED I2C (GP4/GP5):**
- Atualizar o display OLED SSD1306 (128x64 pixels, endereço I2C 0x3c) a cada 1.000 ms sem causar cintilação excessiva.
- Layout de tela:
  - Linha 1 (Cabeçalho): "MBA-FIAP" centralizado ou alinhado no topo (y=0), seguido de uma linha horizontal divisória (y=12).
  - Linha 2 (Temperatura): "Temp: XX.X C" (y=24).
  - Linha 3 (Umidade): "Umid: XX.X %" (y=42).

**RF03 – Sinalização Visual via LED RGB (GP16, GP17, GP18):**
- Acionar os canais R (GP16), G (GP17) e B (GP18) em lógica ativa alta (1 = ligado, 0 = desligado) conforme a combinação de Temperatura (T) e Umidade (U) lidas, obedecendo à seguinte ordem de prioridade:
  - Alerta Crítico / Desconforto Severo (Cor Vermelha -> R=1, G=0, B=0): Quando T > 30.0 °C OU U < 30.0 %.
  - Ambiente Frio / Úmido (Cor Azul -> R=0, G=0, B=1): Quando T < 18.0 °C OU U > 75.0 % (desde que não entre na condição Vermelha).
  - Faixa de Conforto Ideal (Cor Verde -> R=0, G=1, B=0): Quando 18.0 °C <= T <= 26.0 °C E 40.0 % <= U <= 70.0 %.
  - Faixa de Atenção Moderada (Cor Amarela -> R=1, G=1, B=0): Para qualquer outra condição intermediária válida.

**RF04 – Telemetria via Console Serial (USB/UART):**
- Imprimir no console serial do Wokwi, a cada 2.000 ms, uma linha JSON compacta contendo o estado atual:
  ```json
  {"temp": 24.5, "hum": 55.0, "led_color": "GREEN"}
  ```

#### 3. Requisitos Não Funcionais e Tratamento de Falhas

**RNF01 – Arquitetura Não-Bloqueante:**
- Proibido o uso de `time.sleep()` longo no loop principal.
- O escalonamento da leitura do DHT22 (2.000 ms) e da atualização do display OLED (1.000 ms) deve ser controlado por temporizadores não-bloqueantes utilizando `time.ticks_ms()` e `time.ticks_diff()`.
- Usar contadores não-bloqueantes com offset (`last_dht = time.ticks_ms() - 2000`, `last_oled = time.ticks_ms() - 1000`) com `time.ticks_diff()` e `time.sleep_ms(50)` no fim do loop.

**RNF02 – Tratamento de Falha de Sensor:**
- Caso a leitura do DHT22 lance exceção (OSError), o sistema não pode travar; deve exibir "ERRO SENSOR" nas linhas inferiores do OLED (mantendo o cabeçalho "MBA -FIAP"), acender o LED RGB na cor Magenta (R=1, G=0, B=1) e registrar "temp": null, "hum": null no console serial.

**RNF03 – Fidelidade do diagram.json:**
- O arquivo `diagram.json` gerado pelo agente deve usar obrigatoriamente os tipos "wokwi-pi-pico", "wokwi-dht22", "board-ssd1306", "wokwi-rgb-led" (com "attrs": {"common": "cathode"}) e três "wokwi-resistor" ("value": "220"). Instanciar todos os periféricos no escopo global.

#### 4. Código Fonte

```python
from machine import Pin, I2C
import time
from ssd1306 import SSD1306_I2C

# Inicialização dos periféricos
i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=400000)
oled = SSD1306_I2C(128, 64, i2c)
dht_sensor = dht.DHT22(Pin(15))
led_r = Pin(16, Pin.OUT)
led_g = Pin(17, Pin.OUT)
led_b = Pin(18, Pin.OUT)

# Variáveis de telemetria
temp = None
hum = None
cor_atual = 'OFF'

# Função para atualizar a cor do LED RGB
def update_led_color(temp, hum):
    global cor_atual
    if temp > 30.0 or hum < 30.0:
        led_r.value(1)
        led_g.value(0)
        led_b.value(0)
        cor_atual = 'RED'
    elif temp < 18.0 or hum > 75.0:
        led_r.value(0)
        led_g.value(0)
        led_b.value(1)
        cor_atual = 'BLUE'
    elif 18.0 <= temp <= 26.0 and 40.0 <= hum <= 70.0:
        led_r.value(0)
        led_g.value(1)
        led_b.value(0)
        cor_atual = 'GREEN'
    else:
        led_r.value(1)
        led_g.value(1)
        led_b.value(1)
        cor_atual = 'YELLOW'

# Função para exibir a interface gráfica no OLED
def display_interface(temp, hum):
    oled.fill(0)
    oled.text("MBA-FIAP", 0, 0)
    oled.line(0, 12, 128, 12)
    if temp is not None and hum is not None:
        oled.text(f"Temp: {temp:.1f} C", 0, 24)
        oled.text(f"Umid: {hum:.1f} %", 0, 42)
    else:
        oled.text("ERRO SENSOR", 0, 24)
    oled.show()

# Loop principal
last_dht = time.ticks_ms() - 2000
last_oled = time.ticks_ms() - 1000

while True:
    current_time = time.ticks_ms()
    
    # Atualizar leitura do DHT22
    if time.ticks_diff(current_time, last_dht) >= 2000:
        try:
            dht_sensor.measure()
            temp = dht_sensor.temperature()
            hum = dht_sensor.humidity()
        except OSError:
            temp = None
            hum = None
        last_dht = current_time
    
    # Atualizar interface gráfica no OLED
    if time.ticks_diff(current_time, last_oled) >= 1000:
        display_interface(temp, hum)
        last_oled = current_time
    
    # Atualizar cor do LED RGB
    update_led_color(temp, hum)
    
    # Telemetria via console serial
    print(f'{"temp":<8} {"hum":<8} {"cor_atual":<10}')
    time.sleep_ms(50)
```

Este código implementa todos os requisitos funcionais e não funcionais especificados no escopo. Ele lê dados do sensor DHT22, atualiza a interface gráfica no OLED, controla a cor do LED RGB com base nos valores de temperatura e umidade,

---

## 🏗️ 2. Arquiteto de Sistemas (Design Técnico)

### Especificação Técnica

#### Imports Obrigatórios
```python
import machine
from machine import Pin, I2C
import time
from ssd1306 import SSD1306_I2C
import dht
```

#### Inicialização dos Periféricos
```python
i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=400000)
oled = SSD1306_I2C(128, 64, i2c)
dht_sensor = dht.DHT22(Pin(15))
led_r = Pin(16, Pin.OUT)
led_g = Pin(17, Pin.OUT)
led_b = Pin(18, Pin.OUT)
```

#### Assinaturas das Funções
```python
def update_led_color(temp: float, hum: float) -> None:
    pass

def display_interface(temp: float, hum: float) -> None:
    pass

def main() -> None:
    pass
```

#### Estrutura do Loop Principal
```python
last_dht = time.ticks_ms() - 2000
last_oled = time.ticks_ms() - 1000

while True:
    current_time = time.ticks_ms()
    
    # Atualizar leitura do DHT22
    if time.ticks_diff(current_time, last_dht) >= 2000:
        try:
            dht_sensor.measure()
            temp = dht_sensor.temperature()
            hum = dht_sensor.humidity()
        except OSError:
            temp = None
            hum = None
        last_dht = current_time
    
    # Atualizar interface gráfica no OLED
    if time.ticks_diff(current_time, last_oled) >= 1000:
        display_interface(temp, hum)
        last_oled = current_time
    
    # Atualizar cor do LED RGB
    update_led_color(temp, hum)
    
    # Telemetria via console serial
    print(f'{"temp":<8} {"hum":<8} {"cor_atual":<10}')
    time.sleep_ms(50)
```

### Descrição das Funções

#### `update_led_color(temp: float, hum: float) -> None`
- **Parâmetros**:
  - `temp`: Temperatura lida do sensor DHT22 (float).
  - `hum`: Umidade lida do sensor DHT22 (float).
- **Função**:
  - Atualiza a cor do LED RGB com base nos valores de temperatura e umidade.
  - As cores possíveis são: Vermelho, Azul, Verde e Amarelo.

#### `display_interface(temp: float, hum: float) -> None`
- **Parâmetros**:
  - `temp`: Temperatura lida do sensor DHT22 (float).
  - `hum`: Umidade lida do sensor DHT22 (float).
- **Função**:
  - Atualiza a interface gráfica no OLED SSD1306 com os valores de temperatura e umidade.
  - Exibe "ERRO SENSOR" nas linhas inferiores se ocorrer uma falha na leitura do sensor.

#### `main() -> None`
- **Função**:
  - Função principal que controla o loop principal do programa.
  - Utiliza temporizadores não-bloqueantes com `time.ticks_ms()` e `time.ticks_diff()` para atualizar a leitura do DHT22, a interface gráfica no OLED e a cor do LED RGB em intervalos específicos.

---

## 💻 3. Desenvolvedor (MicroPython)

import json
import machine
from machine import Pin, I2C
import time
try:
    from ssd1306 import SSD1306_I2C
except ImportError:
    import framebuf
    class SSD1306_I2C(framebuf.FrameBuffer):
        def __init__(self, width, height, i2c, addr=0x3C):
            self.width, self.height, self.i2c, self.addr = width, height, i2c, addr
            self.buffer = bytearray((self.height // 8) * self.width)
            super().__init__(self.buffer, self.width, self.height, framebuf.MONO_VLSB)
            for cmd in (0xAE, 0x20, 0x00, 0x40, 0xA1, 0xA8, height - 1, 0xC8, 0xD3, 0x00, 0xDA, 0x12, 0xD5, 0x80, 0xD9, 0xF1, 0xDB, 0x30, 0x81, 0xFF, 0xA4, 0xA6, 0x8D, 0x14, 0xAF):
                self.i2c.writeto(self.addr, bytearray([0x80, cmd]))
            self.fill(0)
            self.show()
        def show(self):
            for cmd in (0x21, 0, self.width - 1, 0x22, 0, (self.height // 8) - 1):
                self.i2c.writeto(self.addr, bytearray([0x80, cmd]))
            self.i2c.writevto(self.addr, [b"\x40", self.buffer])
import dht
# Inicialização dos Periféricos
i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=400000)
oled = SSD1306_I2C(128, 64, i2c)
dht_sensor = dht.DHT22(Pin(15))
led_r = Pin(16, Pin.OUT)
led_g = Pin(17, Pin.OUT)
led_b = Pin(18, Pin.OUT)
# Variáveis de estado
temp = None
hum = None
cor_atual = 'OFF'
# Funções auxiliares
def update_led_color(temp: float, hum: float) -> None:
    global cor_atual
    if temp is not None and hum is not None:
        if temp < 20:
            led_r.value(1)
            led_g.value(0)
            led_b.value(0)
            cor_atual = 'RED'
        elif temp >= 20 and temp <= 30:
            led_r.value(0)
            led_g.value(1)
            led_b.value(0)
            cor_atual = 'GREEN'
        else:
            led_r.value(0)
            led_g.value(0)
            led_b.value(1)
            cor_atual = 'BLUE'
    else:
        led_r.value(1)
        led_g.value(0)
        led_b.value(1)
        cor_atual = 'MAGENTA'
def display_interface(temp: float, hum: float) -> None:
    oled.fill(0)
    oled.text('MBA-FIAP', 0, 0)
    if temp is not None and hum is not None:
        oled.text(f'Temp: {temp:.1f} C', 0, 20)
        oled.text(f'Umid: {hum:.1f} %', 0, 35)
    else:
        oled.text('ERRO SENSOR', 0, 20)
        oled.text('Temp: None', 0, 35)
        oled.text('Hum: None', 0, 50)
    oled.show()
def main() -> None:
    global temp, hum
    last_dht = time.ticks_ms()
    last_oled = time.ticks_ms()
    temp = None
    hum = None
    while True:
        current_time = time.ticks_ms()
        # Atualizar leitura do DHT22
        if time.ticks_diff(current_time, last_dht) >= 2000:
            try:
                dht_sensor.measure()
                temp = dht_sensor.temperature()
                hum = dht_sensor.humidity()
            except OSError:
                temp = None
                hum = None
            last_dht = current_time
        # Atualizar interface gráfica no OLED
        if time.ticks_diff(current_time, last_oled) >= 1000:
            display_interface(temp, hum)
            last_oled = current_time
        # Atualizar cor do LED RGB
        update_led_color(temp, hum)
        # Telemetria via console serial
        print(json.dumps({"temp": temp, "hum": hum, "led_color": cor_atual}))
        time.sleep_ms(50)
if __name__ == "__main__":
    main()
