# Relatório de Instalação e Configuração
## Ollama v0.30.11 + Qwen2.5-Coder-1.5B — Execução Local

| | |
|---|---|
| **Data/Hora** | 29 de junho de 2026 — 22h15 a 22h47 (BRT) |
| **Máquina** | ermelinux |
| **Sistema** | Ubuntu 26.04 LTS (Resolute Raccoon) |
| **Responsável** | vsvasconcelos |
| **Projeto** | Curso: I2A2 - Agentic AI|

---

## 1. Objetivo

Instalar e configurar o **Ollama v0.30.11** para executar o modelo de linguagem de código **Qwen2.5-Coder-1.5B** completamente de forma local (offline), sem depender de nuvem, no ambiente de desenvolvimento do projeto EdgeAI.

---

## 2. Inventário do Sistema (pré-instalação)

### 2.1 Hardware

| Componente | Especificação |
|---|---|
| **CPU** | x86_64 · 8 núcleos lógicos |
| **RAM Total** | 7,1 GiB |
| **RAM Disponível** | ~3,3 GiB |
| **Swap** | 4,0 GiB |
| **Armazenamento (/)** | 724 GB · 651 GB livres |
| **GPU Dedicada** | NVIDIA GeForce MX110 · **2048 MiB VRAM** |
| **GPU Integrada** | Intel UHD Graphics 620 (WhiskeyLake-U GT2) |

### 2.2 Software (pré-instalação)

| Componente | Versão |
|---|---|
| **Kernel Linux** | 7.0.0-27-generic (SMP PREEMPT_DYNAMIC) |
| **Ubuntu** | 26.04 LTS (Resolute Raccoon) |
| **Driver NVIDIA** | 580.159.03 |
| **CUDA** | 13.0 |
| **Ollama** | ❌ Não instalado |

### 2.3 Diagnóstico de GPU

```
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 580.159.03   Driver Version: 580.159.03   CUDA Version: 13.0   |
|-----------------------------+----------------------+----------------------+
| GPU  Name        Pers-M    | Bus-Id        Disp.A | Volatile Uncorr. ECC |
|   0  MX110           Off  | 00000000:01:00.0 Off |                  N/A |
|  N/A  42C    P8    N/A     |       3MiB / 2048MiB |      0%      Default |
+-----------------------------------------------------------------------------+
```

> [!WARNING]
> A GPU MX110 possui apenas **2 GB de VRAM**, insuficiente para hospedar o modelo inteiro. O Ollama executou o modelo **inteiramente em CPU (RAM)** durante toda a sessão.

---

## 3. Passo a Passo da Instalação

### Passo 1 — Verificação inicial (Ollama ausente)

**Comando executado:**
```bash
which ollama && ollama --version && ollama list
```

**Resultado:**
```
OLLAMA_NOT_FOUND
```

**Conclusão:** Ollama não estava instalado no sistema.

---

### Passo 2 — Tentativa com instalador oficial (bloqueada)

**Comando tentado:**
```bash
curl -fsSL https://ollama.com/install.sh | sudo sh
```

**Resultado:**
```
>>> Installing ollama to /usr/local
sudo: A terminal is required to authenticate
```

**Causa:** O ambiente de automação não dispõe de terminal interativo para autenticar o `sudo`. Foi necessária uma abordagem alternativa: **instalação manual em espaço do usuário**, sem privilégios root.

---

### Passo 3 — Descoberta da versão e URL de download

**Comando executado:**
```bash
curl -s https://api.github.com/repos/ollama/ollama/releases/latest \
  | python3 -c "import sys,json; r=json.load(sys.stdin); \
    print(r['tag_name']); \
    [print(a['browser_download_url']) for a in r['assets']]"
```

**Resultado relevante:**
```
v0.30.11
https://github.com/ollama/ollama/releases/download/v0.30.11/ollama-linux-amd64.tar.zst
```

**Pacote selecionado:** `ollama-linux-amd64.tar.zst` (binário + libs CUDA para Linux x86_64)

---

### Passo 4 — Download do pacote Ollama

