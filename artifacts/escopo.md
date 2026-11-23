### Documento de Escopo Técnico

#### Plataforma Alvo:
- Raspberry Pi Pico (RP2040)
- MicroPython SDK

#### Artefatos de Saída:
1. **Código-fonte completo em MicroPython** (`main.py` e `driver/ssd1306.py`):
   - Modularizado e comentado no padrão PEP-8.
   - Não-bloqueante, usando temporizadores não-bloqueantes com `time.ticks_ms()` e `time.ticks_diff()`.
   - Sem dependências externas não nativas.

2. **Arquivo diagram.json válido para o Wokwi Pi Pico**:
   - Contendo todas as conexões de hardware mapeadas, pronto para execução imediata sem sobreposição de componentes.

3. **Mapa de Hardware e Pinagem Obrigatória (Pinout RP2040)**:
   - Listando todos os componentes e pinos solicitados no pedido.

#### Componentes Solicitados:
- Sensor DHT22 (wokwi-dht22)
  - Função: Leitura de Temperatura (°C) e Umidade (%).
  - Interface: Digital (1-Wire).
  - Pinos Obrigatórios:
    - VCC -> 3V3
    - GND -> GND.1
    - SDA -> GP15

- Display OLED SSD1306 (board-ssd1306)
  - Função: Exibição do cabeçalho e leituras locais.
  - Interface: I2C0 (addr 0x3c).
  - Pinos Obrigatórios:
    - VCC -> 3V3
    - GND -> GND.2
    - SDA -> GP4
    - SCL -> GP5

- LED RGB Cátodo Comum (wokwi-rgb-led)
  - Função: Sinalização visual por faixas de temperatura e umidade.
  - Interface: Digital Out.
  - Pinos Obrigatórios:
    - COM -> GND.3 (atributo "common": "cathode")
    - R -> GP16
    - G -> GP17
    - B -> GP18

#### Requisitos Funcionais (RF):
1. **RF01 – Aquisição de Dados do DHT22**:
   - Ler o sensor DHT22 conectado ao GP15 a cada 2.000 ms.

2. **RF02 – Interface Gráfica no Display OLED I2C (GP4/GP5)**:
   - Atualizar o display OLED SSD1306 a cada 1.000 ms sem causar cintilação excessiva.
   - Layout de tela:
     * Linha 1: "MBA-FIAP" centralizado ou alinhado no topo (y=0), divisória horizontal (y=12).
     * Linha 2: "Temp: XX.X C".
     * Linha 3: "Umid: XX.X %".

3. **RF03 – Sinalização Visual via LED RGB (GP16, GP17, GP18)**:
   - Acionar os canais R, G e B em lógica ativa alta conforme a combinação de Temperatura e Umidade.

4. **RF04 – Telemetria via Console Serial (USB/UART)**:
   - Imprimir no console serial uma linha JSON compacta contendo o estado atual.

#### Requisitos Não Funcionais (RNF):
1. **RNF01 – Arquitetura Não-Bloqueante**:
   - Proibido o uso de `time.sleep()` longo no loop principal.
   - Escalonamento controlado por temporizadores não-bloqueantes.

2. **RNF02 – Tratamento de Falha de Sensor**:
   - Exibir "ERRO SENSOR" nas linhas inferiores do OLED e acender LED RGB na cor Magenta se a leitura falhar.
   - Registrar `temp": null, "hum": null` no console serial.

3. **RNF03 – Fidelidade do diagram.json**:
   - Usar obrigatoriamente os tipos especificados para componentes e pinos.

#### Restrições de Plataforma:
- Linguagem: MicroPython nativo para Raspberry Pi Pico (RP2040).
- Sempre incluir imports usados: `import machine`, `from machine import Pin, I2C`, `import time`, `import json`.
- Se houver DHT22/DHT11: instanciar obrigatoriamente no escopo global com prefixo do módulo `dht.DHT22(Pin(15))` e ler com `.measure()`, `.temperature()` e `.humidity()`.
- Se houver OLED SSD1306: usar `from ssd1306 import SSD1306_I2C` e inicializar o I2C informando o ID do barramento 0.
- Instanciar TODOS os periféricos no escopo global (fora de qualquer função).
- Para LED RGB: use 3 pinos separados (`led_r = Pin(16, Pin.OUT)`, `led_g = Pin(17, Pin.OUT)`, `led_b = Pin(18, Pin.OUT)`).
- NUNCA passe tupla para Pin().
- Inicialize todas as variáveis de telemetria antes do loop while True para evitar UnboundLocalError.
- Use contadores não-bloqueantes com offset (`last_dht = time.ticks_ms() - 2000`, `last_oled = time.ticks_ms() - 1000`) com `time.ticks_diff()` e `time.sleep_ms(50)` no fim do loop.
- Proibir importar `Adafruit_*`, `board`, `digitalio` ou `wokwi_gpio`.

