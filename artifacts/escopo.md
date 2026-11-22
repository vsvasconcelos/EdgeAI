# Documento de Escopo Técnico

## 1. Plataforma Alvo e Linguagem / SDK

- **Plataforma**: Raspberry Pi Pico (RP2040)
- **Linguagem / SDK**: MicroPython

## 2. Artefatos de Saída

### 2.1 Código-fonte completo, modularizado e comentado no padrão PEP-8

```python
# main.py
import machine
import dht
import ssd1306
import time
import json

class SSD1306_I2C:
    def __init__(self, i2c, addr):
        self.i2c = i2c
        self.display = ssd1306.SSD1306_I2C(128, 64, i2c, addr)

    def clear(self):
        self.display.fill(0)
        self.display.show()

    def draw_header(self):
        self.display.text("MBA -FIA", 0, 0, 1)
        self.display.hline(0, 12, 128, 1)

    def draw_temperature(self, temp):
        self.display.text(f"Temp: {temp:.1f} C", 0, 24, 1)

    def draw_humidity(self, hum):
        self.display.text(f"Umid: {hum:.1f} %", 0, 42, 1)

def main():
    i2c = machine.I2C(0)
    dht_sensor = dht.DHT22(machine.Pin(15))
    oled_display = SSD1306_I2C(i2c, 0x3c)
    
    last_dht_read = time.ticks_ms()
    last_oled_update = time.ticks_ms()

    while True:
        if time.ticks_diff(time.ticks_ms(), last_dht_read) >= 2000:
            try:
                dht_sensor.measure()
                temp_c = dht_sensor.temperature()
                hum = dht_sensor.humidity()
            except OSError as e:
                oled_display.clear()
                oled_display.draw_header()
                oled_display.draw_temperature("ERRO SENSOR")
                oled_display.draw_humidity("ERRO SENSOR")
                oled_display.show()
                print("ERRO SENSOR")
                continue

            last_dht_read = time.ticks_ms()

        if time.ticks_diff(time.ticks_ms(), last_oled_update) >= 1000:
            oled_display.clear()
            oled_display.draw_header()
            oled_display.draw_temperature(temp_c)
            oled_display.draw_humidity(hum)
            oled_display.show()
            last_oled_update = time.ticks_ms()

        # Sinalização visual via LED RGB
        led_color = "GREEN"
        if temp_c > 30.0 or hum < 30.0:
            led_color = "RED"
        elif temp_c < 18.0 or hum > 75.0:
            led_color = "BLUE"
        elif 18.0 <= temp_c <= 26.0 and 40.0 <= hum <= 70.0:
            led_color = "GREEN"
        else:
            led_color = "YELLOW"

        # Acionar os canais RGB
        if led_color == "RED":
            machine.Pin(16, machine.Pin.OUT).value(1)
            machine.Pin(17, machine.Pin.OUT).value(0)
            machine.Pin(18, machine.Pin.OUT).value(0)
        elif led_color == "BLUE":
            machine.Pin(16, machine.Pin.OUT).value(0)
            machine.Pin(17, machine.Pin.OUT).value(0)
            machine.Pin(18, machine.Pin.OUT).value(1)
        else:
            machine.Pin(16, machine.Pin.OUT).value(0)
            machine.Pin(17, machine.Pin.OUT).value(1)
            machine.Pin(18, machine.Pin.OUT).value(0)

        # Telemetria via Console Serial
        telemetry = {
            "temp": temp_c,
            "hum": hum,
            "led_color": led_color
        }
        print(json.dumps(telemetry))

if __name__ == "__main__":
    main()
```

### 2.2 Arquivo diagram.json válido para o Wokwi Pi Pico contendo todas as conexões de hardware mapeadas abaixo, pronto para execução imediata sem sobreposição de componentes

