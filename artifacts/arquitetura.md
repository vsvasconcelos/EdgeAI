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