#### Placa Alvo (`wokwi-pi-pico`) e Mapa de Hardware:
1. **Placa alvo**:
   - Raspberry Pi Pico (RP2040)

2. **Mapa de Hardware**:
   ```
   Componente (Wokwi ID) | Função no Sistema | Interface | Pinos Obrigatórios no Pi Pico e Atributos
   ---------------------|-------------------|----------|-----------------------------------------
   wokwi-dht22          | DHT22 Sensor      | Digital  | VCC -> 3V3, GND -> GND.1, SDA -> GP15
   board-ssd1306        | OLED SSD1306     | I2C0    | VCC -> 3V3, GND -> GND.2, SDA -> GP4, SCL -> GP5
   wokwi-rgb-led         | RGB LED Cátodo Comum | Digital Out| COM -> GND.3 (attrs: {"common": "cathode"}), R -> GP16, G -> GP17, B -> GP18
   ```

#### Requisitos Funcionais Detalhados:
- **RF01 – Aquisição de Dados do DHT22**:
  - Ler o sensor DHT22 a cada 2.000 ms.

- **RF02 – Interface Gráfica no Display OLED I2C (GP4/GP5)**:
  - Atualizar o display OLED SSD1306 a cada 1.000 ms.
  - Layout de tela:
    * Linha 1: "MBA-FIAP" centralizado ou alinhado no topo (y=0), divisória horizontal (y=12).
    * Linha 2: "Temp: XX.X C".
    * Linha 3: "Umid: XX.X %".

- **RF03 – Sinalização Visual via LED RGB (GP16, GP17, GP18)**:
  - Acionar os canais R, G e B em lógica ativa alta conforme a combinação de Temperatura e Umidade.

- **RF04 – Telemetria via Console Serial (USB/UART)**:
  - Imprimir no console serial uma linha JSON compacta contendo o estado atual.

#### Requisitos Não Funcionais Detalhados:
1. **RNF01 – Arquitetura Não-Bloqueante**:
   - Escalonamento controlado por temporizadores não-bloqueantes (`last_dht = time.ticks_ms() - 2000`, `last_oled = time.ticks_ms() - 1000`) com `time.ticks_diff()` e `time.sleep_ms(50)` no fim do loop.

2. **RNF02 – Tratamento de Falha de Sensor**:
   - Exibir "ERRO SENSOR" nas linhas inferiores do OLED e acender LED RGB na cor Magenta se a leitura falhar.
   - Registrar `temp": null, "hum": null` no console serial.

3. **RNF03 – Fidelidade do diagram.json**:
   - Usar obrigatoriamente os tipos especificados para componentes e pinos.

#### Arquivo diagram.json (Exemplo):
```json
{
  "components": [
    {
      "id": "wokwi-dht22",
      "type": "sensor",
      "pins": ["GND.1", "SDA"]
    },
    {
      "id": "board-ssd1306",
      "type": "display",
      "pins": ["VCC", "GND.2", "SDA", "SCL"]
    },
    {
      "id": "wokwi-rgb-led",
      "type": "led",
      "pins": ["COM", "R", "G", "B"],
      "attributes": {"common": "cathode"}
    }
  ]
}
```

#### Código-fonte completo (`main.py`):
```python
import machine
from ssd1306 import SSD1306_I2C
import dht

# Configurando os pinos dos componentes
led_r = Pin(16, Pin.OUT)
led_g = Pin(17, Pin.OUT)
led_b = Pin(18, Pin.OUT)

scl = Pin(5)
sda = Pin(4)
i2c = I2C(0, scl=scl, sda=sda, freq=400000)

dht_sensor = dht.DHT22(Pin(15))

# Inicializando o display OLED
display = SSD1306_I2C(128, 64, i2c)

# Variáveis de telemetria
temp = None
hum = None
cor_atual = 'OFF'

# Contadores não-bloqueantes
last_dht = time.ticks_ms() - 2000
last_oled = time.ticks_ms() - 1000

while True:
    # Verificando a leitura do sensor DHT22
    if time.ticks_diff(time.ticks_ms(), last_dht) >= 2000:
        dht_sensor.measure()
        temp = dht_sensor.temperature()
        hum = dht_sensor.humidity()

        # Atualizando o display OLED
        display.fill(0)