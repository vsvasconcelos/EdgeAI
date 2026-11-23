import machine
from machine import Pin, I2C
import time
import json
import dht

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
            self.i2c.writevto(self.addr, [b"@", self.buffer])

# Instanciação dos periféricos nos pinos oficiais
dht_sensor = dht.DHT22(Pin(15))
i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=400000)
oled = SSD1306_I2C(128, 64, i2c)
display = oled

# Instanciação dos Pinos do LED RGB (Cátodo comum: 1 = ligado, 0 = desligado)
led_r = Pin(16, Pin.OUT)
led_g = Pin(17, Pin.OUT)
led_b = Pin(18, Pin.OUT)

# Variáveis globais de telemetria
temp = None
hum = None
cor_atual = 'OFF'

# Timers não-bloqueantes com offset para rodar no primeiro ciclo
last_dht = time.ticks_ms() - 2000
last_oled = time.ticks_ms() - 1000

def atualizar_led_rgb():
    global cor_atual
    if temp is None or hum is None:
        led_r.value(1); led_g.value(0); led_b.value(1)
        cor_atual = 'MAGENTA'
    elif temp > 30.0 or hum < 30.0:
        led_r.value(1); led_g.value(0); led_b.value(0)
        cor_atual = 'RED'
    elif temp < 18.0 or hum > 75.0:
        led_r.value(0); led_g.value(0); led_b.value(1)
        cor_atual = 'BLUE'
    elif 18.0 <= temp <= 26.0 and 40.0 <= hum <= 70.0:
        led_r.value(0); led_g.value(1); led_b.value(0)
        cor_atual = 'GREEN'
    else:
        led_r.value(1); led_g.value(1); led_b.value(0)
        cor_atual = 'YELLOW'

def enviar_telemetria_serial():
    global temp, hum, cor_atual
    telemetria = {"temp": temp, "hum": hum, "led_color": cor_atual}
    print(json.dumps(telemetria))

def atualizar_sensor_dht22():
    global temp, hum, last_dht
    agora = time.ticks_ms()
    if time.ticks_diff(agora, last_dht) >= 2000:
        last_dht = agora
        try:
            dht_sensor.measure()
            temp = dht_sensor.temperature()
            hum = dht_sensor.humidity()
        except OSError:
            temp = None
            hum = None
        atualizar_led_rgb()
        enviar_telemetria_serial()

def atualizar_display_oled():
    global last_oled
    agora = time.ticks_ms()
    if time.ticks_diff(agora, last_oled) >= 1000:
        last_oled = agora
        oled.fill(0)
        oled.text("MBA-FIAP", 32, 0)
        oled.hline(0, 12, 128, 1)
        if temp is not None and hum is not None:
            oled.text("Temp: {:.1f} C".format(temp), 16, 24)
            oled.text("Umid: {:.1f} % ".format(hum), 16, 42)
        else:
            oled.text("ERRO SENSOR", 20, 32)
        oled.show()

while True:
    atualizar_sensor_dht22()
    atualizar_display_oled()
    time.sleep_ms(50)
