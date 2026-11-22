# Cadeia de Raciocínio Multi-Agente

Execução: 22/11/2026 15:26:50
Modelo: `qwen2.5-coder:3b`

---

## 🎯 1. Gerente de Projetos (Escopo & Requisitos)

# Documento de Escopo Técnico

## 1. Estrutura do Projeto

### 1.1. Arquivos do Projeto

- **main.py**: Código principal que inicializa o sistema e controla os componentes.
- **config.json**: Configurações gerais do sistema, incluindo parâmetros de tempo e conversões ADC.
- **diagram.json**: Descrição dos pinos e conexões entre os componentes no Wokwi Pi Pico.

### 1.2. Código Fonte

O código deve ser modularizado, com funções separadas para cada tarefa principal (leitura de sensores, controle do servo, etc.). O código deve seguir o padrão PEP-8 e não usar `time.sleep()` longo no loop principal.

### 1.3. Diagram.json

O arquivo diagram.json deve incluir todas as conexões entre os componentes, especificando os pinos GPIO, ADCs, PWMs e I2Cs. O arquivo deve ser válido para o Wokwi Pi Pico e não deve conter resistores limitadores de corrente nos LEDs.

## 2. Requisitos Funcionais

### 2.1. Aquisição de Sensores e Escalonamento

- **Sensor DHT22 (GP15)**: Ler a temperatura (°C) e umidade (%) a cada 2000 ms.
- **Fotoresistor / LDR (GP26)**: Ler a luminosidade (0% a 100%) a cada 200 ms, convertendo para o intervalo de 0 a 65535.
- **Potenciômetro (GP27)**: Ler o setpoint de temperatura (15°C a 40°C) a cada 200 ms, convertendo para o intervalo de 0 a 65535.

### 2.2. Controle Proporcional de Ventilação

- **Servo Motor (GP13)**: Comparar a temperatura atual com o setpoint:
  - Se T_atual <= T_set: Servo fechado em 0°.
  - Se T_atual > T_set: Abrir a janela proporcionalmente entre 0° e 90°, atingindo abertura máxima (90°) quando T_atual >= T_set + 5.0°C.

### 2.3. Controle PWM de Iluminação Auxiliar

- **LED Amarelo (GP17)**: Ajustar o brilho via PWM inversamente proporcional à luminosidade, acionando iluminação auxiliar quando a luminosidade cair abaixo de 40%.

### 2.4. Sinalização de Estado e Alarme Crítico

- **LED Verde (GP16)**: Indicador de sistema operando em faixa normal.
- **LED Vermelho (GP18)**: Alerta de baixa luminosidade e alarme crítico.

### 2.5. Interface Gráfica no Display OLED I2C

- Atualizar o display a cada 500 ms sem causar cintilação.
- O botão no GP14 deve alternar entre duas telas: Operação e Diagnóstico.

### 2.6. Telemetria Estruturada via Serial

- Imprimir no console serial do Wokwi a cada 2 segundos, uma linha JSON contendo o estado completo do nó.

## 3. Requisitos Não Funcionais

### 3.1. Arquitetura Não-Bloqueante

- Proibir o uso de `time.sleep()` longo no loop principal.
- Escalonar a leitura do DHT22 (0.5 Hz), a leitura dos ADCs (5 Hz) e a atualização do OLED (2 Hz) por temporizadores não-bloqueantes.

### 3.2. Tratamento de Falha de Sensor

- Caso a leitura do DHT22 lance exceção (`OSError`), registrar "temp": null no JSON, exibir "ERRO DHT22" no OLED e piscar o LED Vermelho.

### 3.3. Fidelidade do diagram.json

- O arquivo diagram.json deve conectar explicitamente GND e 3V3/VBUS de todos os periféricos.
- Incluir resistores limitadores de corrente nos LEDs.
- Usar os nomes exatos dos pinos do wokwi-pi-pico (GP4, GP5, GP13, GP14, GP15, GP16, GP17, GP18, GP26, GP27).

