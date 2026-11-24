### Especificação Técnica

#### Imports Obrigatórios
```python
import machine
from machine import Pin, I2C
import time
from ssd1306 import SSD1306_I2C
import dht
```

#### Inicialização dos Periféricos
```python
i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=400000)
oled = SSD1306_I2C(128, 64, i2c)
dht_sensor = dht.DHT22(Pin(15))
led_r = Pin(16, Pin.OUT)
led_g = Pin(17, Pin.OUT)
led_b = Pin(18, Pin.OUT)
```

#### Assinaturas das Funções
```python
def update_led_color(temp: float, hum: float) -> None:
    pass

def display_interface(temp: float, hum: float) -> None:
    pass

def main() -> None:
    pass
```

#### Estrutura do Loop Principal
```python
last_dht = time.ticks_ms() - 2000
last_oled = time.ticks_ms() - 1000

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
```

### Descrição das Funções

#### `update_led_color(temp: float, hum: float) -> None`
- **Parâmetros**:
  - `temp`: Temperatura lida do sensor DHT22 (float).
  - `hum`: Umidade lida do sensor DHT22 (float).
- **Função**:
  - Atualiza a cor do LED RGB com base nos valores de temperatura e umidade.
  - As cores possíveis são: Vermelho, Azul, Verde e Amarelo.

#### `display_interface(temp: float, hum: float) -> None`
- **Parâmetros**:
  - `temp`: Temperatura lida do sensor DHT22 (float).
  - `hum`: Umidade lida do sensor DHT22 (float).
- **Função**:
  - Atualiza a interface gráfica no OLED SSD1306 com os valores de temperatura e umidade.
  - Exibe "ERRO SENSOR" nas linhas inferiores se ocorrer uma falha na leitura do sensor.

#### `main() -> None`
- **Função**:
  - Função principal que controla o loop principal do programa.
  - Utiliza temporizadores não-bloqueantes com `time.ticks_ms()` e `time.ticks_diff()` para atualizar a leitura do DHT22, a interface gráfica no OLED e a cor do LED RGB em intervalos específicos.