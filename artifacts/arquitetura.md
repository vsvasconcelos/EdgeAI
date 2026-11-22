### Mapeamento de Objetos MicroPython

- **DHT22 Sensor**: `dht.DHT22(Pin(15))`
- **ADC (Luminosidade)**: `ADC(Pin(26))` e `ADC(Pin(27))`
- **I2C Interface**: `I2C(0, sda=Pin(4), scl=Pin(5))`
- **SSD1306 OLED Display**: `SSD1306_I2C(128, 64, i2c)`
- **LED RGB Channels**: `Pin(16, Pin.OUT)`, `Pin(17, Pin.OUT)`, `Pin(18, Pin.OUT)`
- **PWM Servo Control**: `PWM(Pin(13))` and `PWM(Pin(14), Pin.IN, Pin.PULL_UP)` with `.irq()`

### Assinaturas das Funções

```python
def read_dht22_sensor():
    # Ler o sensor DHT22 e retornar temperatura e humidade em graus Celsius e porcentagem
    pass

def convert_adc_to_luminosity(adc_value):
    # Converter valor ADC (0..65535) para porcentagem de luminosidade
    pass

def set_pwm_servo_duty(duty_u16):
    # Configurar o duty cycle do PWM para controlar o servo
    pass

def update_display(temp_c, hum, led_color):
    # Atualizar o display OLED com a temperatura, humidade e cor do LED
    pass

def handle_led_color(temp_c, hum):
    # Determinar a cor do LED com base nas condições de temperatura e humidade
    pass

def main():
    # Loop principal não-bloqueante para ler sensor, atualizar display e controlar LED
    pass
```

### Fluxo do Loop Principal

```python
last_dht_read = time.ticks_ms()
last_oled_update = time.ticks_ms()

while True:
    if time.ticks_diff(time.ticks_ms(), last_dht_read) >= 2000:
        try:
            temp_c, hum = read_dht22_sensor()
        except OSError as e:
            print("ERRO SENSOR")
            continue

        last_dht_read = time.ticks_ms()

    if time.ticks_diff(time.ticks_ms(), last_oled_update) >= 1000:
        led_color = handle_led_color(temp_c, hum)
        update_display(temp_c, hum, led_color)

        # Sinalização visual via LED RGB
        set_pwm_servo_duty(5000)  # Example duty cycle for servo control

        # Telemetria via Console Serial
        telemetry = {
            "temp": temp_c,
            "hum": hum,
            "led_color": led_color
        }
        print(json.dumps(telemetry))

        last_oled_update = time.ticks_ms()
```

### Conexões I2C

- **SDA**: `Pin(4)`
- **SCL**: `Pin(5)`