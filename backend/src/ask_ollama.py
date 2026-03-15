import os
import json
import asyncio
from typing import Dict, Any, List
from ollama import AsyncClient, Message
import logging
import pathlib

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# 1. CONFIGURACIÓN DEL ENTORNO Y VARIABLES GLOBALES
# -------------------------------------------------------------------

BASE_DIR = pathlib.Path(__file__).parent.parent
VECTORS_PATH = BASE_DIR / "chroma_db"

# Import config Ollama
from config import HOST_OLLAMA_LOCAL,HOST_OLLAMA_NUBE
from config import MODEL_EMBEDDINGS
from config import MODEL_LLM_LOCAL, MODEL_LLM_NUBE 
from config import  API_KEY_OLLAMA 

# -------------------------------------------------------------------
# 2. DEFINICIÓN DE HERRAMIENTAS (TOOL CALLING)
# -------------------------------------------------------------------

def obtener_clima(ciudad: str) -> str:
    """Obtiene el clima actual para una ciudad específica (Función simulada)."""
    # En la vida real, aquí llamarías a una API del clima
    clima_simulado = {"ciudad": ciudad, "temperatura": "22°C", "condicion": "Soleado"}
    return json.dumps(clima_simulado)

# Diccionario para mapear el nombre de la herramienta a la función de Python
HERRAMIENTAS_DISPONIBLES = {
    "obtener_clima": obtener_clima
}

