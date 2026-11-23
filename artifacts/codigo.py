import machine
from machine import Pin, I2C
import time
import json
import dht
from ssd1306 import SSD1306_I2C

# ==============================================================================
# Configuração de Pinos e Interfaces de Hardware (RP2040 / Raspberry Pi Pico)
# ==============================================================================
PIN_DHT = 15
PIN_I2C_SDA = 4
PIN_I2C_SCL = 5
PIN_LED_R = 16
PIN_LED_G = 17
PIN_LED_B = 18

# Configuração do LED RGB (Cátodo comum: 1 = ligado, 0 = desligado)
led_r = Pin(PIN_LED_R, Pin.OUT)
led_g = Pin(PIN_LED_G, Pin.OUT)
led_b = Pin(PIN_LED_B, Pin.OUT)

# Configuração do Barramento I2C0 e Display OLED SSD1306 (128x64, addr 0x3c)
i2c = I2C(0, scl=Pin(PIN_I2C_SCL), sda=Pin(PIN_I2C_SDA), freq=400000)
display = SSD1306_I2C(128, 64, i2c)

# Configuração do Sensor de Temperatura e Umidade DHT22
dht_sensor = dht.DHT22(Pin(PIN_DHT))


# ==============================================================================
# Funções de Controle de Atuadores e Interface Gráfica
# ==============================================================================
def set_led_color(r: int, g: int, b: int):
    """Atualiza o estado dos canais R, G e B do LED RGB."""
    led_r.value(1 if r else 0)
    led_g.value(1 if g else 0)
    led_b.value(1 if b else 0)


def avaliar_clima(temp: float, hum: float) -> tuple[str, int, int, int]:
    """
    Avalia faixas de temperatura e umidade conforme regras de prioridade (RF03):
    1. Vermelho (Alerta Crítico): T > 30.0 ou U < 30.0
    2. Azul (Ambiente Frio/Úmido): T < 18.0 ou U > 75.0
    3. Verde (Conforto Ideal): 18.0 <= T <= 26.0 e 40.0 <= U <= 70.0
    4. Amarelo (Atenção Moderada): Qualquer outra condição intermediária
    """
    if temp > 30.0 or hum < 30.0:
        return "RED", 1, 0, 0
    if temp < 18.0 or hum > 75.0:
        return "BLUE", 0, 0, 1
    if (18.0 <= temp <= 26.0) and (40.0 <= hum <= 70.0):
        return "GREEN", 0, 1, 0
    return "YELLOW", 1, 1, 0


def renderizar_display(temp: float = None, hum: float = None, erro: bool = False):
    """Renderiza a interface no display OLED SSD1306 (RF02 e RNF02)."""
    display.fill(0)
    # Cabeçalho fixo (Linha 1) e divisória
    display.text("MBA-FIAP", 32, 0)
    display.hline(0, 12, 128, 1)

    if erro:
        display.text("ERRO SENSOR", 20, 32)
    elif temp is not None and hum is not None:
        display.text("Temp: {:.1f} C".format(temp), 16, 24)
        display.text("Umid: {:.1f} %".format(hum), 16, 42)
    display.show()


# ==============================================================================
# Loop Principal Não-Bloqueante
# ==============================================================================
def main():
    # Inicializa tela e LED
    renderizar_display(None, None, erro=False)
    set_led_color(0, 0, 0)

    # Temporizadores não-bloqueantes
    intervalo_dht_ms = 2000
    intervalo_oled_ms = 1000

    ultimo_ticks_dht = time.ticks_ms() - intervalo_dht_ms
    ultimo_ticks_oled = time.ticks_ms() - intervalo_oled_ms

    temp_atual = None
    hum_atual = None
    cor_atual = "OFF"
    falha_sensor = False

    while True:
        agora = time.ticks_ms()

        # Leitura do DHT22 e Telemetria Serial a cada 2.000 ms (RF01 e RF04)
        if time.ticks_diff(agora, ultimo_ticks_dht) >= intervalo_dht_ms:
            ultimo_ticks_dht = agora
            try:
                dht_sensor.measure()
                temp_atual = dht_sensor.temperature()
                hum_atual = dht_sensor.humidity()
                falha_sensor = False
                cor_atual, r, g, b = avaliar_clima(temp_atual, hum_atual)
                set_led_color(r, g, b)
                # Telemetria JSON compacta
                telemetria = {"temp": temp_atual, "hum": hum_atual, "led_color": cor_atual}
                print(json.dumps(telemetria))
            except OSError:
                falha_sensor = True
                temp_atual = None
                hum_atual = None
                cor_atual = "MAGENTA"
                set_led_color(1, 0, 1)
                telemetria = {"temp": None, "hum": None, "led_color": "MAGENTA"}
                print(json.dumps(telemetria))

        # Atualização do Display OLED a cada 1.000 ms (RF02 e RNF02)
        if time.ticks_diff(agora, ultimo_ticks_oled) >= intervalo_oled_ms:
            ultimo_ticks_oled = agora
            renderizar_display(temp_atual, hum_atual, erro=falha_sensor)

        time.sleep_ms(50)


if __name__ == "__main__":
    main()
