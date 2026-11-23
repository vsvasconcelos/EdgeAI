import machine
from machine import Pin, I2C
import dht
import time
import json
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
# Inicializações globais
dht_sensor = dht.DHT22(Pin(15))
i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=400000)
oled = SSD1306_I2C(128, 64, i2c)
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
def atualizar_led(cor):
    global cor_atual
    if cor != cor_atual:
        led_r.value(0)
        led_g.value(0)
        led_b.value(0)
        if cor == 'RED':
            led_r.value(1)
        elif cor == 'GREEN':
            led_g.value(1)
        elif cor == 'BLUE':
            led_b.value(1)
        elif cor == 'MAGENTA':
            led_r.value(1)
            led_b.value(1)
        cor_atual = cor
def ler_sensor_dht22():
    global temp, hum
    try:
        dht_sensor.measure()
        temp = dht_sensor.temperature()
        hum = dht_sensor.humidity()
    except OSError:
        print("ERRO SENSOR")
        atualizar_led('MAGENTA')
        temp = None
        hum = None
def atualizar_display():
    oled.fill(0)
    oled.text("MBA-FIAP", 0, 0)
    oled.line(0, 12, 127, 12)
    if temp is not None and hum is not None:
        oled.text(f"Temp: {temp:.1f} C", 0, 24)
        oled.text(f"Umid: {hum:.1f} %", 0, 42)
    else:
        oled.text("ERRO SENSOR", 0, 24)
        oled.text("ERRO SENSOR", 0, 42)
    oled.show()
def determinar_cor(temp, hum):
    if temp > 30.0 or hum < 30.0:
        return 'RED'
    elif temp < 18.0 or hum > 75.0:
        return 'BLUE'
    elif 18.0 <= temp <= 26.0 and 40.0 <= hum <= 70.0:
        return 'GREEN'
    else:
        return 'YELLOW'
def telemetria_console():
    if temp is not None and hum is not None:
        print(json.dumps({"temp": temp, "hum": hum, "led_color": determinar_cor(temp, hum)}))
# Função principal
while True:
    current_time = time.ticks_ms()
    # Atualiza sensor DHT22 a cada 2000 ms
    if time.ticks_diff(current_time, last_dht) >= 2000:
        ler_sensor_dht22()
        last_dht = current_time
    # Atualiza display OLED a cada 1000 ms
    if time.ticks_diff(current_time, last_oled) >= 1000:
        atualizar_display()
        last_oled = current_time
    # Imprime telemetria no console serial a cada 2000 ms
    telemetria_console()
    # Espera 50 ms antes da próxima iteração
    time.sleep_ms(50)