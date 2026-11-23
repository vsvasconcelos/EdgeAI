### Documento de Escopo: Monitor Ambiental Simplificado (Raspberry Pi Pico)

#### Plataforma Alvo:
- Raspberry Pi Pico (RP2040)
- Linguagem / SDK: MicroPython

#### Artefatos de Saída:

1. **Código-fonte completo, modularizado e comentado no padrão PEP-8**:
   - `main.py`: Implementação principal do agente.
   - `driver/ssd1306.py`: Módulo separado para a classe SSD1306_I2C.

2. **Arquivo diagram.json válido para o Wokwi Pi Pico**:
   - Contém todas as conexões de hardware mapeadas conforme especificado no pedido, pronto para execução imediata sem sobreposição de componentes.

3. **Mapa de Hardware e Pinagem Obrigatória (Pinout RP2040)**:
   - Lista dos componentes e pinos solicitados no pedido.

#### Componentes Solicitados:

- **Sensor DHT22 (wokwi-dht22)**:
  - Função: Leitura de Temperatura (°C) e Umidade (%).
  - Interface: Digital (1-Wire).
  - Pinos Obrigatórios:
    - VCC -> 3V3
    - GND -> GND.1
    - SDA -> GP15

- **Display OLED SSD1306 (board-ssd1306)**:
  - Função: Exibição do cabeçalho e leituras locais.
  - Interface: I2C0 (addr 0x3c).
  - Pinos Obrigatórios:
    - VCC -> 3V3
    - GND -> GND.2
    - SDA -> GP4
    - SCL -> GP5

- **LED RGB Cátodo Comum (wokwi-rgb-led)**:
  - Função: Sinalização visual por faixas de temperatura e umidade.
  - Interface: Digital Out.
  - Pinos Obrigatórios:
    - COM -> GND.3 (atributo "common": "cathode")
    - R -> GP16
    - G -> GP17
    - B -> GP18

#### Requisitos Funcionais (RF):

- **RF01 – Aquisição de Dados do DHT22**:
  - Ler o sensor DHT22 conectado ao GP15 a cada 2.000 ms.

- **RF02 – Interface Gráfica no Display OLED I2C (GP4/GP5)**:
  - Atualizar o display OLED SSD1306 a cada 1.000 ms.
  - Layout de tela:
    * Linha 1: "MBA-FIAP" centralizado ou alinhado no topo, divisória horizontal.
    * Linha 2: "Temp: XX.X C".
    * Linha 3: "Umid: XX.X %".

- **RF03 – Sinalização Visual via LED RGB (GP16, GP17, GP18)**:
  - Acionar os canais R, G e B em lógica ativa alta conforme a combinação de Temperatura e Umidade.
  - Prioridades:
    1. Alerta Crítico / Desconforto Severo (Vermelho).
    2. Ambiente Frio / Úmido (Azul).
    3. Faixa de Conforto Ideal (Verde).
    4. Faixa de Atenção Moderada (Amarelo).

- **RF04 – Telemetria via Console Serial (USB/UART)**:
  - Imprimir no console serial a cada 2.000 ms, uma linha JSON contendo o estado atual.

#### Requisitos Não Funcionais (RNF):

- **RNF01 – Arquitetura Não-Bloqueante**:
  - Proibido usar `time.sleep()` longo no loop principal.
  - Escalonamento controlado por temporizadores não-bloqueantes com `time.ticks_ms()`, `time.ticks_diff()`.

- **RNF02 – Tratamento de Falha de Sensor**:
  - Exibir "ERRO SENSOR" nas linhas inferiores do OLED.
  - Acender LED RGB na cor Magenta (R=1, G=0, B=1).
  - Registrar `{"temp": null, "hum": null}` no console serial.

- **RNF03 – Fidelidade do diagram.json**:
  - Usar obrigatoriamente os tipos "wokwi-pi-pico", "wokwi-dht22", "board-ssd1306", "wokwi-rgb-led" (com "attrs": {"common": "cathode"}) e três "wokwi-resistor".
  - Pinos de alimentação (3V3 e GND) explicitamente conectados.

#### Restrições de Plataforma:
- Linguagem: MicroPython nativo para Raspberry Pi Pico (RP2040).
- Proibir uso de `Adafruit_*`, `board`, `digitalio` ou `wokwi_gpio`.

---

**Placa alvo (`wokwi-pi-pico`) e Mapa de Hardware**:
- Componentes: Sensor DHT22, Display OLED SSD1306, LED RGB Cátodo Comum.
- Pinos: GP15 (DHT22), GP4 (SDA), GP5 (SCL) para OLED, GND.1, GND.2, GND.3 para alimentação e comum do LED RGB.

**Requisitos Funcionais detalhados**:
- Intervalo de leitura DHT22: 2000 ms.
- Intervalo de atualização display OLED: 1000 ms.
- Layout de tela no display OLED:
  * Linha 1: "MBA-FIAP" centralizado, divisória horizontal.
  * Linha 2: "Temp: XX.X C".
  * Linha 3: "Umid: XX.X %".

**Requisitos Não Funcionais e Tratamento de Falhas**:
- Arquitetura não-bloqueante usando `time.ticks_ms()` e `time.sleep_ms(50)`.
- Exibir "ERRO SENSOR" nas linhas inferiores do OLED.
- Acender LED RGB na cor Magenta (R=1, G=0, B=1).
- Registrar `{"temp": null, "hum": null}` no console serial.

---

**Imports necessários**:
```python
import machine
from machine import Pin, I2C
import time
import json

# Importar DHT22 se necessário
# from dht import DHT22
```

Este documento de escopo detalha todas as especificações e requisitos solicitados para o projeto utilizando a plataforma Wokwi com o Raspberry Pi Pico (RP2040) e MicroPython, garantindo que todos os componentes e pinos solicitados estejam explicitamente mencionados.