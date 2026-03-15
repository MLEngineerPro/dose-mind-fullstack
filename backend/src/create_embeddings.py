import os
import pathlib
import logging
import time
import glob
import chromadb
from chromadb.utils import embedding_functions # <-- NUEVO: Para usar integraciones nativas
import sqlite3
import json
import pymupdf as fitz

# Import config Ollama
from backend.src.config import HOST_OLLAMA_LOCAL
from backend.src.config import MODEL_EMBEDDINGS 


# Configuración de rutas
BASE_DIR = pathlib.Path(__file__).parent.parent
VECTORS_PATH = BASE_DIR / "chroma_db"
DOCS_PATH = BASE_DIR / "docs"

# Ruta para la base de datos SQLite
SQLITE_DB_PATH = BASE_DIR / "output" / "historial_consultas.db"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# =================================================================
# 1. CONFIGURACIÓN DE OLLAMA PARA EMBEDDINGS
# =================================================================
ollama_ef = embedding_functions.OllamaEmbeddingFunction(
    url=HOST_OLLAMA_LOCAL +  "/api/embeddings",
    model_name=MODEL_EMBEDDINGS
)

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 150):
    """Divide un texto largo en fragmentos más pequeños con un margen de superposición."""
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap 
    return chunks

def extract_text_from_file(file_path: str):
    """Detecta el tipo de archivo y extrae su texto dividiéndolo en fragmentos."""
    ext = os.path.splitext(file_path)[1].lower()
    nombre_archivo = os.path.basename(file_path)
    document_chunks = []

    if ext == '.txt':
        with open(file_path, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        fragmentos = chunk_text(contenido)
        for i, fragmento in enumerate(fragmentos):
            document_chunks.append({
                "texto": fragmento,
                "metadata": {
                    "origen": nombre_archivo,
                    "ubicacion": f"Fragmento {i + 1}"
                }
            })
            
    elif ext == '.pdf':
        doc = fitz.open(file_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            texto_pagina = page.get_text("text")
            
            if texto_pagina.strip():
                fragmentos = chunk_text(texto_pagina)
                for i, fragmento in enumerate(fragmentos):
                    document_chunks.append({
                        "texto": fragmento,
                        "metadata": {
                            "origen": nombre_archivo,
                            "ubicacion": f"Página {page_num + 1} (Frag. {i + 1})"
                        }
                    })
        doc.close()
    else:
        logger.warning(f"⚠️ Formato no soportado ignorado: {nombre_archivo}")

    return document_chunks

def load_and_vectorize_documents():
    """Lee archivos TXT/PDF, los fragmenta y los guarda en ChromaDB usando Ollama."""
    os.makedirs(VECTORS_PATH, exist_ok=True)
    os.makedirs(DOCS_PATH, exist_ok=True)
    
    client = chromadb.PersistentClient(path=str(VECTORS_PATH))
    
    try:
        client.delete_collection(name="base_conocimiento")
    except:
        pass

    # Creamos la colección y le pasamos la función de embeddings de Ollama
    collection = client.get_or_create_collection(
        name="base_conocimiento",
        embedding_function=ollama_ef 
    )
    
    archivos_txt = glob.glob(f"{DOCS_PATH}/*.txt")
    archivos_pdf = glob.glob(f"{DOCS_PATH}/*.pdf")
    todos_los_archivos = archivos_txt + archivos_pdf
    
    if not todos_los_archivos:
        logger.warning(f"❌ No se encontraron archivos .txt ni .pdf en {DOCS_PATH}")
        return collection

    documents = []
    metadatas = []
    ids = []
    doc_id_counter = 0
    
    for archivo_ruta in todos_los_archivos:
        logger.info(f"📄 Procesando documento: {os.path.basename(archivo_ruta)}")
        chunks_extraidos = extract_text_from_file(archivo_ruta)
        
        for chunk in chunks_extraidos:
            documents.append(chunk["texto"])
            metadatas.append(chunk["metadata"])
            ids.append(f"doc_{doc_id_counter}")
            doc_id_counter += 1

    logger.info(f"🚀 Iniciando vectorización local con Ollama de {len(documents)} fragmentos...")
    
    # Agregamos todo a ChromaDB. Chroma llamará a Ollama automáticamente.
    collection.add(documents=documents, metadatas=metadatas, ids=ids)
    
    logger.info("✅ Base de conocimiento construida exitosamente.")
    return collection

def get_collection():
    """Obtiene la colección existente de ChromaDB sin re-vectorizar."""
    client = chromadb.PersistentClient(path=str(VECTORS_PATH))
    return client.get_or_create_collection(
        name="base_conocimiento",
        embedding_function=ollama_ef
    )

def init_sqlite_db():
    os.makedirs(os.path.dirname(SQLITE_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historial_qa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            pregunta TEXT NOT NULL,
            respuesta TEXT NOT NULL,
            fuentes_utilizadas TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_interaction_to_db(pregunta: str, respuesta: str, fuentes: list):
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    fuentes_json = json.dumps(fuentes, ensure_ascii=False)
    cursor.execute('''
        INSERT INTO historial_qa (pregunta, respuesta, fuentes_utilizadas)
        VALUES (?, ?, ?)
    ''', (pregunta, respuesta, fuentes_json))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    
    init_sqlite_db()
    
    # ---------------------------------------------------------
    # FLUJO DE TRABAJO
    # ---------------------------------------------------------
    # Paso 1: Vectorizar (Ejecutar solo si hay documentos nuevos)
    db_collection = load_and_vectorize_documents() 

    print(db_collection)
    
    # Paso 1 Alternativo: Si ya vectorizaste y solo quieres consultar, 
    # comenta la línea de arriba y descomenta esta:
    # db_collection = get_collection()

    # Paso 2: Probar una consulta
    #pregunta_prueba = "¿Qué información importante hay en los documentos?"
    
    #print(f"\n🔍 Buscando respuesta para: '{pregunta_prueba}'")
    #resultado = query_knowledge_base(pregunta_prueba, db_collection, API_KEY)
    
    #print("\n🤖 RESPUESTA GEMINI:")
    #print(resultado["respuesta"])
    
    #save_interaction_to_db(pregunta_prueba, resultado["respuesta"], resultado["referencias_encontradas"])