"""
Monitor Ambiental Simplificado (Raspberry Pi Pico - RP2040)
Plataforma: Wokwi Simulator / MicroPython
Periféricos:
  - Sensor DHT22 (GP15)
  - Display OLED SSD1306 I2C0 (SDA=GP4, SCL=GP5, addr=0x3c)
  - LED RGB Cátodo Comum (R=GP16, G=GP17, B=GP18)
"""

import json
import time
import dht
from machine import Pin, I2C
from ssd1306 import SSD1306_I2C

PIN_DHT22 = 15
PIN_I2C_SDA = 4
PIN_I2C_SCL = 5
OLED_WIDTH = 128
OLED_HEIGHT = 64
OLED_ADDR = 0x3C

PIN_LED_R = 16
PIN_LED_G = 17
PIN_LED_B = 18

INTERVALO_DHT_MS = 2000
INTERVALO_OLED_MS = 1000


def definir_cor_rgb(led_r: Pin, led_g: Pin, led_b: Pin, r: int, g: int, b: int) -> None:
    """Aciona os canais R, G e B do LED RGB (cátodo comum: 1 = ligado, 0 = desligado)."""
    led_r.value(r)
    led_g.value(g)
    led_b.value(b)


def avaliar_faixa_ambiental(
    temp: float, hum: float, led_r: Pin, led_g: Pin, led_b: Pin
) -> str:
    """Avalia Temperatura (T) e Umidade (U) segundo RF03 e aciona o LED RGB."""
    if temp > 30.0 or hum < 30.0:
        definir_cor_rgb(led_r, led_g, led_b, 1, 0, 0)
        return "RED"
    if temp < 18.0 or hum > 75.0:
        definir_cor_rgb(led_r, led_g, led_b, 0, 0, 1)
        return "BLUE"
    if 18.0 <= temp <= 26.0 and 40.0 <= hum <= 70.0:
        definir_cor_rgb(led_r, led_g, led_b, 0, 1, 0)
        return "GREEN"
    definir_cor_rgb(led_r, led_g, led_b, 1, 1, 0)
    return "YELLOW"


def atualizar_oled(oled: SSD1306_I2C, temp, hum, erro: bool) -> None:
    """Atualiza o display OLED SSD1306 respeitando o layout de 3 linhas (RF02 e RNF02)."""
    oled.fill(0)
    oled.text("MBA -FIA", 32, 0)
    oled.hline(0, 12, OLED_WIDTH, 1)

    if erro or temp is None or hum is None:
        oled.text("ERRO SENSOR", 20, 24)
        oled.text("ERRO SENSOR", 20, 42)
    else:
        oled.text(f"Temp: {temp:.1f} C", 0, 24)
        oled.text(f"Umid: {hum:.1f} %", 0, 42)

    oled.show()


def main() -> None:
    """Loop principal não-bloqueante escalonado com time.ticks_ms() e time.ticks_diff()."""
    sensor_dht = dht.DHT22(Pin(PIN_DHT22))
    i2c = I2C(0, sda=Pin(PIN_I2C_SDA), scl=Pin(PIN_I2C_SCL), freq=400000)
    oled = SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c, addr=OLED_ADDR)

    led_r = Pin(PIN_LED_R, Pin.OUT)
    led_g = Pin(PIN_LED_G, Pin.OUT)
    led_b = Pin(PIN_LED_B, Pin.OUT)

    temp_atual = None
    hum_atual = None
    cor_atual = "GREEN"
    erro_sensor = False

    agora_inicial = time.ticks_ms()
    ultimo_dht = time.ticks_add(agora_inicial, -INTERVALO_DHT_MS)
    ultimo_oled = time.ticks_add(agora_inicial, -INTERVALO_OLED_MS)

    while True:
        agora = time.ticks_ms()

        if time.ticks_diff(agora, ultimo_dht) >= INTERVALO_DHT_MS:
            ultimo_dht = agora
            try:
                sensor_dht.measure()
                temp_atual = round(sensor_dht.temperature(), 1)
                hum_atual = round(sensor_dht.humidity(), 1)
                erro_sensor = False
                cor_atual = avaliar_faixa_ambiental(
                    temp_atual, hum_atual, led_r, led_g, led_b
                )
            except OSError:
                temp_atual = None
                hum_atual = None
                erro_sensor = True
                cor_atual = "MAGENTA"
                definir_cor_rgb(led_r, led_g, led_b, 1, 0, 1)

            telemetria = {
                "temp": temp_atual,
                "hum": hum_atual,
                "led_color": cor_atual,
            }
            print(json.dumps(telemetria))

        if time.ticks_diff(agora, ultimo_oled) >= INTERVALO_OLED_MS:
            ultimo_oled = agora
            atualizar_oled(oled, temp_atual, hum_atual, erro_sensor)

        time.sleep_ms(20)


if __name__ == "__main__":
    main()