```json
{
  "components": [
    {
      "id": "wokwi-pi-pico",
      "type": "wokwi-pi-pico",
      "attrs": {}
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
        "i2c": "wokwi-pi-pico:i2c0",
        "addr": 0x3c
      }
    },
    {
      "id": "wokwi-rgb-led",
      "type": "wokwi-rgb-led",
      "attrs": {
        "common": "cathode",
        "pins": [16, 17, 18]
      }
    },
    {
      "id": "wokwi-resistor",
      "type": "wokwi-resistor",
      "attrs": {
        "value": "220"
      }
    },
    {
      "id": "wokwi-resistor-2",
      "type": "wokwi-resistor",
      "attrs": {
        "value": "220"
      }
    },
    {
      "id": "wokwi-resistor-3",
      "type": "wokwi-resistor",
      "attrs": {
        "value": "220"
      }
    }
  ],
  "connections": [
    {
      "from": "wokwi-pi-pico:3V3",
      "to": "board-ssd1306:vcc"
    },
    {
      "from": "wokwi-pi-pico:gnd.2",
      "to": "board-ssd1306:gnd"
    },
    {
      "from": "wokwi-pi-pico:gp4",
      "to": "board-ssd1306:sda"
    },
    {
      "from": "wokwi-pi-pico:gp5",
      "to": "board-ssd1306:scl"
    },
    {
      "from": "wokwi-pi-pico:gnd.3",
      "to": "wokwi-rgb-led:com"
    },
    {
      "from": "wokwi-pi-pico:gp16",
      "to": "wokwi-rgb-led:r"
    },
    {
      "from": "wokwi-pi-pico:gp17",
      "to": "wokwi-rgb-led:g"
    },
    {
      "from": "wokwi-pi-pico:gp18",
      "to": "wokwi-rgb-led:b"
    }
  ]
}
```

## 3. Mapa de Hardware e Pinagem Obrigatória (Pinout RP2040)

| Pino | Função |
|------|--------|
| GP0  | GPIO0  |
| GP1  | GPIO1  |
| GP2  | GPIO2  |
| GP3  | GPIO3  |
| GP4  | SDA    |
| GP5  | SCL    |
| GP6  | GPIO6  |
| GP7  | GPIO7  |
| GP8  | GPIO8  |
| GP9  | GPIO9  |
| GP10 | GPIO10 |
| GP11 | GPIO11 |
| GP12 | GPIO12 |
| GP13 | GND.1  |
| GP14 | VCC    |
| GP15 | SDA    |
| GP16 | R      |
| GP17 | G      |
| GP18 | B      |
| GP19 | GPIO19 |
| GP20 | GPIO20 |
| GP21 | GPIO21 |
| GP22 | GPIO22 |
| GP23 | GPIO23 |
| GP24 | GPIO24 |
| GP25 | GPIO25 |
| GP26 | GND.2  |
| GP27 | VCC    |

## 4. Requisitos Funcionais (RF)

### RF01 – Aquisição de Dados do DHT22
- Ler o sensor DHT22 conectado ao GP15 a cada 2.000 ms (respeitando o intervalo mínimo de amostragem do sensor).

### RF02 – Interface Gráfica no Display OLED I2C (GP4/GP5)
- Atualizar o display OLED SSD1306 (128x64 pixels, endereço I2C 0x3c) a cada 1.000 ms sem causar cintilação excessiva.
- O layout de tela deve seguir rigorosamente 3 linhas de texto:
  * Linha 1 (Cabeçalho): Exibir exatamente o texto "MBA -FIA" centralizado ou alinhado no topo (y=0), seguido de uma linha horizontal divisória (y=12).
  * Linha 2: Exibir a temperatura atualizada.
  * Linha 3: Exibir a humidade atualizada.

### RF03 – Sinalização Visual via LED RGB
- Acionar os canais RGB com base nas condições de temperatura e humidade:
  - Se a temperatura for maior que 30°C ou a humidade menor que 30%, o LED deve ficar vermelho.
  - Se a temperatura for menor que 18°C ou a humidade maior que 75%, o LED deve ficar azul.
  - Caso contrário, se a temperatura estiver entre 18°C e 26°C e a humidade entre 40% e 70%, o LED deve ficar verde.
  - Se nenhuma das condições acima for atendida, o LED deve ficar amarelo.

### RF04 – Telemetria via Console Serial
- Exibir os dados de temperatura, humidade e cor do LED no console serial a cada atualização da interface gráfica.

## 5. Requisitos Adicionais

### 5.1 Modularização do Código
- O código deve ser modularizado para facilitar a manutenção e reutilização.

### 5.2 Tratamento de Erros
- O código deve tratar erros de comunicação com o sensor DHT22 e atualizar o display e o LED corretamente.

### 5.3 Conexões I2C
- As conexões I2C devem ser feitas corretamente para que o display OLED funcione adequadamente.

## 6. Requisitos de Desenvolvimento

### 6.1 Tecnologias Utilizadas
- Python
- MicroPython
- DHT22