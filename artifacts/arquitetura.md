### Mapeamento de Objetos MicroPython

- **DHT22 Sensor**: `dht.DHT22(Pin(15))`
- **ADCs**:
  - Luminosidade: `ADC(Pin(26))` -> Convertido para % luminosidade (0..65535)
  - Setpoint de temperatura: `ADC(Pin(27))` -> Convertido para setpoint (15°C..40°C)
- **I2C**: `I2C(0, sda=Pin(4), scl=Pin(5))`
- **SSD1306 OLED Display**: `SSD1306_I2C(128, 64, i2c)`
- **LEDs**:
  - Verde: `Pin(16, Pin.OUT)`
  - Vermelho: `Pin(18, Pin.OUT)`
- **PWMs**:
  - LED Amarelo: `PWM(Pin(17))`
  - Servo Motor: `PWM(Pin(13))`

### Assinaturas das Funções

1. **Leitura de Sensores e Conversões**:
   ```python
   def read_dht22():
       # Ler temperatura e umidade do DHT22
       dht_sensor.measure()
       temperature = dht_sensor.temperature()  # °C
       humidity = dht_sensor.humidity()        # %
       return temperature, humidity

   def convert_luminosity_to_percent(luminance):
       # Converter valor ADC para porcentagem de luminosidade (0..65535)
       return int((luminance / 65535) * 100)

   def convert_temperature_to_setpoint(temperature):
       # Converter temperatura para setpoint (15°C..40°C)
       return int((temperature - 15) / (40 - 15)) * 65535
   ```

2. **Controle Proporcional de Ventilação**:
   ```python
   def control_servo(temperature, setpoint):
       # Comparar temperatura atual com o setpoint
       if temperature <= setpoint:
           servo.duty_u16(0)  # Servo fechado em 0°
       else:
           duty = int((temperature - setpoint) / (5.0)) * 65535
           servo.duty_u16(duty)  # Abrir a janela proporcionalmente
   ```

3. **Controle PWM de Iluminação Auxiliar**:
   ```python
   def control_led_amarelo(luminosity):
       # Ajustar o brilho via PWM inversamente proporcional à luminosidade
       if luminosity < 40:
           led_amarelo.duty_u16(65535 - luminosity)  # Acionar iluminação auxiliar
       else:
           led_amarelo.duty_u16(0)  # Desligar iluminação auxiliar
   ```

4. **Sinalização de Estado e Alarme Crítico**:
   ```python
   def update_leds(temperature, setpoint):
       if temperature <= setpoint:
           led_verde.value(1)  # LED Verde ligado
           led_vermelho.value(0)  # LED Vermelho desligado
       else:
           led_verde.value(0)  # LED Verde desligado
           led_vermelho.value(1)  # LED Vermelho ligado

   def handle_dht22_error():
       dht_sensor.measure()
       temperature = None
       humidity = None
       print("ERRO DHT22")
       oled.fill(0)
       oled.text("ERRO DHT22", 0, 0)
       oled.show()
       led_vermelho.value(1)  # Piscar LED Vermelho
   ```

5. **Fluxo do Loop Principal Não-Bloqueante**:
   ```python
   import time

   while True:
       current_time = time.ticks_ms()

       if time.ticks_diff(current_time, last_dht22_read) >= 2000:
           temperature, humidity = read_dht22()
           last_dht22_read = current_time

       if time.ticks_diff(current_time, last_adc_read) >= 500:
           luminosity = convert_luminosity_to_percent(adc_luminosity.read_u16())
           setpoint = convert_temperature_to_setpoint(adc_setpoint.read_u16())
           last_adc_read = current_time

       if time.ticks_diff(current_time, last_oled_update) >= 500:
           update_leds(temperature, setpoint)
           oled.fill(0)
           oled.text(f"Temp: {temperature:.2f}°C", 0, 0)
           oled.text(f"Hum: {humidity:.2f}% ", 0, 16)
           oled.show()
           last_oled_update = current_time

       if time.ticks_diff(current_time, last_button_read) >= 500:
           button_state = button.value()
           last_button_read = current_time
           # Implementar lógica para alternar entre telas Operação e Diagnóstico

       if time.ticks_diff(current_time, last_serial_print) >= 2000:
           json_data = {
               "temp": temperature,
               "humidity": humidity,
               "luminosity": luminosity,
               "setpoint": setpoint
           }
           print(json.dumps(json_data))
           last_serial_print = current_time

       # Tratar falhas de sensor e atualizar o display conforme necessário
   ```

Este mapeamento e assinaturas fornecem uma estrutura clara para implementar o projeto, garantindo que todos os requisitos sejam cumpridos.