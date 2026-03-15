import asyncio
import os
import chromadb
from ollama import AsyncClient
import pathlib
import logging

# Import config Ollama
from config import HOST_OLLAMA_LOCAL,HOST_OLLAMA_NUBE
from config import MODEL_EMBEDDINGS 
from config import MODEL_LLM_LOCAL, MODEL_LLM_NUBE 
from config import  API_KEY_OLLAMA 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# CONFIGURACIÓN DE ARQUITECTURA HÍBRIDA
# -------------------------------------------------------------------

BASE_DIR = pathlib.Path(__file__).parent.parent
VECTORS_PATH = BASE_DIR / "chroma_db"

class ChatRAGHibrido:
    def __init__(self):
        logging.info("[*] Inicializando sistema de RAG Híbrido...")
        
        # --- CLIENTE 1: OLLAMA LOCAL ---
        self.ollama_local = AsyncClient(host=HOST_OLLAMA_LOCAL)
        
        # --- CLIENTE 2: OLLAMA NUBE ---
        headers = {}
        if API_KEY_OLLAMA:
            headers['Authorization'] = f'Bearer {API_KEY_OLLAMA}'
            
        self.ollama_nube = AsyncClient(
            host=HOST_OLLAMA_NUBE, 
            headers=headers,
            timeout=180.0 # Damos más tiempo por la latencia de red
        )
        
        # --- BASE DE DATOS LOCAL ---
        self.chroma_client = chromadb.PersistentClient(path=VECTORS_PATH)
        try:
            self.coleccion = self.chroma_client.get_collection(name="base_conocimiento")
            logging.info(f"[+] Base de datos local conectada. ({self.coleccion.count()} documentos)")
        except ValueError:
            logging.info("[-] ERROR: No se encontró la base vectorial local.")
            exit(1)

    async def consultar(self, pregunta: str):
        """Ejecuta el pipeline distribuyendo la carga entre Local y Nube."""
        
        # ---------------------------------------------------------
        # FASE 1: PROCESAMIENTO LOCAL (Privado y sin costo de red)
        # ---------------------------------------------------------
        logging.info("\n[💻 Local]: Vectorizando pregunta...")
        # Usamos el cliente LOCAL para generar los embeddings
        embed_pregunta = await self.ollama_local.embed(
            model=MODEL_EMBEDDINGS, 
            input=pregunta
        )
        vector_pregunta = embed_pregunta.embeddings[0]

        logging.info("[💻 Local]: Buscando en el disco duro...")
        resultados = self.coleccion.query(
            query_embeddings=[vector_pregunta],
            n_results=10
        )

        if not resultados['documents'][0]:
            logging.info("No encontré información en tu base de datos local.")
            return

        contexto_recuperado = "\n---\n".join(resultados['documents'][0])

        # ---------------------------------------------------------
        # FASE 2: INFERENCIA EN LA NUBE (Poder de cómputo bruto)
        # ---------------------------------------------------------
        prompt_sistema = """Eres un químico farmaceuta y un asistente que conoce ampliamente de medicamentos.
          Responde a la pregunta basándote ÚNICAMENTE en el contexto. No inventes información. 
          Cuando sea posible responde con referencias a los fragmentos del contexto y en viñetas
          Si no sabes la respuesta, di que no fue proporcionada en la documentación oficial."""
        prompt_usuario = f"Contexto:\n{contexto_recuperado}\n\nPregunta: {pregunta}"

        logging.info(f"[☁️ Nube]: Generando respuesta con el LLM principal...{MODEL_LLM_NUBE}")

        
        # Usamos el cliente NUBE para el chat, enviando solo el contexto relevante
        async for fragmento in await self.ollama_nube.chat(
            model=MODEL_LLM_NUBE,
            messages=[
                {'role': 'system', 'content': prompt_sistema},
                {'role': 'user', 'content': prompt_usuario}
            ],
            stream=True
        ):
            print(fragmento['message']['content'], end='', flush=True)
            
        print("\n" + "-" * 50)

# -------------------------------------------------------------------
# EJECUCIÓN
# -------------------------------------------------------------------
async def iniciar_chat():
    sistema = ChatRAGHibrido()
    
    while True:
        pregunta = input("\n[🧑 Tú]: ")
        if pregunta.lower() in ['salir', 'exit', 'quit']:
            break
        if pregunta.strip():
            await sistema.consultar(pregunta)

if __name__ == "__main__":
    asyncio.run(iniciar_chat())