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

# Variáveis globais
tela_atual = 0
ultimo_clique = 0
ultima_leitura = 0
ultima_oled = 0

def read_luminosity():
    # Convertendo o valor lido do ADC0 para uma porcentagem de luminosidade (0 a 100%)
    return int(ldr_adc.read_u16() * 100 / 65535)

def convert_temperature_to_pwm(temperature, setpoint=25.0):
    # Abertura proporcional do servo motor, abertura entre 0 e 90 graus se a temperatura for maior que o setpoint
    if temperature > setpoint:
        angulo = min(90.0, (temperature - setpoint) * (90.0 / 5.0))
    else:
        angulo = 0.0
    duty_us = 500 + (angulo / 90.0) * 1000
    return int((duty_us / 20000.0) * 65535)

def send_telemetry(temperature, humidity):
    # Enviar dados de telemetria em formato JSON
    data = {
        "temperature": temperature,
        "humidity": humidity,
        "luminosity": read_luminosity()
    }
    json_data = json.dumps(data)
    print(json_data)

def loop():
    led_amarelo.freq(1000)
    servo.freq(50)
    temperature = 25.0
    humidity = 50.0
    while True:
        current_time = time.ticks_ms()

        # Lendo sensor DHT22
        try:
            dht_sensor.measure()
            temperature = dht_sensor.temperature()
            humidity = dht_sensor.humidity()
            led_vermelho.value(0)
            led_verde.value(1)
        except OSError as e:
            print("Erro ao ler sensor DHT22:", e)
            led_vermelho.value(1)
            led_verde.value(0)
            display.fill(0)
            display.text("ERRO DHT22", 0, 0)
            display.show()

        # Lendo sensores ADC
        luminosity = read_luminosity()
        setpoint_temperature = 15.0 + (potenciometro_adc.read_u16() * 25.0 / 65535.0)

        # Controle do LED amarelo via PWM se luz < 40%
        if luminosity < 40:
            led_amarelo.duty_u16(int(((40 - luminosity) / 40.0) * 65535))
        else:
            led_amarelo.duty_u16(0)

        # Controle do servo motor
        servo.duty_u16(convert_temperature_to_pwm(temperature, setpoint_temperature))

        # Atualizando tela OLED SSD1306
        display.fill(0)
        display.text(f"Temp: {temperature:.1f}C", 0, 0)
        display.text(f"Hum: {humidity:.1f}%", 0, 12)
        display.text(f"Set: {setpoint_temperature:.1f}C", 0, 24)
        display.text(f"Lum: {luminosity}%", 0, 36)
        display.show()

        # Telemetria JSON na Serial
        send_telemetry(temperature, humidity)

        # Verificando pressionamento do botão
        if button.value() == 0:
            display.fill(0)
            display.text("MODO: DIAG", 0, 0)
            display.text(f"ADC LDR: {ldr_adc.read_u16()}", 0, 16)
            display.text(f"ADC POT: {potenciometro_adc.read_u16()}", 0, 32)
            display.show()

        # Intervalo de amostragem
        time.sleep_ms(500)

# Inicialização das variáveis globais antes do loop principal
tela_atual = 0
ultimo_clique = 0
ultima_leitura = 0
ultima_oled = 0

# Loop principal
loop()