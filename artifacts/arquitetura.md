1. Imports obrigatórios:
   ```python
   import machine
   from ssd1306 import SSD1306_I2C
   import dht
   ```

2. Inicialização dos periféricos e pinos:
   ```python
   led_r = Pin(16, Pin.OUT)
   led_g = Pin(17, Pin.OUT)
   led_b = Pin(18, Pin.OUT)

   scl = Pin(5)
   sda = Pin(4)
   i2c = I2C(0, scl=scl, sda=sda, freq=400000)

   dht_sensor = dht.DHT22(Pin(15))

   display = SSD1306_I2C(128, 64, i2c)
   ```

3. Estrutura de estado do loop principal:
   ```python
   while True:
       # Verificando a leitura do sensor DHT22
       if time.ticks_diff(time.ticks_ms(), last_dht) >= 2000:
           dht_sensor.measure()
           temp = dht_sensor.temperature()
           hum = dht_sensor.humidity()

           # Atualizando o display OLED
           display.fill(0)
   ```

4. Assinaturas das funções:
   ```python
   def update_display():
       display.fill(0)
       display.text("MBA-FIAP", 16, 0, 1)
       display.line(0, 12, 128, 12, 1)
       display.text(f"Temp: {temp:.1f} C", 16, 14, 1)
       display.text(f"Hum: {hum:.1f} %", 16, 30, 1)

   def update_led():
       if temp is not None and hum is not None:
           cor_atual = 'OFF'
           if temp > 25:
               cor_atual = 'RED'
           elif temp < 18:
               cor_atual = 'BLUE'
           elif hum > 60:
               cor_atual = 'GREEN'

           led_r.value(1 if cor_atual == 'RED' else 0)
           led_g.value(1 if cor_atual == 'GREEN' else 0)
           led_b.value(1 if cor_atual == 'BLUE' else 0)

   def handle_sensor_failure():
       display.fill(0)
       display.text("ERRO SENSOR", 16, 0, 1)
       display.line(0, 12, 128, 12, 1)
       led_r.value(1)
       led_g.value(1)
       led_b.value(1)

   def main():
       last_dht = time.ticks_ms() - 2000
       last_oled = time.ticks_ms() - 1000

       while True:
           if time.ticks_diff(time.ticks_ms(), last_dht) >= 2000:
               dht_sensor.measure()
               temp = dht_sensor.temperature()
               hum = dht_sensor.humidity()

               if temp is None or hum is None:
                   handle_sensor_failure()
               else:
                   update_display()
                   update_led()

           time.sleep_ms(50)
   ```

5. Estrutura de estado do loop principal com `time.ticks_diff()` e `time.sleep_ms()`: 
   ```python
   while True:
       if time.ticks_diff(time.ticks_ms(), last_dht) >= 2000:
           dht_sensor.measure()
           temp = dht_sensor.temperature()
           hum = dht_sensor.humidity()

           if temp is None or hum is None:
               handle_sensor_failure()
           else:
               update_display()
               update_led()

       time.sleep_ms(50)
   ```