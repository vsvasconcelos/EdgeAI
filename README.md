# 🤖 EdgeAI — Sistema Multi-Agente Local
### Projeto desenvolvido para o curso: **I2A2 - Agentic AI: uma introdução**

![tela](Tela.png)   


> **Pipeline multi-agente linear sequencial e servidor MCP otimizados para execução local em hardware Edge AI (Restrito/Low-End).**

---

## 📋 Índice
1. [Sobre o Projeto](#-sobre-o-projeto)
2. [Arquitetura do Sistema](#%EF%B8%8F-arquitetura-do-sistema)
3. [Histórico Arquitetural: Do Loop Dinâmico ao Upgrade 1.5B → 3B](#-hist%C3%B3rico-arquitetural-do-loop-din%C3%A2mico-ao-upgrade-15b--3b)
4. [Hardware Alvo e Defesas Contra Bloat](#-hardware-alvo-e-defesas-contra-bloat)
5. [Estrutura do Projeto](#-estrutura-do-projeto)
6. [Instalação e Configuração](#-instala%C3%A7%C3%A3o-e-configura%C3%A7%C3%A3o)
7. [Principais Comandos do Ollama](#-principais-comandos-do-ollama)
8. [Como Executar](#-como-executar)
9. [Como Executar os Artefatos no Simulador Wokwi](#-como-executar-os-artefatos-no-simulador-wokwi)
10. [Integração com a IDE Zed](#-integra%C3%A7%C3%A3o-com-a-ide-zed)
11. [Matriz de Compatibilidade](#-matriz-de-compatibilidade)

---

## ℹ️ Sobre o Projeto

Projeto desenvolvido para o curso **I2A2 - Agentic AI: uma introdução**.

O **EdgeAI** é uma solução de engenharia de software projetada para rodar **sistemas multi-agentes de inteligência artificial de forma 100% local e offline**. Desenvolvido com foco no ecossistema local do **Ollama** e no modelo **Qwen2.5-Coder-3B** (`qwen2.5-coder:3b`), o projeto simula uma tripulação de engenharia de software (Gerente de Projetos, Arquiteto e Desenvolvedor) para gerar soluções de código documentadas, testadas e projetos completos de sistemas embarcados para o simulador **Wokwi (Raspberry Pi Pico / MicroPython)** sem precisar de chaves de API pagas ou conexões de rede externas.

Adicionalmente, o projeto inclui um servidor **MCP (Model Context Protocol)** para integração direta como uma ferramenta (tool) na interface de chat do agente da IDE **Zed**.


## Assista ao vídeo:
[![EdgeAI - Assistente de Código local](https://img.youtube.com/vi/1Rb6H7dSKRw/0.jpg)](https://www.youtube.com/watch?v=1Rb6H7dSKRw)  


---

## 🏗️ Arquitetura do Sistema

O fluxo de trabalho foi estruturado como um pipeline linear direto. Cada etapa é uma chamada direta (via LangChain / ChatOllama) que recebe apenas o resumo técnico purificado do agente anterior, mantendo a janela de contexto limpa e prevenindo crashs de memória.

```mermaid
graph TD
    U["👤 Usuário"] -->|Pedido de Software| GP["🎯 Gerente de Projetos (Define o Escopo)"]
    GP -->|Requisitos e Restrições| ARQ["🏗️ Arquiteto de Sistemas (Design Técnico)"]
    ARQ -->|Estrutura e Assinaturas| DEV["💻 Desenvolvedor Python (Código e Testes)"]
    DEV -->|Código Final e Testes Inline| R["📄 Gravação de Artefatos (pasta artifacts/)"]
```

### Personas dos Agentes

| Agente                         | Função no Pipeline                                                  | Diretriz do Prompt                                                                                     |
| :----------------------------- | :------------------------------------------------------------------ | :----------------------------------------------------------------------------------------------------- |
| **🎯 Gerente de Projetos (GP)** | Analisa o pedido do usuário e define os limites do projeto.         | Documento conciso: requisitos funcionais, critérios de aceitação e restrições.                         |
| **🏗️ Arquiteto de Sistemas**    | Cria o design técnico a partir do escopo do GP.                     | Assinaturas de funções, escolha do algoritmo e fluxo de dados (sem escrever código real).              |
| **💻 Desenvolvedor Python**     | Implementa o código Python completo baseado no design do Arquiteto. | Código limpo com type-hints, bloco `if __name__ == '__main__':` de teste e testes inline com veredito. |

---

## 🔄 Histórico Arquitetural: Do Loop Dinâmico ao Upgrade 1.5B → 3B

### Fase 1: O Pivô do Loop Dinâmico (CrewAI → Pipeline Sequencial Direto)
Originalmente, o projeto foi planejado utilizando o framework **CrewAI** com um processo hierárquico (`Process.hierarchical`) e loops dinâmicos de correção automática (se um teste inline falhasse, o GP enviaria o erro de volta ao Arquiteto/Desenvolvedor para retificar).

Durante os testes práticos no hardware restrito, foram identificados **três problemas críticos** ao usar modelos de pequeno porte (SLMs):
1. **Falha Sistemática no Protocolo ReAct**: Modelos de até 3B parâmetros não conseguem seguir de forma consistente a lógica *Thought → Action → Observation* exigida pelo motor de agentes do CrewAI, resultando em erros de parser JSON ou loops intermináveis de execução (travados por até 27 minutos).
2. **Context Bloat (Inchaço de Contexto)**: O vai-e-vem dos loops dinâmicos acumulava o histórico no buffer do modelo, estourando rapidamente o limite físico de **4096 tokens**.
3. **VRAM Spillover**: O estouro do contexto forçava o transbordo da memória da GPU de 2GB para a memória RAM (CPU), paralisando o sistema.

**Solução da Fase 1:**
A orquestração complexa do CrewAI foi substituída por um **pipeline sequencial direto via LangChain (`llm.invoke()`)**. Ao invés de manter um chat contínuo volumoso, o pipeline extrai e envia apenas o output final útil de cada etapa.

### Fase 2: Evolução do Modelo (`qwen2.5-coder:1.5b` → `qwen2.5-coder:3b`) e Adequação para o Wokwi
Ao submeter especificações complexas de sistemas embarcados IoT para a plataforma **Wokwi (Raspberry Pi Pico / MicroPython)** (ex.: execução registrada em `artifacts/run_20261122_120216`), o modelo inicial `qwen2.5-coder:1.5b` (986 MB) apresentou limitações severas de domínio:
1. **Alucinação de Bibliotecas Incompatíveis**: O modelo `1.5b` misturava bibliotecas de Linux embarcado/CPython (`import Adafruit_DHT`, `import Adafruit_ADS1x15`, `import Adafruit_SSD1306`), CircuitPython (`board`, `digitalio`, `analogio`) e módulos fictícios (`from wokwi_gpio import Pin, PWMOut`), que **não existem no firmware MicroPython do Raspberry Pi Pico no Wokwi**.
2. **Quebra do Schema Oficial do `diagram.json`**: Em vez de gerar a estrutura exigida pelo simulador Wokwi (`"version": 1`, `"parts": [...]`, `"connections": [...]`), o modelo `1.5b` gerava um JSON meramente descritivo (`{"components": [...]}`), que o Wokwi não consegue renderizar.
3. **Conflito de Prompts Genéricos**: Os prompts originais de `app_agente.py` continham instruções fixas para algoritmos Python de console (`"Python puro, stdlib apenas"`, `"Máximo 150 palavras"`), suprimindo detalhes críticos de pinagem GPIO, ADC de 16 bits (`0..65535`), PWM e interrupções (IRQ).

**Solução Implementada na Fase 2:**
*   **Upgrade para o modelo imediatamente superior (`qwen2.5-coder:3b`)**: Com ~1.9 GB (quantização `Q4_K_M`), o modelo de 3 bilhões de parâmetros cabe no orçamento de memória do hardware alvo (2 GB VRAM + offload híbrido em RAM) e apresenta fidelidade significativamente superior a restrições de API e estruturação de código. A versão `1.5b` foi desinstalada para liberar armazenamento local.
*   **Roteamento Inteligente de Pipeline para Wokwi (`eh_pedido_wokwi`)**: O `app_agente.py` detecta automaticamente pedidos voltados ao Wokwi/MicroPython e aciona prompts especializados que exigem **exclusivamente** as APIs nativas do MicroPython (`from machine import Pin, ADC, PWM, I2C`, `import dht`, `import time`, `import json` e `from ssd1306 import SSD1306_I2C`), proibindo explicitamente bibliotecas `Adafruit_*`, `board` ou `wokwi_gpio`.
*   **Empacotamento Completo de Artefatos Wokwi**: O `salvar_artefatos()` passou a gerar e validar automaticamente os arquivos prontos para simulação (`main.py`, `diagram.json` no schema oficial do Wokwi com `parts` e `connections`, driver `ssd1306.py` e `wokwi.toml`).

---

## 💻 Hardware Alvo e Defesas Contra Bloat

O sistema foi otimizado para o seguinte perfil de máquina edge:

*   **Processador**: CPU x86_64 de 8 núcleos
*   **Memória RAM**: 8 GB totais (~4.2 GB disponíveis de uso livre)
*   **GPU Dedicada**: NVIDIA GeForce MX110 (2 GB VRAM)
*   **Sistema Operacional**: Ubuntu Linux

### Estratégias de Mitigação
Para rodar com estabilidade sem estourar o limite físico de hardware:

*   **Janela de Contexto Travada (`num_ctx=4096`)**: Impede o crescimento desordenado do cache KV na VRAM de 2GB.
*   **Limite Estrito de Geração (`num_predict=1500`)**: Evita respostas excessivamente longas ou loops recursivos infinitos do LLM.
*   **Temperatura Baixa (`temperature=0.1`)**: Prioriza a previsibilidade e a consistência das respostas de codificação.
*   **Controle de CPU/Thread (`num_thread=6`)**: Limita a execução do Ollama em 6 núcleos da CPU, garantindo que o sistema operacional permaneça responsivo (evita starvation).

---

## 📁 Estrutura do Projeto

```
EdgeAI/
├── app_agente.py             # Script principal: Pipeline multi-agente direto via LLM
├── mcp_server.py             # Servidor MCP para integração com o chat do Zed Agent
├── ollama.sh                 # Wrapper Bash para gerenciar e executar o Ollama localmente
├── requirements.txt          # Declaração das dependências do ecossistema Python
├── zed_tasks.json            # Configuração de Tasks customizadas para a IDE Zed
├── slm.py                    # Script de validação simples de inferência da API REST
├── edgeai_sistema_multiagente.md  # Detalhamento técnico da arquitetura multi-agente
├── relatorio_ollama_qwen.md   # Relatório técnico completo do setup local
├── artifacts/                # Diretório onde os artefatos das runs são salvos
│   ├── run_[timestamp]/      # Histórico individual de cada execução
│   │   ├── escopo.md
│   │   ├── arquitetura.md
│   │   ├── codigo.py
│   │   ├── main.py           # (Modo Wokwi) Código MicroPython principal
│   │   ├── diagram.json      # (Modo Wokwi) Circuito no schema oficial do Wokwi
│   │   ├── ssd1306.py        # (Modo Wokwi) Driver MicroPython para display OLED
│   │   ├── wokwi.toml        # (Modo Wokwi) Configuração para extensão Wokwi VS Code
│   │   └── raciocinio.md
│   ├── escopo.md             # Cópia do último escopo gerado (latest)
│   ├── arquitetura.md        # Cópia da última arquitetura gerada (latest)
│   ├── codigo.py             # Cópia do último código gerado (latest)
│   ├── main.py               # (Modo Wokwi) Último main.py gerado (latest)
│   ├── diagram.json          # (Modo Wokwi) Último diagram.json gerado (latest)
│   ├── ssd1306.py            # (Modo Wokwi) Driver OLED SSD1306 (latest)
│   └── raciocinio.md         # Cadeia de raciocínio completa consolidada (latest)
└── ollama_install/           # Diretório local do Ollama offline (binário, libs e modelos)
```

---

## 🔧 Instalação e Configuração

### 1. Preparar o Ambiente Python
Recomenda-se criar um ambiente virtual (venv) para isolar as dependências:

```bash
# Criar e ativar o ambiente virtual
python3 -m venv .venv
source .venv/bin/activate

# Instalar as dependências do projeto
pip install -r requirements.txt
```

### 2. Configurar o Ollama Localmente
Se você deseja utilizar a instalação manual offline provida na pasta do projeto:

```bash
# Tornar o script gerenciador executável
chmod +x ollama.sh

# Iniciar o servidor Ollama local em background
./ollama.sh serve

# Fazer o download do modelo Qwen2.5-Coder-3B
./ollama.sh pull qwen2.5-coder:3b

# (Opcional) Remover versão anterior 1.5B caso esteja instalada
./ollama.sh rm qwen2.5-coder:1.5b
```

> [!NOTE]
> Se preferir instalar o Ollama globalmente no sistema com privilégios administrativos (`sudo`), execute:
> `curl -fsSL https://ollama.com/install.sh | sudo sh`

---

## 🦙 Principais Comandos do Ollama

Você pode gerenciar os modelos tanto pelo script wrapper do projeto (`./ollama.sh`) quanto diretamente pela CLI nativa do Ollama (`ollama` ou `./ollama_install/bin/ollama`).

### 1. Comandos via Wrapper do Projeto (`./ollama.sh`)
O script `ollama.sh` já configura automaticamente variáveis de ambiente locais (`OLLAMA_MODELS`, `OLLAMA_HOST` e `LD_LIBRARY_PATH`):

| Comando | Descrição |
| :--- | :--- |
| `./ollama.sh serve` | Inicia o servidor Ollama local em background (`127.0.0.1:11434`). |
| `./ollama.sh status` | Verifica se o servidor Ollama está online ou offline. |
| `./ollama.sh stop` | Encerra o processo do servidor Ollama em execução. |
| `./ollama.sh pull [modelo]` | Baixa um modelo (padrão: `qwen2.5-coder:3b`). |
| `./ollama.sh rm [modelo]` | Remove um modelo do armazenamento local (ex.: `./ollama.sh rm qwen2.5-coder:1.5b`). |
| `./ollama.sh list` | Lista todos os modelos baixados localmente. |
| `./ollama.sh ps` | Mostra os modelos atualmente carregados na memória. |
| `./ollama.sh run "prompt"` | Executa uma consulta direta ao modelo `qwen2.5-coder:3b`. |
| `./ollama.sh chat` | Abre uma sessão de chat interativo no terminal com o modelo. |
| `./ollama.sh logs` | Exibe as últimas 50 linhas do log do servidor (`ollama_server.log`). |

### 2. Comandos Nativos da CLI do Ollama (`ollama`)
Caso utilize o binário diretamente no terminal:

| Comando | Exemplo de Uso | Descrição |
| :--- | :--- | :--- |
| `ollama serve` | `ollama serve` | Inicia o servidor da API do Ollama. |
| `ollama pull` | `ollama pull qwen2.5-coder:3b` | Baixa ou atualiza um modelo do registro oficial. |
| `ollama run` | `ollama run qwen2.5-coder:3b` | Inicia e executa um modelo (baixa automaticamente se não existir). |
| `ollama stop` | `ollama stop qwen2.5-coder:3b` | Descarrega um modelo em execução da memória (VRAM/RAM). |
| `ollama list` (`ls`) | `ollama list` | Lista todos os modelos armazenados no disco local. |
| `ollama ps` | `ollama ps` | Mostra os modelos atualmente carregados na memória e o uso de VRAM/CPU. |
| `ollama show` | `ollama show qwen2.5-coder:3b` | Exibe informações detalhadas do modelo (parâmetros, arquitetura, Modelfile). |
| `ollama create` | `ollama create meu-modelo -f Modelfile` | Cria um modelo customizado a partir de um arquivo `Modelfile`. |
| `ollama cp` | `ollama cp qwen2.5-coder:3b backup-qwen` | Duplica um modelo existente com um novo nome. |
| `ollama rm` | `ollama rm qwen2.5-coder:1.5b` | Remove um modelo do armazenamento local para liberar espaço. |
| `ollama --version` | `ollama --version` | Exibe a versão instalada do Ollama. |

### 3. Comandos Internos do Chat Interativo (`ollama run`)
Dentro de uma sessão interativa no terminal:
* `/bye` — Sai do chat interativo.
* `/clear` — Limpa o histórico de contexto da conversa atual.
* `/set parameter num_ctx 4096` — Ajusta parâmetros de inferência em tempo de execução.
* `/?` ou `/help` — Lista todos os atalhos e comandos disponíveis no modo interativo.

---

## 🚀 Como Executar

### Modo Interativo
Inicie o script e insira a descrição da sua aplicação. O prompt aceita múltiplas linhas e será executado quando você pressionar a tecla `Enter` duas vezes (uma linha em branco).

```bash
python3 app_agente.py
```

### Modo Batch (Pipeline de Comando)
Você pode enviar a especificação diretamente via pipe (`stdin`), útil para integrações ou automação:

```bash
echo "Escreva uma calculadora em Python que suporte operações básicas e validação de divisão por zero." | python3 app_agente.py
```

---

## 🛠️ Como Executar os Artefatos no Simulador Wokwi

Quando você solicita um projeto embarcado para **Wokwi / MicroPython / Raspberry Pi Pico**, o pipeline gera automaticamente os arquivos prontos para simulação dentro de `artifacts/` (e em `artifacts/run_[timestamp]/`):

*   `main.py` — Código principal em MicroPython (`machine`, `dht`, `time`, `json`, `ssd1306`).
*   `diagram.json` — Esquema elétrico completo no formato oficial do Wokwi (`version: 1`, `parts`, `connections`).
*   `ssd1306.py` — Driver I2C para o display OLED SSD1306.
*   `wokwi.toml` — Configuração para execução local via extensão Wokwi do VS Code.

### Opção 1: Executar no Wokwi Web (Navegador)
1. Acesse o template oficial de MicroPython para Raspberry Pi Pico:
   👉 [https://wokwi.com/projects/new/micropython-pi-pico](https://wokwi.com/projects/new/micropython-pi-pico)
2. Na aba **`main.py`**, cole o conteúdo de `artifacts/main.py`.
3. Clique no botão **`+`** (ao lado das abas) → **New File...** → crie **`ssd1306.py`** e cole o conteúdo de `artifacts/ssd1306.py`.
4. Na aba **`diagram.json`**, substitua todo o conteúdo pelo arquivo `artifacts/diagram.json`.
5. Clique no botão verde **Start the simulation (Play ▶️)** para interagir com os sensores (DHT22, LDR, potenciômetro, botão GP14, servo e OLED) em tempo real.

### Opção 2: Executar no VS Code (Extensão Wokwi Simulator)
Diferente da versão Web, a extensão **Wokwi Simulator** do VS Code exige um binário `.uf2` local do MicroPython configurado no `wokwi.toml`. O `app_agente.py` já empacota automaticamente o `main.py` e o `ssd1306.py` dentro da partição LittleFS2 (`0x100A0000`) do arquivo **`firmware.uf2`**.

1. Instale a extensão **Wokwi Simulator** (`wokwi.wokwi-vscode`) no VS Code e ative sua licença gratuita (`Wokwi: Request a New License`).
2. Abra o arquivo `artifacts/diagram.json` (ou de qualquer subpasta `artifacts/run_*/diagram.json`).
3. Pressione `F1` / `Ctrl+Shift+P` e selecione **`Wokwi: Start Simulator`**.
4. Caso queira reenviar ou testar alterações no `main.py` com o simulador aberto via porta serial virtual (`rfc2217ServerPort = 4000`), mantenha a aba do simulador visível e execute em outro terminal:
   ```bash
   ./.venv/bin/python3 -m mpremote connect port:rfc2217://localhost:4000 fs cp artifacts/ssd1306.py :ssd1306.py + run artifacts/main.py
   ```

---

## 🔌 Integração com a IDE Zed

### 1. Configurando Tasks Customizadas

#### Ambiente Linux Nativo
Para ter atalhos rápidos de execução e gerência dentro da IDE Zed no Linux, importe as configurações para o diretório da IDE ou para a pasta `.zed/` do projeto:

```bash
mkdir -p ~/.config/zed
cp zed_tasks.json ~/.config/zed/tasks.json
```

#### Ambiente Windows + WSL2 (Zed instalado no Windows)
Quando o Zed está instalado no Windows e o projeto roda dentro do WSL2 (`Ubuntu-24.04`), o arquivo `tasks.json` no Windows fica localizado em:
* **Caminho no Windows:** `%APPDATA%\Zed\tasks.json` (ex.: `C:\Users\<SEU_USUARIO>\AppData\Roaming\Zed\tasks.json`)
* **Caminho acessível via WSL2:** `/mnt/c/Users/<SEU_USUARIO>/AppData/Roaming/Zed/tasks.json`
* **Alternativa pela própria IDE Zed:** Pressione `Ctrl+Shift+P` e selecione `zed: open tasks`.
* **Por projeto:** Também fica disponível automaticamente em `.zed/tasks.json` na raiz deste repositório.

> [!NOTE]
> No setup Windows + WSL2, os comandos das tasks utilizam `wsl.exe -d Ubuntu-24.04 --cd /home/vsvasconcelos/projetos/EdgeAI ...` para que o Zed do Windows dispare a execução diretamente dentro do ambiente Linux do WSL2 sem conflito de caminhos.

Abra a IDE Zed no projeto, aperte `Ctrl+Shift+P` (ou `Cmd+Shift+P` no macOS), busque por `Task: Spawn` e escolha uma das opções disponíveis:
*   `🤖 EdgeAI — Executar Sistema Multi-Agente`
*   `🔍 EdgeAI — Verificar Ambiente`
*   `📦 EdgeAI — Instalar Dependências`
*   `🚀 EdgeAI — Iniciar Ollama`
*   `⬇️ EdgeAI — Baixar Modelo`
*   `⚡ EdgeAI — Executar em Modo Batch`

### 2. Configurando o Servidor MCP (Model Context Protocol)
O arquivo `mcp_server.py` permite que o agente interno do Zed (IA integrada) utilize a sua tripulação local de agentes como uma ferramenta.

Para registrar o servidor MCP no seu Zed:
1. Abra as configurações globais do Zed (`Ctrl+,` ou `zed: open settings` — no Windows fica em `%APPDATA%\Zed\settings.json`).
2. Adicione ou edite o bloco `context_servers` em seu `settings.json`:

**No Linux nativo:**
```json
{
  "context_servers": {
    "edgeai-agents": {
      "command": "/home/vsvasconcelos/projetos/EdgeAI/.venv/bin/python3",
      "args": ["/home/vsvasconcelos/projetos/EdgeAI/mcp_server.py"],
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

**No Windows com WSL2 (`Ubuntu-24.04`):**
```json
{
  "context_servers": {
    "edgeai-agents": {
      "command": "wsl.exe",
      "args": [
        "-d",
        "Ubuntu-24.04",
        "--cd",
        "/home/vsvasconcelos/projetos/EdgeAI",
        "env",
        "PYTHONUNBUFFERED=1",
        "PYTHONIOENCODING=utf-8",
        "/home/vsvasconcelos/projetos/EdgeAI/.venv/bin/python3",
        "/home/vsvasconcelos/projetos/EdgeAI/mcp_server.py"
      ]
    }
  }
}
```

3. Certifique-se de que a dependência `fastmcp` ou `mcp` está instalada no seu Python global ou venv em execução.
4. Agora, no chat do Zed Agent, você poderá invocar a ferramenta `rodar_pipeline_agentes` enviando um pedido de funcionalidade!

---

## 📊 Matriz de Compatibilidade

As versões abaixo foram homologadas e garantem o funcionamento correto do ecossistema:

| Tecnologia        | Versão             | Observação                                              |
| :---------------- | :----------------- | :------------------------------------------------------ |
| **Python**        | 3.14.4 / 3.x       | Linguagem de execução padrão do pipeline                |
| **Ollama**        | v0.30.11 / v0.31.1 | Motor de inferência local rodando na porta 11434        |
| **Qwen2.5-Coder** | 3B (INT4 / Q4_K_M) | Modelo de linguagem local principal (~1.9 GB) — substituiu a versão 1.5B |
| **CrewAI**        | v0.11.2            | Legado de arquitetura (não utilizado no pipeline ativo) |
| **LangChain**     | Versão resolvida   | Biblioteca base de interação com ChatOllama             |
| **FastMCP**       | 0.x                | SDK para encapsulamento das ferramentas MCP             |

---

> [!TIP]
> Todos os códigos Python gerados pelo desenvolvedor local são salvos automaticamente em formato bruto no arquivo `artifacts/codigo.py`, pronto para execução e testes imediatos.