## 4. Entregáveis

- **Mapa de Hardware e Pinagem**: Exato no wokwi-pi-pico (GP4, GP5, GP13, GP14, GP15, GP16, GP17, GP18, GP26, GP27).
- **Requisitos Funcionais**: Amostragem, conversões ADC 0-65535, controle proporcional do Servo, PWM do LED, telas do OLED, IRQ do botão e telemetria JSON via Serial.
- **Critérios de Aceitação e Tratamento de Falhas**: OSError no DHT22.
- **Restrições de Plataforma**: MicroPython nativo (`machine`, `dht`, `time`, `json`, `ssd1306`). Proibir usar `Adafruit_DHT`, `board`, `digitalio` ou `wokwi_gpio`.

---

Este documento fornece uma estrutura clara e detalhada para o projeto, garantindo que todos os requisitos sejam cumpridos e que a arquitetura seja não-bloqueante.

---

## 🏗️ 2. Arquiteto de Sistemas (Design Técnico)

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

---

## 💻 3. Desenvolvedor Python (Código & Testes Inline)

```python
from machine import Pin, ADC, PWM, I2C
import dht
import time
import json
from ssd1306 import SSD1306_I2C

# Inicialização dos pinos
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
i2c = I2C(0, sda=Pin(4), scl=Pin(5))
oled = SSD1306_I2C(128, 64, i2c)

# Configuração inicial dos valores
temperature = 25.0
humidity = 50.0
setpoint = 25.0

# Variáveis para temporizadores
last_dht22_read = time.ticks_ms()
last_adc_read = time.ticks_ms()
last_oled_update = time.ticks_ms()
last_button_read = time.ticks_ms()
last_serial_print = time.ticks_ms()

# Função de tratamento de erro do DHT22
def handle_dht22_error():
    dht_sensor.measure()
    temperature = None
    humidity = None
    print("ERRO DHT22")
    oled.fill(0)
    oled.text("ERRO DHT22", 0, 0)
    oled.show()
    led_vermelho.value(1)  # Piscar LED Vermelho

# Função de atualização dos LEDs
def update_leds(temperature, setpoint):
    if temperature <= setpoint:
        led_verde.value(1)  # LED Verde ligado
        led_vermelho.value(0)  # LED Vermelho desligado
    else:
        led_verde.value(0)  # LED Verde desligado
        led_vermelho.value(1)  # LED Vermelho ligado

# Função de controle do servo
def control_servo(temperature, setpoint):
    if temperature <= setpoint:
        servo.duty_u16(0)  # Servo fechado em 0°
    else:
        duty = int((temperature - setpoint) / (5.0)) * 65535
        servo.duty_u16(duty)  # Abrir a janela proporcionalmente

# Função de controle da iluminação auxiliar
def control_led_amarelo(luminosity):
    if luminosity < 40:
        led_amarelo.duty_u16(65535 - luminosity)  # Acionar iluminação auxiliar
    else:
        led_amarelo.duty_u16(0)  # Desligar iluminação auxiliar

# Função de leitura do DHT22
def read_dht22():
    try:
        dht_sensor.measure()
        temperature = dht_sensor.temperature()  # °C
        humidity = dht_sensor.humidity()        # %
        return temperature, humidity
    except OSError:
        handle_dht22_error()

# Função de conversão da luminosidade para porcentagem
def convert_luminosity_to_percent(luminance):
    return int((luminance / 65535) * 100)

# Função de conversão da temperatura para setpoint
def convert_temperature_to_setpoint(temperature):
    return int((temperature - 15) / (40 - 15)) * 65535

# Função de tratamento do botão
def button_handler(pin):
    global tela_atual
    tela_atual = 1 - tela_atual

# Configuração da interrupção no botão
button.irq(trigger=Pin.IRQ_FALLING, handler=button_handler)

# Loop principal não-bloqueante
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
