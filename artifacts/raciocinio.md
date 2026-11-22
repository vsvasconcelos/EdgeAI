# Cadeia de Raciocínio Multi-Agente

Execução: 22/11/2026 14:59:22
Modelo: `qwen2.5-coder:3b`

---

## 🎯 1. Gerente de Projetos (Escopo & Requisitos)

# Documento de Escopo Técnico

## 1. Mapa de Hardware e Pinagem

### 1.1 Raspberry Pi Pico (GP4, GP5, GP13, GP14, GP15, GP16, GP17, GP18, GP26, GP27)

| **Pino** | **Nome**       | **Descrição**                                                                 |
|----------|----------------|--------------------------------------------------------------------------------|
| GP4      | SDA          | Conectado ao Display OLED SSD1306 (SDA)                                         |
| GP5      | SCL          | Conectado ao Display OLED SSD1306 (SCL)                                         |
| GP13     | PWM Servo   | Controle proporcional do servo motor, abertura de 0 a 90 graus se temp > setpoint |
| GP14     | IRQ Botão    | Interrupção e debounce para alternar tela Operação/Diagnóstico e telemetria JSON via Serial |
| GP15     | DHT22       | Sensor de temperatura e umidade, amostragem a cada 2000ms, tratando OSError |
| GP16     | LED Verde   | Normal                                                                 |
| GP17     | PWM LED Amarelo | Luz < 40%                                                                 |
| GP18     | LED Vermelho | Alarme/erro                                                               |
| GP26     | ADC LDR      | Sensor de luminosidade, amostragem a cada 500ms                             |
| GP27     | ADC Potenciômetro | Setpoint de temperatura, amostragem a cada 500ms                         |

## 2. Requisitos Funcionais

### 2.1 DHT22 (GP15)

- **Amostragem**: A cada 2000ms
- **Conversão ADC**: Não aplicável, pois é um sensor analogico
- **Tratamento de Erro**: Tratar OSError

### 2.2 Photoresistor LDR (GP26)

- **Amostragem**: A cada 500ms
- **Conversão ADC**: Convertendo o valor lido do ADC0 para uma porcentagem de luminosidade (0 a 100%)
- **Tratamento de Erro**: Não aplicável

### 2.3 Potenciômetro (GP27)

- **Amostragem**: A cada 500ms
- **Conversão ADC**: Convertendo o valor lido do ADC1 para uma temperatura em graus Celsius (15 a 40°C)
- **Tratamento de Erro**: Não aplicável

### 2.4 Display OLED SSD1306 (SDA=GP4, SCL=GP5)

- **Atualização**: A cada 500ms
- **Controle de Tela**: Alternar entre tela Operação e Diagnóstico

### 2.5 LED Verde (GP16)

- **Normal**: Ligado quando o sistema está operando normalmente

### 2.6 LED Amarelo PWM (GP17)

- **Luz < 40%**: Controlado por um valor de PWM
- **Tratamento de Erro**: Não aplicável

### 2.7 LED Vermelho (GP18)

- **Alarme/Erro**: Ligado quando ocorre um erro ou alarme

### 2.8 Servo Motor PWM (GP13)

- **Abertura Proporcional**: Controlado por um valor de PWM, abertura entre 0 e 90 graus se a temperatura for maior que o setpoint
- **Tratamento de Erro**: Não aplicável

### 2.9 Pushbutton (IRQ Botão) no GP14

- **Interrupção**: Detectar pressionamento do botão
- **Debounce**: Implementar debounce para evitar interrupções indesejadas
- **Alternância Tela**: Alternar entre tela Operação e Diagnóstico
- **Telemetria JSON via Serial**: Enviar dados de telemetria em formato JSON quando o botão é pressionado

## 3. Critérios de Aceitação e Tratamento de Falhas

### 3.1 DHT22 (GP15)

- **OSError**: Tratar OSError ao tentar ler os valores do sensor, exibindo uma mensagem de erro na tela OLED.

## 4. Restrições de Plataforma

- **MicroPython nativo (`machine`, `dht`, `time`, `json`, `ssd1306`). PROIBIDO usar `Adafruit_DHT`, `board`, `digitalio` ou `wokwi_gpio`.**

---