**Comando executado:**
```bash
mkdir -p /projetos/EdgeAI/ollama_install
curl -L \
  "https://github.com/ollama/ollama/releases/download/v0.30.11/ollama-linux-amd64.tar.zst" \
  -o ollama_install/ollama-linux-amd64.tar.zst \
  --progress-bar
```

| Atributo | Valor |
|---|---|
| **Tamanho** | 1,4 GB |
| **Tempo de download** | ~9 minutos |
| **Status** | ✅ Sucesso |

---

### Passo 5 — Extração do pacote

**Comando executado:**
```bash
cd ollama_install
tar -xf ollama-linux-amd64.tar.zst
```

**Estrutura extraída:**
```
ollama_install/
├── bin/
│   └── ollama          ← Binário principal (37 MB)
├── lib/
│   └── ollama/         ← Bibliotecas CUDA/Vulkan/GPU
├── ollama-linux-amd64.tar.zst   ← Pacote original (1,4 GB)
└── start_ollama.sh     ← Criado na sequência
```

**Verificação:**
```bash
chmod +x bin/ollama
bin/ollama --version
# Warning: client version is 0.30.11
```

**Status:** ✅ Binário funcional

---

### Passo 6 — Configuração do ambiente (sem sudo)

O Ollama foi configurado inteiramente via **variáveis de ambiente**, sem necessidade de privilégios root:

| Variável de Ambiente | Valor Configurado | Propósito |
|---|---|---|
| `OLLAMA_MODELS` | `./ollama_install/models` | Diretório local dos modelos |
| `OLLAMA_HOST` | `127.0.0.1:11434` | Endereço e porta do servidor |
| `LD_LIBRARY_PATH` | `./ollama_install/lib/ollama` | Libs CUDA/GPU locais |

---

### Passo 7 — Inicialização do servidor Ollama

**Comando executado:**
```bash
OLLAMA_MODELS="$INSTALL_DIR/models" \
OLLAMA_HOST="127.0.0.1:11434" \
LD_LIBRARY_PATH="$INSTALL_DIR/lib/ollama:$LD_LIBRARY_PATH" \
"$INSTALL_DIR/bin/ollama" serve > ollama_server.log 2>&1 &
```

**Saída do log (trecho):**
```log
time=2026-06-29T22:26:56 level=INFO msg="server config"
  OLLAMA_HOST:http://127.0.0.1:11434
  OLLAMA_MODELS:.../ollama_install/models
  OLLAMA_VULKAN:true

time=2026-06-29T22:26:56 level=INFO msg="Listening on 127.0.0.1:11434 (version 0.30.11)"
time=2026-06-29T22:26:56 level=INFO msg="discovering available GPUs..."
```

| Atributo | Valor |
|---|---|
| **PID** | 17688 |
| **Endpoint** | http://127.0.0.1:11434 |
| **Status** | ✅ Online |

---

### Passo 8 — Download do modelo Qwen2.5-Coder-1.5B

**Comando executado:**
```bash
"$INSTALL_DIR/bin/ollama" pull qwen2.5-coder:1.5b
```

**Progresso do download (layers):**

| Layer (SHA256) | Tamanho | Conteúdo |
|---|---|---|
| `29d8c98fa6b0...` | **986 MB** | Pesos do modelo (GGUF Q4_K_M) |
| `66b9ea09bd5b...` | 68 B | Template de prompt |
| `1e65450c3067...` | 1,6 KB | Parâmetros de geração |
| `832dd9e00a68...` | 11 KB | Vocabulário do tokenizer |
| `152cb442202b...` | 487 B | Licença Apache 2.0 |

```
verifying sha256 digest ✓
writing manifest ✓
success ✓
```

**Status:** ✅ Instalado com sucesso

---

### Passo 9 — Verificação via API REST

**Teste 1 — Servidor respondendo:**
```bash
curl http://127.0.0.1:11434/
# Resposta: Ollama is running
```

**Teste 2 — Listagem de modelos:**
```bash
curl -s http://127.0.0.1:11434/api/tags | python3 -m json.tool
```

