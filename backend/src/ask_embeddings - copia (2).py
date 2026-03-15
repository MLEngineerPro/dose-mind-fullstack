# logging
import logging
import sys
from logging.handlers import TimedRotatingFileHandler

# Import config Ollama
from ollama import AsyncClient
from config import HOST_OLLAMA_LOCAL, HOST_OLLAMA_NUBE
from config import MODEL_EMBEDDINGS 
from config import MODEL_LLM_LOCAL, MODEL_LLM_NUBE 
from config import API_KEY_OLLAMA 

# Otros import
import chromadb
import pathlib
from prompts import system_prompt

# Constantes
BASE_DIR = pathlib.Path(__file__).parent.parent
VECTORS_PATH = BASE_DIR / "chroma_db"
LOGS_PATH = BASE_DIR / "logs"

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG) # Nivel base para aceptar todo

if logger.hasHandlers():
    logger.handlers.clear()

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')


file_handler = TimedRotatingFileHandler(
    filename=LOGS_PATH / 'app.log',
    when='midnight',   # Corta y crea un archivo nuevo a la medianoche
    interval=1,        # Cada 1 día
    backupCount=7,     # ¡Aquí está la clave! Mantiene 7 archivos viejos. El día 8, borra el más viejo.
    encoding='utf-8'   # Para evitar problemas con tildes o caracteres especiales
)
file_handler.setLevel(logging.DEBUG) # Al archivo enviamos todo el detalle
file_handler.setFormatter(formatter)

# 4. Configuramos la pantalla (consola)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO) # A la pantalla solo enviamos de INFO para arriba (oculta DEBUG)
console_handler.setFormatter(formatter)

# 5. Conectamos ambos manejadores a nuestro logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# ─────────────────────────────────────────────
# Función de inicialización (llamar una sola vez)
# ─────────────────────────────────────────────
def crear_chroma_client(collection_name: str) -> chromadb.Collection:
    """
    Crea el cliente de ChromaDB y retorna la colección.
    Debe llamarse UNA SOLA VEZ al arrancar la aplicación (ej. lifespan de FastAPI).
    """
    logger.info("[*] Inicializando ChromaDB...")
    client = chromadb.PersistentClient(path=str(VECTORS_PATH))
    try:
        coleccion = client.get_collection(name=collection_name)
        logger.info(f"[+] Colección '{collection_name}' cargada ({coleccion.count()} documentos)")
        return coleccion
    except Exception as e:
        logger.error(f"[-] ERROR al conectar a ChromaDB: {e}")
        raise

