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
- Acionar os canais R (GP16), G (GP17) e B (GP18) em lógica ativa alta (1 = ligado, 0 = desligado) conforme a combinação de Temperatura (T) e Umidade (U) lidas.

**RF04 – Telemetria via Console Serial (USB/UART):**
- Imprimir no console serial do Wokwi, a cada 2.000 ms, uma linha JSON compacta contendo o estado atual:
  ```json
  {"temp": 24.5, "hum": 55.0, "led_color": "GREEN"}
  ```

#### 3. Requisitos Não Funcionais e Tratamento de Falhas

**RNF01 – Arquitetura Não-Bloqueante:**
- Proibido o uso de `time.sleep()` longo no loop principal.
- O escalonamento da leitura do DHT22 (2.000 ms) e da atualização do display OLED (1.000 ms) deve ser controlado por temporizadores não-bloqueantes utilizando `time.ticks_ms()` e `time.ticks_diff()`.

**RNF02 – Tratamento de Falha de Sensor:**
- Caso a leitura do DHT22 lance exceção (`OSError`), o sistema não pode travar.
- Deve exibir "ERRO SENSOR" nas linhas inferiores do OLED (mantendo o cabeçalho "MBA -FIAP").
- Acender o LED RGB na cor Magenta (R=1, G=0, B=1).
- Registrar `{"temp": null, "hum": null}` no console serial.

**RNF03 – Fidelidade do diagram.json:**
- O arquivo `diagram.json` gerado pelo agente deve usar obrigatoriamente os tipos `"wokwi-pi-pico"`, `"wokwi-dht22"`, `"board-ssd1306"`, `"wokwi-rgb-led"` (com `"attrs": {"common": "cathode"}}`).
- Três `"wokwi-resistor"` ("value": "220").
- Todos os pinos de alimentação (3V3 e GND) devem estar explicitamente conectados.

#### 4. Restrições de Plataforma

**Linguagem:**
- MicroPython nativo para Raspberry Pi Pico (RP2040).

**Imports Obrigatórios:**
```python
import machine
from machine import Pin, I2C
import time
import json
```

**Instanciamento do Sensor DHT22:**
```python
dht_sensor = dht.DHT22(Pin(15))
```

**Inicialização do OLED SSD1306:**
```python
i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=400000)
oled = SSD1306_I2C(128, 64, i2c)
```

**Instanciamento dos Pinos do LED RGB:**
```python
led_r = Pin(16, Pin.OUT)
led_g = Pin(17, Pin.OUT)
led_b = Pin(18, Pin.OUT)
```

**Variáveis de Telemetria:**
```python
temp = None
hum = None
cor_atual = 'OFF'
last_dht = time.ticks_ms() - 2000
last_oled = time.ticks_ms() - 1000
```

**Contadores Não-Bloqueantes com Offset:**
```python
while True:
    # Lógica do programa aqui
    
    time.sleep_ms(50)
```

Este documento de escopo técnico garante que todos os requisitos funcionais e não funcionais sejam atendidos, utilizando a plataforma `wokwi-pi-pico` e as bibliotecas padrão do MicroPython para o Raspberry Pi Pico.