```json
{
  "models": [{
    "name": "qwen2.5-coder:1.5b",
    "model": "qwen2.5-coder:1.5b",
    "modified_at": "2026-06-29T22:31:20.365-03:00",
    "size": 986062089,
    "digest": "d7372fd828518a4d38b1eb196c673c31a85f2ed302b3d1e406c4c2d1b64a0668",
    "details": {
      "format": "gguf",
      "family": "qwen2",
      "parameter_size": "1.5B",
      "quantization_level": "Q4_K_M",
      "context_length": 32768,
      "embedding_length": 1536
    },
    "capabilities": ["completion", "tools", "insert"]
  }]
}
```

**Status:** ✅ API funcionando, modelo visível

---

### Passo 10 — Teste de inferência

**Comando executado:**
```bash
"$INSTALL_DIR/bin/ollama" run qwen2.5-coder:1.5b \
  "Escreva uma função Python que calcula o número de Fibonacci de forma recursiva com memoization."
```

**Resposta do modelo:**
```python
def fibonacci(n, memo={}):
    if n in memo:
        return memo[n]
    if n <= 1:
        return n
    result = fibonacci(n-1, memo) + fibonacci(n-2, memo)
    memo[n] = result
    return result
```

| Métrica | Valor |
|---|---|
| **Tempo de resposta** | ~1 minuto e 28 segundos |
| **Backend de execução** | CPU (RAM offload — GPU sem VRAM suficiente) |
| **Qualidade da resposta** | ✅ Código correto e funcional |

---

### Passo 11 — Diagnóstico automatizado (health check)

**Comando executado:**
```bash
# Script de diagnóstico completo com 5 verificações
```

**Resultado:**
```
✅ 1. Binário: ollama version is 0.30.11
✅ 2. Servidor ONLINE → http://127.0.0.1:11434
✅ 3. Modelo: qwen2.5-coder:1.5b  (986 MB)
✅ 4. API REST /api/tags retornou o modelo
✅ 5. Inferência funcionando! Resposta: 'OK'
   ⏱ Duração: 1.5s  |  📊 Tokens gerados: 2
```

**Status:** ✅ 5/5 verificações aprovadas

---

### Passo 12 — Cópia dos blobs para ~/.ollama/models

Para preparar a migração para a instalação oficial (via `sudo`), os blobs do modelo foram copiados para o diretório padrão do Ollama:

**Comandos executados:**
```bash
mkdir -p ~/.ollama/models/blobs
mkdir -p ~/.ollama/models/manifests/registry.ollama.ai/library/qwen2.5-coder

cp -v ollama_install/models/blobs/* ~/.ollama/models/blobs/
cp -v ollama_install/models/manifests/registry.ollama.ai/library/qwen2.5-coder/1.5b \
       ~/.ollama/models/manifests/registry.ollama.ai/library/qwen2.5-coder/1.5b
```

**Arquivos copiados para `~/.ollama/models/`:**

| Arquivo | Tamanho |
|---|---|
| `blobs/sha256-29d8c98fa6b0...` | **941 MB** (pesos GGUF) |
| `blobs/sha256-832dd9e00a68...` | 12 KB (tokenizer) |
| `blobs/sha256-152cb442202b...` | 4 KB (licença) |
| `blobs/sha256-1e65450c3067...` | 4 KB (params) |
| `blobs/sha256-66b9ea09bd5b...` | 4 KB (template) |
| `manifests/.../1.5b` | 4 KB (índice) |

**Status:** ✅ Cópia concluída — modelo pronto para instalação oficial

---

## 4. Arquivos Criados no Projeto

```
EdgeAI/
├── ollama.sh                          ← Wrapper de conveniência (gerenciar o Ollama)
└── ollama_install/
    ├── bin/
    │   └── ollama                     ← Binário Ollama v0.30.11 (37 MB)
    ├── lib/
    │   └── ollama/                    ← Bibliotecas CUDA/Vulkan
    ├── models/
    │   ├── blobs/                     ← Arquivos binários do modelo
    │   └── manifests/                 ← Índices/manifests
    ├── ollama-linux-amd64.tar.zst     ← Pacote original (1,4 GB)
    ├── ollama_server.log              ← Log do servidor
    └── start_ollama.sh                ← Script de inicialização
```

```
~/.ollama/
└── models/
    ├── blobs/                         ← Cópia dos pesos do modelo
    └── manifests/                     ← Cópia dos manifests
```

---

## 5. Informações do Modelo Instalado

