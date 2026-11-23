import machine
from machine import Pin, I2C
import dht
import time
import json
from ssd1306 import SSD1306_I2C
# Instanciando periféricos
dht_sensor = dht.DHT22(Pin(15))
i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=400000)
display = SSD1306_I2C(128, 64, i2c)
led_r = Pin(16, Pin.OUT)
led_g = Pin(17, Pin.OUT)
led_b = Pin(18, Pin.OUT)
# Variáveis de telemetria
temp = None
hum = None
cor_atual = 'OFF'
# Contadores não-bloqueantes
last_dht = time.ticks_ms() - 2000
last_oled = time.ticks_ms() - 1000
def set_led_color(color: str) -> None:
    """Define a cor do LED RGB."""
    global led_r, led_g, led_b
    if color == 'RED':
        led_r.value(1)
        led_g.value(0)
        led_b.value(0)
    elif color == 'GREEN':
        led_r.value(0)
        led_g.value(1)
        led_b.value(0)
    elif color == 'BLUE':
        led_r.value(0)
        led_g.value(0)
        led_b.value(1)
    elif color == 'MAGENTA':
        led_r.value(1)
        led_g.value(0)
        led_b.value(1)
    else:
        led_r.value(0)
        led_g.value(0)
        led_b.value(0)
def update_display(temp: float, hum: float) -> None:
    """Atualiza o display OLED com as temperaturas e umidade."""
    global display
    display.fill(0)
    display.text("MBA-FIAP", 0, 0)
    if temp is not None and hum is not None:
        display.text(f"Temp: {temp:.1f} C", 0, 24)
        display.text(f"Umid: {hum:.1f} %", 0, 42)
    else:
        display.text("ERRO SENSOR", 0, 24)
    display.show()
def log_telemetry(temp: float, hum: float, led_color: str) -> None:
    """Imprime os dados de telemetria no console serial."""
    if temp is not None and hum is not None:
        print(json.dumps({"temp": temp, "hum": hum, "led_color": led_color}))
while True:
    current_time = time.ticks_ms()
    # Leitura do sensor DHT22
    if time.ticks_diff(current_time, last_dht) >= 2000:
        try:
            dht_sensor.measure()
            temp = dht_sensor.temperature()
            hum = dht_sensor.humidity()
        except OSError:
            display.text("ERRO SENSOR", 0, 12)
            set_led_color('MAGENTA')
        last_dht = current_time
    # Atualização do display OLED
    if time.ticks_diff(current_time, last_oled) >= 1000:
        update_display(temp, hum)
        last_oled = current_time
    # Telemetria via console serial
    if temp is not None and hum is not None:
        log_telemetry(temp, hum, cor_atual)
    # Controle de LED RGB
    if temp > 30.0 or hum < 30.0:
        set_led_color('RED')
    elif temp < 18.0 or hum > 75.0:
        set_led_color('BLUE')
    elif 18.0 <= temp <= 26.0 and 40.0 <= hum <= 70.0:
        set_led_color('GREEN')
    else:
        set_led_color('OFF')
    time.sleep_ms(50)