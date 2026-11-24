import dht
import time
import machine

dht_sensor = dht.DHT22(Pin(15))

last_dht = time.ticks_ms() - 2000
last_oled = time.ticks_ms() - 1000
temp = None
hum = None
while True:
    current_time = time.ticks_ms()
    # Atualizar leitura do DHT22
    if time.ticks_diff(current_time, last_dht) >= 2000:
        try:
            dht_sensor.measure()
            temp = dht_sensor.temperature()
            hum = dht_sensor.humidity()
        except OSError:
            temp = None
            hum = None
        last_dht = current_time
    # Atualizar interface gráfica no OLED
    if time.ticks_diff(current_time, last_oled) >= 1000:
        display_interface(temp, hum)
        last_oled = current_time
    # Atualizar cor do LED RGB
    update_led_color(temp, hum)
    # Telemetria via console serial
    print(f'{"temp":<8} {"hum":<8} {"cor_atual":<10}')
    time.sleep_ms(50)