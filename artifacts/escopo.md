### Documento de Escopo Técnico

#### Plataforma Alvo:
- Raspberry Pi Pico (RP2040)
- MicroPython

#### Artefatos de Saída:

1. **Código-fonte completo em MicroPython** (`main.py` e `driver/ssd1306.py`):
   - Modularizado e comentado no padrão PEP-8.
   - Não-bloqueante, usando temporizadores não-bloqueantes com `time.ticks_ms()` e `time.ticks_diff()`.
   - Sem dependências externas não nativas.

2. **Arquivo diagram.json válido para o Wokwi Pi Pico**:
   - Contendo todas as conexões de hardware mapeadas, pronto para execução imediata sem sobreposição de componentes.
   - Fidelidade ao diagram.json: Usando obrigatoriamente os tipos "wokwi-pi-pico", "wokwi-dht22", "board-ssd1306", "wokwi-rgb-led" (com "attrs": {"common": "cathode"}) e três "wokwi-resistor" ("value": "220").
   - Pinos de alimentação (3V3 e GND) explicitamente conectados.

#### Mapa de Hardware e Pinagem Obrigatória:

| Componente (Wokwi ID) | Função no Sistema | Interface | Pinos Obrigatórios no Pi Pico e Atributos |
|-----------------------|-------------------|----------|----------------------------------------|
| wokwi-dht22          | Leitura de Temperatura (°C) e Umidade (%) | Digital (1-Wire) | VCC -> 3V3, GND -> GND.1, SDA -> GP15 |
| board-ssd1306        | Exibição do cabeçalho e leituras locais | I2C0 (addr 0x3c) | VCC -> 3V3, GND -> GND.2, SDA -> GP4, SCL -> GP5 |
| wokwi-rgb-led        | Sinalização visual por faixas de temperatura e umidade | Digital Out | COM -> GND.3 (atributo "common": "cathode"), R -> GP16 (via resistor 220 ohms), G -> GP17 (via resistor 220 ohms), B -> GP18 (via resistor 220 ohms) |

#### Requisitos Funcionais:

1. **RF01 – Aquisição de Dados do DHT22**:
   - Ler o sensor DHT22 conectado ao GP15 a cada 2.000 ms.

2. **RF02 – Interface Gráfica no Display OLED I2C (GP4/GP5)**:
   - Atualizar o display OLED SSD1306 (128x64 pixels, endereço I2C 0x3c) a cada 1.000 ms.
   - Layout de tela:
     * Linha 1: "MBA-FIAP" centralizado ou alinhado no topo (y=0), linha horizontal divisória (y=12).
     * Linha 2: "Temp: XX.X C" (y=24).
     * Linha 3: "Umid: XX.X %" (y=42).

3. **RF03 – Sinalização Visual via LED RGB (GP16, GP17, GP18)**:
   - Acionar os canais R, G e B em lógica ativa alta conforme a combinação de Temperatura (T) e Umidade (U), obedecendo à seguinte ordem de prioridade:
     1. Alerta Crítico / Desconforto Severo: Cor Vermelha -> R=1, G=0, B=0.
     2. Ambiente Frio / Úmido: Cor Azul -> R=0, G=0, B=1.
     3. Faixa de Conforto Ideal: Cor Verde -> R=0, G=1, B=0.
     4. Faixa de Atenção Moderada: Cor Amarela -> R=1, G=1, B=0.

4. **RF04 – Telemetria via Console Serial (USB/UART)**:
   - Imprimir no console serial do Wokwi a cada 2.000 ms, uma linha JSON compacta contendo o estado atual: `{"temp": XX.X, "hum": XX.X, "led_color": "COLOR"}`.

#### Requisitos Não Funcionais:

1. **RNF01 – Arquitetura Não-Bloqueante**:
   - Proibido o uso de `time.sleep()` longo no loop principal.
   - Escalonamento da leitura do DHT22 (2.000 ms) e atualização do display OLED (1.000 ms) controlado por temporizadores não-bloqueantes utilizando `time.ticks_ms()` e `time.ticks_diff()`.

2. **RNF02 – Tratamento de Falha de Sensor**:
   - Caso a leitura do DHT22 lance exceção (`OSError`), o sistema deve exibir "ERRO SENSOR" nas linhas inferiores do OLED (mantendo o cabeçalho "MBA-FIAP"), acender o LED RGB na cor Magenta (R=1, G=0, B=1) e registrar `{"temp": null, "hum": null}` no console serial.

3. **RNF03 – Fidelidade do diagram.json**:
   - O arquivo diagram.json gerado pelo agente deve usar obrigatoriamente os tipos "wokwi-pi-pico", "wokwi-dht22", "board-ssd1306", "wokwi-rgb-led" (com "attrs": {"common": "cathode"}) e três "wokwi-resistor" ("value": "220").
   - Pinos de alimentação (3V3 e GND) explicitamente conectados.

#### Restrições de Plataforma:
- Linguagem: MicroPython nativo (`from machine import ...`, `import time`, `import json`).
- Se houver DHT22/DHT11 use `import dht` com `.measure()`, `.temperature()` e `.humidity()`.
- Se houver OLED SSD1306 use `from ssd1306 import SSD1306_I2C`.
- Use temporização não-bloqueante com `time.ticks_ms()` e `time.ticks_diff()`.
- Proibido importar `Adafruit_*`, `board`, `digitalio` ou `wokwi_gpio`.