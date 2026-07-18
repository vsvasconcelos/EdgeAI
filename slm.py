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