class ChatRAGHibrido:
    def __init__(self, collection_name):
        logger.info("[*] Inicializando sistema de RAG Híbrido...")
        
        self.ollama_local = AsyncClient(host=HOST_OLLAMA_LOCAL)
        
        headers = {}
        if API_KEY_OLLAMA:
            headers['Authorization'] = f'Bearer {API_KEY_OLLAMA}'
            
        self.ollama_nube = AsyncClient(
            host=HOST_OLLAMA_NUBE, 
            headers=headers,
            timeout=180.0
        )
        
        self.chroma_client = chromadb.PersistentClient(path=str(VECTORS_PATH))
        try:
            self.coleccion = self.chroma_client.get_collection(name=collection_name)
            logger.info(f"[+] Base de datos local conectada, {collection_name} ({self.coleccion.count()} documentos)")
        except Exception as e:
            logger.error(f"[-] ERROR al conectar a ChromaDB: {e}")
            exit(1)

    def mostrar_detalles_fuentes(self,resultado_busqueda):
        """
        Extrae y muestra de forma legible la ubicación y origen de los documentos 
        encontrados en un resultado de base de datos vectorial (ej. ChromaDB).
        """
        # Verificamos que existan los datos necesarios
        if not resultado_busqueda or not resultado_busqueda.get('metadatas'):
            print("No se encontraron resultados o metadatos.")
            return

        # Extraemos las listas de la primera consulta (índice 0)
        metadatos = resultado_busqueda['metadatas'][0]
        ids_documentos = resultado_busqueda['ids'][0]
        distancias = resultado_busqueda['distances'][0]

        logging.info("### Resultados de la Búsqueda ###\n")

                # Iteramos sobre los resultados combinando metadatos, IDs y distancias
        for i, (meta, doc_id, distancia) in enumerate(zip(metadatos, ids_documentos, distancias), start=1):
            # Extraemos las claves específicas (usamos .get por seguridad si falta alguna)
            origen = meta.get('origen', 'Archivo desconocido')
            ubicacion = meta.get('ubicacion', 'Página desconocida')
            
            # Formateamos la salida
            logger.info(f"📌 **Resultado {i}** (ID: {doc_id})")
            logger.info(f"   📄 Documento: {origen}")
            logger.info(f"   📍 Ubicación: {ubicacion}")
            logger.info(f"   🎯 Distancia (Relevancia): {distancia:.4f}")
            logger.info("-" * 50)

    async def _obtener_contexto(self, pregunta: str):
        """Metodo interno para evitar repetir codigo de busqueda"""
        logger.info(f"Obteniendo respuesta del RAG con el modelo {MODEL_EMBEDDINGS}")
        embed_pregunta = await self.ollama_local.embed(
            model=MODEL_EMBEDDINGS, 
            input=pregunta
        )
        vector_pregunta = embed_pregunta.embeddings[0]
        
        resultados = self.coleccion.query(
            query_embeddings=[vector_pregunta],
            n_results=5
        )
        
        if not resultados['documents'] or not resultados['documents'][0]:
            return None
        
        #self.mostrar_detalles_fuentes(resultados)
        return resultados['documents'][0]

    async def consultar_stream(self, pregunta: str, inference_model: str, instancia:str):
        """Generador para streaming (yield)."""
        '''
        Campos disponibles en el último fragmento:	
            Campo	                Descripción
            done	                True solo en el último fragmento
            prompt_eval_count	    Tokens consumidos del prompt/contexto
            eval_count	            Tokens generados en la respuesta
            total_duration	        Tiempo total en nanosegundos
            load_duration	        Tiempo en cargar el modelo en nanosegundos
            eval_duration	        Tiempo de inferencia en nanosegundos
            prompt_eval_duration	Tiempo en procesar el prompt en nanosegundos
        '''
        temperature=0.5
        contexto = await self._obtener_contexto(pregunta)
        if not contexto:
            yield "No encontré información relevante."
            return

        prompt_usuario = f"Contexto:\n{contexto}\n\nPregunta: {pregunta}"
        logger.info(f"Pregunta del usuario: {pregunta}")
        logger.info(f"Buscando respuestas con {inference_model}, temperatura: {temperature} en la instancia: {instancia}")
        

        if instancia=='nube':
            async for fragmento in await self.ollama_nube.chat(
                model=inference_model,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': prompt_usuario}
                ],
                stream=True,
                think='high',
                options={'temperature': temperature}
            ):
                yield fragmento['message']['content']

                if fragmento.get('done'):
                    metricas = {
                    'tokens_prompt':    fragmento.get('prompt_eval_count', 0),
                    'tokens_respuesta': fragmento.get('eval_count', 0),
                    'tiempo_total_s':   fragmento.get('total_duration', 0) / 1e9,
                    }
                    logger.info(f"Métricas: {metricas}")

        else:
            async for fragmento in await self.ollama_local.chat(
                model=inference_model,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': prompt_usuario}
                ],
                stream=True
            ):
                yield fragmento['message']['content']


# if __name__ == "__main__":
#     # Prueba rápida del generador
#     import asyncio
    
#     chat_rag = ChatRAGHibrido(collection_name='base_conocimiento')
    
#     pregunta_test = "¿para que sirve el salbutamol?"
#     inference_model_test = MODEL_LLM_NUBE
#     instancia_test = 'nube'
    
#     async def prueba_stream():
#         async for fragmento in chat_rag.consultar_stream(pregunta_test, inference_model_test, instancia_test):
#             print(fragmento, end='', flush=True)
    
#     asyncio.run(prueba_stream())