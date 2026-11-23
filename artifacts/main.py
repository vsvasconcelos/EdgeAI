import machine
from machine import Pin, I2C
import time
import json
from ssd1306 import SSD1306_I2C
import dht

# Instanciação do Sensor DHT22
dht_sensor = dht.DHT22(Pin(15))

# Instanciação do Display OLED SSD1306
i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=400000)
oled = SSD1306_I2C(128, 64, i2c)

# Instanciação dos Pinos do LED RGB
led_r = Pin(16, Pin.OUT)
led_g = Pin(17, Pin.OUT)
led_b = Pin(18, Pin.OUT)

# Variáveis de Telemetria
temp = None
hum = None
cor_atual = 'OFF'

# Contadores Não-Bloqueantes
last_dht = time.ticks_ms() - 2000
last_oled = time.ticks_ms() - 1000

def atualizar_sensor_dht22():
    global last_dht
    global temp, hum
    current_time = time.ticks_ms()
    if time.ticks_diff(current_time, last_dht) >= 2000:
        try:
            dht_sensor.measure()
            temp = dht_sensor.temperature()
            hum = dht_sensor.humidity()
        except OSError:
            oled.text("ERRO SENSOR", 0, 36)
            led_r.value(1)
            led_g.value(0)
            led_b.value(1)
            print('{"temp": null, "hum": null, "led_color": "MAGENTA"}')
        last_dht = current_time

def atualizar_display_oled():
    global last_oled
    global temp, hum
    current_time = time.ticks_ms()
    if time.ticks_diff(current_time, last_oled) >= 1000:
        oled.fill(0)
        oled.text("MBA-FIAP", 32, 0)
        oled.line(0, 12, 128, 12)
        if temp is not None and hum is not None:
            oled.text(f"Temp: {temp} C", 0, 24)
            oled.text(f"Umid: {hum} %", 0, 36)
        oled.show()
        last_oled = current_time

def enviar_telemetria_serial():
    global temp, hum
    if temp is not None and hum is not None:
        led_color = "GREEN"
    else:
        led_color = "MAGENTA"
    print(json.dumps({"temp": temp, "hum": hum, "led_color": led_color}))

def loop_principal():
    while True:
        atualizar_sensor_dht22()
        atualizar_display_oled()
        enviar_telemetria_serial()
        time.sleep_ms(50)

loop_principal()