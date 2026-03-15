import os
# Host Ollama
HOST_OLLAMA_LOCAL = 'http://localhost:11434/'
HOST_OLLAMA_NUBE = 'https://ollama.com'

# Modelo de Embeddings
MODEL_EMBEDDINGS = "nomic-embed-text-v2-moe:latest" #"nomic-embed-text"

# Modelo de Inferencia
MODEL_LLM_LOCAL = "llama3.2:latest"
MODEL_LLM_NUBE = "gpt-oss:120b-cloud"     # gpt-oss:120b-cloud, deepseek-v3.1:671b

# Api Ollama
API_KEY_OLLAMA = os.environ.get('OLLAMA_API_KEY', '96e9ee8d8635439b94b780dc1409fa75.EJ0zTzBh7dDKA1R_WqWZlvxG')
