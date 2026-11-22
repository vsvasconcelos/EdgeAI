"""
Monitor Ambiental Simplificado — Raspberry Pi Pico (RP2040) / MicroPython.
Atende integralmente aos requisitos RF01..RF04 e RNF01..RNF03 no Wokwi.
"""

import json
import time
import dht
import machine
from machine import Pin, I2C
from ssd1306 import SSD1306_I2C

# =============================================================================
# Inicialização dos Periféricos (Pinout RP2040 Obrigatório)
# =============================================================================
dht_sensor = dht.DHT22(Pin(15))
i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=400000)
display = SSD1306_I2C(128, 64, i2c, addr=0x3C)

led_r = Pin(16, Pin.OUT)
led_g = Pin(17, Pin.OUT)
led_b = Pin(18, Pin.OUT)

INTERVALO_DHT_MS = 2000
INTERVALO_OLED_MS = 1000


def ler_dht22() -> dict:
    """RF01 & RNF02: Lê temperatura (°C) e umidade (%) do DHT22 no GP15."""
    try:
        dht_sensor.measure()
        temp = round(float(dht_sensor.temperature()), 1)
        hum = round(float(dht_sensor.humidity()), 1)
        return {"temp": temp, "hum": hum, "erro": False}
    except OSError:
        return {"temp": None, "hum": None, "erro": True}


def atualizar_led_rgb(dados: dict) -> str:
    """
    RF03 & RNF02: Atualiza LED RGB (Cátodo Comum, lógica ativa alta)
    conforme ordem de prioridade de temperatura (T) e umidade (U).
    """
    if dados.get("erro") or dados["temp"] is None or dados["hum"] is None:
        led_r.value(1)
        led_g.value(0)
        led_b.value(1)
        return "MAGENTA"

    temp = dados["temp"]
    hum = dados["hum"]

    # 1. Alerta Crítico / Desconforto Severo (Vermelho)
    if temp > 30.0 or hum < 30.0:
        led_r.value(1)
        led_g.value(0)
        led_b.value(0)
        return "RED"

    # 2. Ambiente Frio / Úmido (Azul)
    if temp < 18.0 or hum > 75.0:
        led_r.value(0)
        led_g.value(0)
        led_b.value(1)
        return "BLUE"

    # 3. Faixa de Conforto Ideal (Verde)
    if 18.0 <= temp <= 26.0 and 40.0 <= hum <= 70.0:
        led_r.value(0)
        led_g.value(1)
        led_b.value(0)
        return "GREEN"

    # 4. Faixa de Atenção Moderada (Amarelo)
    led_r.value(1)
    led_g.value(1)
    led_b.value(0)
    return "YELLOW"


def atualizar_display_oled(dados: dict) -> None:
    """RF02 & RNF02: Atualiza o display OLED SSD1306 (128x64, I2C0 0x3c)."""
    display.fill(0)
    # Linha 1 (Cabeçalho y=0) + linha horizontal divisória (y=12)
    display.text("MBA-FIAP", 32, 0, 1)
    display.line(0, 12, 127, 12, 1)

    if not dados.get("erro") and dados["temp"] is not None and dados["hum"] is not None:
        # Linha 2 (y=24) e Linha 3 (y=42)
        display.text(f"Temp: {dados['temp']:.1f} C", 0, 24, 1)
        display.text(f"Umid: {dados['hum']:.1f} %", 0, 42, 1)
    else:
        display.text("ERRO SENSOR", 0, 24, 1)
        display.text("ERRO SENSOR", 0, 42, 1)

    display.show()


def enviar_telemetria(dados: dict, cor_led: str) -> None:
    """RF04 & RNF02: Imprime linha JSON compacta no console serial."""
    payload = {
        "temp": dados["temp"],
        "hum": dados["hum"],
        "led_color": cor_led,
    }
    print(json.dumps(payload))


def main() -> None:
    """RNF01: Loop principal não-bloqueante baseado em ticks_ms e ticks_diff."""
    agora = time.ticks_ms()
    ultimo_dht = time.ticks_add(agora, -INTERVALO_DHT_MS)
    ultimo_oled = time.ticks_add(agora, -INTERVALO_OLED_MS)

    estado_atual = {"temp": None, "hum": None, "erro": True}
    cor_led = "MAGENTA"

    while True:
        agora = time.ticks_ms()

        # Tarefa de 2.000 ms: Leitura DHT22 + LED RGB + Telemetria Serial
        if time.ticks_diff(agora, ultimo_dht) >= INTERVALO_DHT_MS:
            ultimo_dht = agora
            estado_atual = ler_dht22()
            cor_led = atualizar_led_rgb(estado_atual)
            enviar_telemetria(estado_atual, cor_led)

        # Tarefa de 1.000 ms: Atualização da interface OLED SSD1306
        if time.ticks_diff(agora, ultimo_oled) >= INTERVALO_OLED_MS:
            ultimo_oled = agora
            atualizar_display_oled(estado_atual)

        time.sleep_ms(50)


if __name__ == "__main__":
    main()