| Atributo | Valor |
|---|---|
| **Nome** | Qwen2.5-Coder-1.5B-Instruct |
| **Desenvolvedor** | Alibaba Cloud — Qwen Team |
| **Parâmetros** | 1,5 bilhão |
| **Formato** | GGUF (llama.cpp compatível) |
| **Quantização** | Q4_K_M (4 bits — balanceado) |
| **Context Window** | 32.768 tokens |
| **Embedding** | 1.536 dimensões |
| **Digest SHA256** | `d7372fd828518a4d...` |
| **Especialização** | Geração, completação e depuração de código |
| **Idiomas** | Multilingual (PT-BR, EN, ZH, etc.) |
| **Licença** | Apache 2.0 |

---

## 6. Guia de Uso

### 6.1 Gerenciar o servidor (via wrapper `ollama.sh`)

```bash
cd /projetos/EdgeAI

./ollama.sh serve    # Inicia o servidor em background
./ollama.sh status   # Verifica se está online
./ollama.sh list     # Lista modelos instalados
./ollama.sh chat     # Abre chat interativo (digite /bye para sair)
./ollama.sh logs     # Exibe log do servidor
./ollama.sh stop     # Para o servidor
```

### 6.2 Consulta direta (sem chat)

```bash
./ollama.sh run "Escreva um bubble sort em C"
```

### 6.3 API REST com curl

```bash
# Verificar status
curl http://127.0.0.1:11434/

# Listar modelos
curl http://127.0.0.1:11434/api/tags

# Gerar texto
curl http://127.0.0.1:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-coder:1.5b",
    "prompt": "Explique o que é um ponteiro em C",
    "stream": false
  }'
```

### 6.4 API REST com Python

```python
import requests

resposta = requests.post(
    "http://127.0.0.1:11434/api/generate",
    json={
        "model": "qwen2.5-coder:1.5b",
        "prompt": "Escreva uma busca binária em Python",
        "stream": False
    }
)
print(resposta.json()["response"])
```

---

## 7. Próximo Passo — Instalação Oficial (com sudo)

Execute no **terminal do usuário** (fora do agente):

```bash
curl -fsSL https://ollama.com/install.sh | sudo sh
```

Isso irá:
- ✅ Mover o binário para `/usr/local/bin/ollama` (disponível globalmente)
- ✅ Criar o serviço `systemd` (`ollama.service`) — **inicia automaticamente no boot**
- ✅ Criar o usuário de sistema `ollama`
- ✅ Detectar e configurar a GPU NVIDIA automaticamente

**Após a instalação oficial, o modelo já estará disponível** (blobs copiados em `~/.ollama/models/`):

```bash
ollama list            # Confirmar que qwen2.5-coder:1.5b aparece
ollama run qwen2.5-coder:1.5b   # Testar
sudo systemctl status ollama    # Verificar serviço
-----
- ✅ Desativar a inicialização automática no boot
sudo systemctl disable ollama
- ✅  Iniciar manualmente o modelo
sudo systemctl start ollama
- ✅  Utilizar o modelo
ollama run qwen2.5-coder:1.5b



```

---

## 8. Diagnóstico de GPU — Observações

| Item | Status |
|---|---|
| GPU NVIDIA MX110 detectada | ✅ |
| Driver 580.159.03 instalado | ✅ |
| CUDA 13.0 disponível | ✅ |
| VRAM suficiente (≥ 4 GB necessário) | ❌ 2 GB insuficiente |
| **Execução** | **100% CPU (RAM offload)** |

> [!NOTE]
> Para habilitar aceleração GPU total seria necessária uma placa com ≥ 4 GB de VRAM (ex: RTX 3050 ou superior). Com CPU, o tempo de resposta foi de ~88s para respostas médias.

---

## 9. Referências

| Recurso | Link |
|---|---|
| Ollama Official Site | https://ollama.com |
| Ollama GitHub Releases | https://github.com/ollama/ollama/releases |
| Qwen2.5-Coder no Ollama Hub | https://ollama.com/library/qwen2.5-coder |
| Qwen2.5-Coder Paper (arXiv) | https://arxiv.org/abs/2409.12186 |
| Ollama API Documentation | https://github.com/ollama/ollama/blob/main/docs/api.md |