class OllamaAvanzado:
    """Clase que encapsula todas las funcionalidades avanzadas de Ollama usando AsyncClient."""

    #def __init__(self, host: str, api_key: str):
    def __init__(self):
        """Inicializa el cliente asíncrono con configuraciones personalizadas."""
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
        
        # Opciones avanzadas de generación (Hyperparameters)
        self.opciones_avanzadas = {
            "temperature": 0.5,      # Creatividad (0.0 = determinista, 1.0 = muy creativo)
            "num_ctx": 4096,         # Tamaño de la ventana de contexto (tokens que recuerda)
            "top_p": 0.9,            # Nucleus sampling (controla la diversidad de palabras)
            "top_k": 40,             # Reduce la probabilidad de generar palabras sin sentido
            "repeat_penalty": 1.1,   # Penaliza la repetición de palabras
            "seed": 42,              # Semilla para reproducibilidad (siempre dará la misma respuesta si temp=0)
            "num_predict": 2000,      # Número máximo de tokens a predecir (generar)
            "stop": ["\nUser:", "<|end|>"] # Secuencias donde el modelo dejará de generar texto
        }

    # async def preparar_modelo(self, model_name: str):
    #     """Usa los métodos list() y pull() para asegurar que el modelo exista."""
    #     logging.info(f"[*] Verificando si {model_name} está instalado...")
        
    #     # Método list(): Obtiene todos los modelos descargados
    #     lista_modelos = await self.client.list()
    #     modelos_instalados = [m['name'] for m in lista_modelos['models']]

    #     if model_name not in modelos_instalados:
    #         logging.info(f"[*] Descargando {model_name}. Esto puede tardar...")
    #         # Método pull(): Descarga un modelo. stream=True nos da progreso en vivo.
    #         async for progreso in await self.client.pull(model_name, stream=True):
    #             logging.info(f"Progreso: {progreso.get('status')} - {progreso.get('completed', 0)}/{progreso.get('total', 1)} bytes", end="\r")
    #         logging.info("\n[+] Descarga completada.")
    #     else:
    #         logging.info(f"[+] Modelo {model_name} ya está disponible.")

    # async def crear_modelo_personalizado(self, nuevo_nombre: str, modelo_base: str):
    #     """Usa el método create() para generar un modelo con un System Prompt fijo."""
    #     logging.info(f"[*] Creando modelo personalizado '{nuevo_nombre}'...")
    #     modelfile = f"""
    #     FROM {modelo_base}
    #     SYSTEM Eres un asistente experto en Python. Responde siempre en formato JSON.
    #     PARAMETER temperature 0.2
    #     """
    #     # Método create(): Crea un modelo a partir de un Modelfile
    #     await self.client.create(model=nuevo_nombre, modelfile=modelfile)
    #     logging.info(f"[+] Modelo '{nuevo_nombre}' creado.")

    async def chat_avanzado(self, question: str, model_name: str, local_nube:str) -> str:
        """Usa el método chat() con todas sus capacidades: herramientas, opciones y streaming."""
        logging.info(f"\n[*] Iniciando chat con {model_name}...")
        
        mensajes: List[Message] = [
            {'role': 'system', 'content': 'Eres un asistente útil que puede usar herramientas si es necesario.'},
            {'role': 'user', 'content': question}
        ]
        # 1. Seleccionar el cliente adecuado dinámicamente
        cliente = self.ollama_local if local_nube == "local" else self.ollama_nube

        # 2. Definir las herramientas (pasamos la función directamente)
        #herramientas_lista = [obtener_clima]
        # Configuración de la herramienta que el LLM puede usar
        # tools = [{
        #     'type': 'function',
        #     'function': {
        #         'name': 'obtener_clima',
        #         'description': 'Obtiene el clima actual de una ciudad',
        #         'parameters': {
        #             'type': 'object',
        #             'properties': {
        #                 'ciudad': {'type': 'string', 'description': 'El nombre de la ciudad, ej. Madrid'}
        #             },
        #             'required': ['ciudad']
        #         }
        #     }
        # }]

        # Método chat() completo
        # if local_nube=="local":
        #     response = await self.ollama_local.chat(
        #         model=model_name,
        #         messages=mensajes,
        #         stream=False,                 # Lo mantenemos en False para procesar la respuesta completa
        #         format="",                    # Podría ser "json" si queremos forzar que la salida sea un JSON válido
        #         options=self.opciones_avanzadas,
        #         #tools=tools,                  # Le pasamos la herramienta
        #         keep_alive="1h"               # Mantiene el modelo cargado en la VRAM/RAM durante 1 hora
        #     )
        # else:
        #     response = await self.ollama_nube.chat(
        #         model=model_name,
        #         messages=mensajes,
        #         stream=False,                 # Lo mantenemos en False para procesar la respuesta completa
        #         format="",                    # Podría ser "json" si queremos forzar que la salida sea un JSON válido
        #         options=self.opciones_avanzadas,
        #         #tools=tools,                  # Le pasamos la herramienta
        #         keep_alive="1h"               # Mantiene el modelo cargado en la VRAM/RAM durante 1 hora
        #     )
        response = await cliente.chat(
        model=model_name,
        messages=mensajes,
        stream=False,
        options=self.opciones_avanzadas,
        #tools=herramientas_lista, 
        keep_alive="1h"
        )

        # Evaluar si el modelo decidió usar la herramienta (Tool Calling)
        if response.message.tool_calls:
            logging.info("[*] El modelo decidió usar una herramienta...")
            for tool in response.message.tool_calls:
                nombre_func = tool.function.name
                argumentos = tool.function.arguments
                logging.info(f"    -> Ejecutando '{nombre_func}' con argumentos: {argumentos}")
                
                # Ejecutar la función real de Python
                if nombre_func in HERRAMIENTAS_DISPONIBLES:
                    resultado = HERRAMIENTAS_DISPONIBLES[nombre_func](**argumentos)
                    
                    # Añadir la respuesta de la herramienta a la conversación
                    mensajes.append(response.message) # Agregamos el llamado a la herramienta
                    mensajes.append({'role': 'tool', 'content': resultado, 'name': nombre_func})
            
            # Segunda llamada a chat() para que el modelo lea el resultado y responda al usuario
            logging.info("[*] Generando respuesta final con los datos de la herramienta...")
            respuesta_final = await cliente.chat( 
                model=model_name,
                messages=mensajes,
                options=self.opciones_avanzadas
            )
            return respuesta_final.message.content
        else:
            return response.message.content

    async def chat_avanzado_stream(self, question: str, model_name: str, local_nube: str):
            """Generador asíncrono que devuelve la respuesta palabra por palabra."""
            logging.info(f"\n[*] Iniciando chat en STREAMING con {model_name}...")
            
            cliente = self.ollama_local if local_nube == "local" else self.ollama_nube
            
            mensajes = [
                {'role': 'system', 'content': 'Eres un asistente útil y conciso.'},
                {'role': 'user', 'content': question}
            ]

            # Al usar stream=True, Ollama devuelve un iterador asíncrono
            respuesta_stream = await cliente.chat(
                model=model_name,
                messages=mensajes,
                stream=True, 
                options=self.opciones_avanzadas,
                keep_alive="1h"
            )

            # Iteramos sobre los pedacitos (chunks) a medida que llegan
            async for chunk in respuesta_stream:
                if 'message' in chunk and 'content' in chunk['message']:
                    # 'yield' escupe el texto y pausa la función hasta el siguiente ciclo
                    yield chunk['message']['content']        

    async def obtener_embeddings(self, texto: str, model_name: str):
        """Usa el método embed() para convertir texto en vectores (útil para RAG)."""
        logger = logging.getLogger(__name__)
        logging.info("\n[*] Generando embeddings (representación vectorial)...")
        # Método embed(): Transforma texto en un array de números de alta dimensionalidad
        respuesta = await self.ollama_local.embed(model=model_name, input=texto)
        logging.info(f"[+] Dimensión del vector generado: {len(respuesta.embeddings[0])}")
        return respuesta.embeddings

    async def estado_del_servidor(self):
        """Usa el método ps() para ver los modelos cargados actualmente en memoria."""
        logging.info("\n[*] Modelos actualmente corriendo en la memoria (RAM/VRAM):")
        # Método ps(): Devuelve los procesos/modelos activos
        estado = await self.ollama_local.ps()
        for modelo in estado['models']:
            logging.info(f"    - Modelo: {modelo['name']} | Tamaño: {modelo['size_vram']} bytes en VRAM")

# -------------------------------------------------------------------
# 4. FUNCIÓN PRINCIPAL DE EJECUCIÓN (ENTRY POINT)
# -------------------------------------------------------------------

async def main():
    # Inicializamos nuestro gestor
    gestor = OllamaAvanzado()
    
    # 1. Preparar el modelo (Pull)
    #await gestor.preparar_modelo(MODEL_NAME)
    
    # 2. (Opcional) Crear un modelo modificado
    # await gestor.crear_modelo_personalizado("gemma3-experto", MODEL_NAME)
    
    # 3. Chat avanzado con Tool Calling
    pregunta = "El acetaminofen es un antibiotico?"
    respuesta_chat = await gestor.chat_avanzado(pregunta, MODEL_LLM_LOCAL,'local')
    logging.info("\n[🤖 RESPUESTA DEL MODELO]:")
    logging.info(respuesta_chat)
    
    # 4. Generar Embeddings
    #await gestor.obtener_embeddings("Este texto será convertido en números.", MODEL_NAME)
    
    # 5. Ver qué modelos están ocupando memoria
    await gestor.estado_del_servidor()

# Ejecutar el bucle asíncrono
if __name__ == "__main__":
    asyncio.run(main())