## 🏗️ 2. Arquiteto de Sistemas (Design Técnico)

### Mapeamento de Objetos MicroPython

```python
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
```

### Assinaturas das Funções e Fórmulas de Conversão

```python
def read_luminosity():
    # Convertendo o valor lido do ADC0 para uma porcentagem de luminosidade (0 a 100%)
    return int(ldr_adc.read_u16() * 100 / 65535)

def convert_temperature_to_pwm(temperature):
    # Abertura proporcional do servo motor, abertura entre 0 e 90 graus se a temperatura for maior que o setpoint
    if temperature > setpoint:
        return int((temperature - 15) * (90 / 25))
    else:
        return 0

def send_telemetry():
    # Enviar dados de telemetria em formato JSON quando o botão é pressionado
    data = {
        "temperature": dht_sensor.temperature,
        "humidity": dht_sensor.humidity,
        "luminosity": read_luminosity()
    }
    json_data = json.dumps(data)
    print(json_data)
```

### Fluxo do Loop Principal Não-Bloqueante

```python
def loop():
    while True:
        current_time = time.ticks_ms()

        # Lendo sensor DHT22
        try:
            dht_sensor.measure()
            temperature = dht_sensor.temperature
            humidity = dht_sensor.humidity
        except OSError as e:
            print("Erro ao ler sensor DHT22:", e)
            display.text("Erro DHT", 0, 0)

        # Lendo sensores ADC
        luminosity = read_luminosity()
        setpoint_temperature = potenciometro_adc.read_u16() * 15 / 65535

        # Controle do servo motor
        servo.duty_u16(convert_temperature_to_pwm(temperature))

        # Atualizando tela OLED SSD1306
        display.fill(0)
        display.text(f"Temp: {temperature:.2f}C", 0, 0)
        display.text(f"Hum: {humidity:.2f}%", 0, 8)
        display.text(f"Lum: {luminosity:.2f}%", 0, 16)
        display.show()

        # Verificando pressionamento do botão
        if button.value() == 0:
            send_telemetry()
            display.fill(0)
            display.text("Telemetria enviada", 0, 0)

        # Intervalo de amostragem
        time.sleep_ms(500)
```

Este é o esboço técnico para a arquitetura do firmware MicroPython no Wokwi.

---

## 💻 3. Desenvolvedor Python (Código & Testes Inline)

```python
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

def convert_temperature_to_pwm(temperature):
    # Abertura proporcional do servo motor, abertura entre 0 e 90 graus se a temperatura for maior que o setpoint
    if temperature > setpoint:
        return int((temperature - 15) * (90 / 25))
    else:
        return 0

def send_telemetry():
    # Enviar dados de telemetria em formato JSON quando o botão é pressionado
    data = {
        "temperature": dht_sensor.temperature,
        "humidity": dht_sensor.humidity,
        "luminosity": read_luminosity()
    }
    json_data = json.dumps(data)
    print(json_data)

def loop():
    while True:
        current_time = time.ticks_ms()

        # Lendo sensor DHT22
        try:
            dht_sensor.measure()
            temperature = dht_sensor.temperature
            humidity = dht_sensor.humidity
        except OSError as e:
            print("Erro ao ler sensor DHT22:", e)
            display.text("Erro DHT", 0, 0)

        # Lendo sensores ADC
        luminosity = read_luminosity()
        setpoint_temperature = potenciometro_adc.read_u16() * 15 / 65535

        # Controle do servo motor
        servo.duty_u16(convert_temperature_to_pwm(temperature))

        # Atualizando tela OLED SSD1306
        display.fill(0)
        display.text(f"Temp: {temperature:.2f}C", 0, 0)
        display.text(f"Hum: {humidity:.2f}%", 0, 8)
        display.text(f"Lum: {luminosity:.2f}%", 0, 16)
        display.show()

        # Verificando pressionamento do botão
        if button.value() == 0:
            send_telemetry()
            display.fill(0)
            display.text("Telemetria enviada", 0, 0)

        # Intervalo de amostragem
        time.sleep_ms(500)

# Inicialização das variáveis globais antes do loop principal
tela_atual = 0
ultimo_clique = 0
ultima_leitura = 0
ultima_oled = 0

# Loop principal
loop()
```
