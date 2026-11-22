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