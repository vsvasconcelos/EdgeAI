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