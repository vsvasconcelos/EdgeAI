from machine import Pin, ADC, PWM, I2C
import dht
import time
import json
from ssd1306 import SSD1306_I2C

# Inicialização dos pinos e sensores
dht_sensor = dht.DHT22(Pin(15))
led_verde = Pin(16, Pin.OUT)
led_amarelo = PWM(Pin(17))
led_vermelho = Pin(18, Pin.OUT)
servo = PWM(Pin(13))
button = Pin(14, Pin.IN, Pin.PULL_UP)

# Configuração dos PWMs
led_amarelo.freq(1000)
servo.freq(50)

# Inicialização das ADCs
adc_luminosity = ADC(Pin(26))
adc_setpoint = ADC(Pin(27))

# Inicialização do I2C para o OLED
i2c = I2C(0, sda=Pin(4), scl=Pin(5), freq=400000)
oled = SSD1306_I2C(128, 64, i2c)

# Configuração inicial dos valores
temperature = 25.0
humidity = 50.0
luminosity = 50
setpoint = 25.0
servo_angle = 0
tela_atual = 0
ultimo_clique = 0

# Variáveis para temporizadores (iniciadas para disparar na 1ª iteração)
agora_init = time.ticks_ms()
last_dht22_read = time.ticks_add(agora_init, -2000)
last_adc_read = time.ticks_add(agora_init, -500)
last_oled_update = time.ticks_add(agora_init, -500)
last_serial_print = time.ticks_add(agora_init, -2000)

# Função de tratamento de erro do DHT22
def handle_dht22_error():
    oled.fill(0)
    oled.text("ERRO DHT22", 20, 24)
    oled.show()
    led_verde.value(0)
    led_vermelho.toggle()  # Piscar LED Vermelho

# Função de atualização dos LEDs
def update_leds(temperature, setpoint):
    if temperature is None:
        led_verde.value(0)
        led_vermelho.toggle()
    elif temperature <= setpoint + 5.0:
        led_verde.value(1)     # LED Verde ligado (faixa normal)
        led_vermelho.value(0)  # LED Vermelho desligado
    else:
        led_verde.value(0)     # LED Verde desligado
        led_vermelho.value(1)  # LED Vermelho ligado (alarme crítico)

# Função de controle proporcional do servo (0° a 90°)
def control_servo(temperature, setpoint):
    global servo_angle
    if temperature is None or temperature <= setpoint:
        servo_angle = 0
    else:
        servo_angle = min(90, int(((temperature - setpoint) / 5.0) * 90))
    # Conversão de ângulo (0..90°) para pulso PWM em 50Hz (0.5ms a 1.5ms de 20ms)
    duty_us = 500 + (servo_angle / 90.0) * 1000
    servo.duty_u16(int((duty_us / 20000.0) * 65535))

# Função de controle da iluminação auxiliar (LED Amarelo PWM)
def control_led_amarelo(luminosity):
    if luminosity < 40:
        duty = int(((40 - luminosity) / 40.0) * 65535)
        led_amarelo.duty_u16(max(0, min(65535, duty)))
    else:
        led_amarelo.duty_u16(0)

# Função de leitura do DHT22
def read_dht22():
    try:
        dht_sensor.measure()
        temp = round(dht_sensor.temperature(), 1)  # °C
        hum = round(dht_sensor.humidity(), 1)      # %
        return temp, hum
    except OSError:
        handle_dht22_error()
        return None, None

# Função de conversão da luminosidade para porcentagem (0 a 100%)
def convert_luminosity_to_percent(adc_val):
    return int(round((1.0 - (adc_val / 65535.0)) * 100))

# Função de conversão do potenciômetro ADC para setpoint (15.0°C a 40.0°C)
def convert_adc_to_setpoint(adc_val):
    return round(15.0 + (adc_val / 65535.0) * 25.0, 1)

# Função de tratamento da interrupção do botão (GP14) com debounce
def button_handler(pin):
    global tela_atual, ultimo_clique
    agora = time.ticks_ms()
    if time.ticks_diff(agora, ultimo_clique) > 250:
        tela_atual = 1 - tela_atual
        ultimo_clique = agora

# Configuração da interrupção no botão GP14
button.irq(trigger=Pin.IRQ_FALLING, handler=button_handler)

# Loop principal não-bloqueante
while True:
    current_time = time.ticks_ms()

    if time.ticks_diff(current_time, last_dht22_read) >= 2000:
        temperature, humidity = read_dht22()
        last_dht22_read = current_time

    if time.ticks_diff(current_time, last_adc_read) >= 200:
        luminosity = convert_luminosity_to_percent(adc_luminosity.read_u16())
        setpoint = convert_adc_to_setpoint(adc_setpoint.read_u16())
        control_servo(temperature, setpoint)
        control_led_amarelo(luminosity)
        update_leds(temperature, setpoint)
        last_adc_read = current_time

    if time.ticks_diff(current_time, last_oled_update) >= 500:
        oled.fill(0)
        if temperature is None:
            oled.text("ERRO DHT22", 20, 16)
            oled.text(f"Set: {setpoint:.1f} C", 0, 36)
        elif tela_atual == 0:
            oled.text("TELA: OPERACAO", 0, 0)
            oled.text(f"Temp: {temperature:.1f} C", 0, 16)
            oled.text(f"Umid: {humidity:.1f} %", 0, 28)
            oled.text(f"Set : {setpoint:.1f} C", 0, 40)
            oled.text(f"Luz : {luminosity} %", 0, 52)
        else:
            oled.text("TELA: DIAG", 0, 0)
            oled.text(f"Servo: {servo_angle} deg", 0, 16)
            oled.text(f"ADC0 : {adc_luminosity.read_u16()}", 0, 30)
            oled.text(f"ADC1 : {adc_setpoint.read_u16()}", 0, 44)
        oled.show()
        last_oled_update = current_time

    if time.ticks_diff(current_time, last_serial_print) >= 2000:
        json_data = {
            "temp": temperature,
            "humidity": humidity,
            "luminosity": luminosity,
            "setpoint": setpoint,
            "servo": servo_angle,
            "tela": "OPERACAO" if tela_atual == 0 else "DIAG",
        }
        print(json.dumps(json_data))
        last_serial_print = current_time

    time.sleep_ms(20)