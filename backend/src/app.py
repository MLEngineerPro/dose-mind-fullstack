# FastApi
from fastapi import FastAPI,Body, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic
from fastapi.responses import StreamingResponse 

from contextlib import asynccontextmanager
from typing import List, Optional
from pydantic import BaseModel,  Field
from ask_embeddings import ChatRAGHibrido, create_chroma_client
from sqlite_functions import search_items, search_rates
from oracle_functions import search_sku_prices_stock
from rag_retriever import InventoryRetriever

from ask_ollama import OllamaAvanzado
from config import MODEL_LLM_LOCAL, MODEL_LLM_NUBE 
import pathlib,logging
from logging.handlers import TimedRotatingFileHandler
import sys


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
# Estado global de la aplicación
# ─────────────────────────────────────────────
app_state: dict = {}

# ─────────────────────────────────────────────
# Lifespan: se ejecuta al ARRANCAR y al CERRAR
# ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── ARRANQUE ──────────────────────────────
    # ChromaDB se carga UNA SOLA VEZ aquí
    coleccion = create_chroma_client(collection_name="base_conocimiento")
    app_state["rag"] = ChatRAGHibrido(coleccion=coleccion)
 
    yield  # La app corre normalmente entre yield y el bloque de cierre
 
    # ── CIERRE ────────────────────────────────
    # Aquí puedes cerrar conexiones si fuera necesario
    app_state.clear()

app = FastAPI(lifespan=lifespan)
app.title="API Consulta relacionadas a medicamentos y presentaciones en droguería"
app.version="0.0.1"
app.description="API Consulta relacionadas a medicamentos y presentaciones en droguería"

# ─────────────────────────────────────────────
# Dependencia: inyecta el RAG en cada endpoint
# ─────────────────────────────────────────────
def get_rag() -> ChatRAGHibrido:
    """
    Retorna la instancia de RAG ya inicializada.
    No recarga ChromaDB, solo devuelve el objeto del app_state.
    """
    return app_state["rag"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

#gestor_ollama = OllamaAvanzado()

# Inicialización
#name_collection = 'base_conocimiento'
#chat_ollama = ChatRAGHibrido(name_collection)

# 1. Instanciamos el esquema de seguridad HTTPBasic
security = HTTPBasic()

# --- MODELOS ---
class ChatRequest(BaseModel):
    pregunta: str = Field(..., description="La pregunta para el modelo")
    inference_model: Optional[str] = Field(default=MODEL_LLM_NUBE)
    instancia: Optional[str] = Field(default="nube")

class ChatResponse(BaseModel):
    respuesta: str

# # Definimos el esquema de la petición esperada usando Pydantic
# class ChatRequest(BaseModel):
#     pregunta: str = Field(..., description="La pregunta que le quieres hacer al modelo")
#     modelo: Optional[str] = Field(default=MODEL_LLM_LOCAL, description="El nombre del modelo a usar")
#     entorno: Optional[str] = Field(default="local", description="'local' o 'nube'")

# # Definimos el esquema de la respuesta
# class ChatResponse(BaseModel):
#     respuesta: str

# Definimos la estructura de lo que recibimos
class RateQuery(BaseModel):
    items: List[str]

@app.get("/search")
def search(q: str):
    if len(q) < 5: 
        return {"message": "Query too short"}
    return search_items(q)
    

@app.post("/rates")
async def handle_search_sku(
    data: dict = Body(...),
    ):
    codigos_medicamentos = data.get("codigos_medicamentos", None)
    if not codigos_medicamentos:
        raise HTTPException(status_code=400, detail="El campo 'codigos_medicamentos' es obligatorio.")

    # Consulta a Oracle
    #resultado_raw = await search_sku_prices_stock(str(codigos_medicamentos))

    # Consulta a sqllite
    resultado_raw =  search_rates(codigos_medicamentos)
    return {"data": resultado_raw}  

# Instancia global del servicio
inventory_service = InventoryRetriever()

@app.post("/semantic_search")
async def search_inventory(
    query: str = Query(..., description="Nombre o descripción del medicamento", min_length=5),
    limit: int = Query(5, ge=1, le=20, description="Número de resultados a devolver")
):
    """
    Realiza una búsqueda semántica en la base de datos vectorial de medicamentos.
    """
    try:
        results = inventory_service.search(query, limit)
        return {
            "query": query,
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno en la búsqueda: {str(e)}")

# @app.post("/chat/stream")
# async def chat_stream_endpoint(request: ChatRequest):
#     """
#     Endpoint de Streaming. Devuelve la respuesta token por token (Server-Sent Events).
#         {
#         "pregunta": "Que es un antibiotico?",
#         "modelo": "llama3.2",
#         "entorno": "local"
#         }
#     """
#     try:
#         modelo_seguro = request.modelo or MODEL_LLM_LOCAL
#         entorno_seguro = request.entorno or "local"

#         # No usamos 'await' aquí porque es un generador, se lo pasamos directamente a StreamingResponse
#         generador = gestor_ollama.chat_avanzado_stream(
#             question=request.pregunta,
#             model_name=modelo_seguro,
#             local_nube=entorno_seguro
#         )
        
#         # Retornamos la respuesta indicando que es un flujo de texto (text/plain o text/event-stream)
#         return StreamingResponse(generador, media_type="text/plain")
    
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

# @app.post("/ask_embeddings")
# async def ask_embeddings(request: ChatRequest):
#     """
#     Endpoint tradicional. Espera a que se genere toda la respuesta antes de devolverla.
#     {
#         "pregunta": "Que es un antibiotico?",
#         "modelo": "llama3.2",
#         "entorno": "local"
#     }
#     """
#     try:
#         modelo_seguro = request.modelo or MODEL_LLM_LOCAL
#         entorno_seguro = request.entorno or "local"

#         # Aquí sí usamos 'await' porque queremos esperar a que se genere toda la respuesta
#         respuesta_completa = await gestor_ollama.chat_avanzado(
#             question=request.pregunta,
#             model_name=modelo_seguro,
#             local_nube=entorno_seguro
#         )
        
#         return ChatResponse(respuesta=respuesta_completa)
    
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")



# @app.post("/chat")
# async def chat_endpoint(request: ChatRequest):
#     """Respuesta en Streaming (palabra por palabra)."""
#     try:
#         generador = chat_ollama.consultar_stream(
#             request.pregunta, 
#             request.inference_model,
#             request.instancia
#         )
#         return StreamingResponse(generador, media_type="text/plain")
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
    

@app.post("/chat")
async def consultar(
    body: ChatRequest,
    rag: ChatRAGHibrido = Depends(get_rag)   # ← inyección de dependencia
):
    """
    Responde en streaming. El cliente recibe los fragmentos
    a medida que el modelo los genera.
    """
    #modelo = MODEL_LLM_NUBE if body.instancia == "Nube" else MODEL_LLM_LOCAL
    #logger.info(f"Modelo seleccionado {modelo}")
 
    async def generador():
        async for fragmento in rag.consultar_stream(
            pregunta=body.pregunta,
            inference_model=body.inference_model,
            instancia=body.instancia
        ):
            yield fragmento
 
    return StreamingResponse(generador(), media_type="text/plain")

@app.get("/health")
def salud():
    """Endpoint para verificar que la API está viva."""
    return {"estado": "ok", "documentos": app_state["rag"].coleccion.count()}

if __name__=="__main__":
    
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)