### Mapeamento de Objetos MicroPython

```python
from machine import Pin, ADC, PWM, I2C
import dht
import time
import json
from ssd1306 import SSD1306_I2C

# Pinos definidos no escopo
display = SSD1306_I2C(128, 64, I2C(0, sda=Pin(4), scl=Pin(5)))
button = Pin(14, Pin.IN, Pin.PULL_UP)
led_verde = Pin(16, Pin.OUT)
led_amarelo = PWM(Pin(17))
led_vermelho = Pin(18, Pin.OUT)
servo = PWM(Pin(13))

# Sensor DHT22
dht_sensor = dht.DHT22(Pin(15))

# Sensores ADC
ldr_adc = ADC(Pin(26))
potenciometro_adc = ADC(Pin(27))
```

### Assinaturas das Funções e Fórmulas de Conversão

```python
def read_luminosity():
    # Convertendo o valor lido do ADC0 para uma porcentagem de luminosidade (0 a 100%)
    return int(ldr_adc.read_u16() * 100 / 65535)

def convert_temperature_to_pwm(temperature):
    # Abertura proporcional do servo motor, abertura entre 0 e 90 graus se a temperatura for maior que o setpoint
    if temperature > setpoint:
        return int((temperature - 15) * (90 / 25))
    else:
        return 0

def send_telemetry():
    # Enviar dados de telemetria em formato JSON quando o botão é pressionado
    data = {
        "temperature": dht_sensor.temperature,
        "humidity": dht_sensor.humidity,
        "luminosity": read_luminosity()
    }
    json_data = json.dumps(data)
    print(json_data)
```

### Fluxo do Loop Principal Não-Bloqueante

```python
def loop():
    while True:
        current_time = time.ticks_ms()

        # Lendo sensor DHT22
        try:
            dht_sensor.measure()
            temperature = dht_sensor.temperature
            humidity = dht_sensor.humidity
        except OSError as e:
            print("Erro ao ler sensor DHT22:", e)
            display.text("Erro DHT", 0, 0)

        # Lendo sensores ADC
        luminosity = read_luminosity()
        setpoint_temperature = potenciometro_adc.read_u16() * 15 / 65535

        # Controle do servo motor
        servo.duty_u16(convert_temperature_to_pwm(temperature))

        # Atualizando tela OLED SSD1306
        display.fill(0)
        display.text(f"Temp: {temperature:.2f}C", 0, 0)
        display.text(f"Hum: {humidity:.2f}%", 0, 8)
        display.text(f"Lum: {luminosity:.2f}%", 0, 16)
        display.show()

        # Verificando pressionamento do botão
        if button.value() == 0:
            send_telemetry()
            display.fill(0)
            display.text("Telemetria enviada", 0, 0)

        # Intervalo de amostragem
        time.sleep_ms(500)
```

Este é o esboço técnico para a arquitetura do firmware MicroPython no Wokwi.