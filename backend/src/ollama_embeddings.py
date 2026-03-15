import ollama
import chromadb
from chromadb.utils.embedding_functions import EmbeddingFunction
import time
import pathlib
import csv
import os
from typing import List, Dict

### CONSTANTES
MODEL_NAME = "qwen3-embedding:0.6b-q8_0"  
# embeddinggemma:300m, qwen3-embedding:4b-q4_K_M, Optimizado para Tesla T4, otros 
# qwen3-embedding:latest, qwen3-embedding:0.6b-q8_0

BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", 32))

DATA_PATH = pathlib.Path(__file__).parent.parent / "data"
CSV_FILE = DATA_PATH / "medicamentos.csv"
COLLECTION_NAME = "medicamentos_inventario"
VECTORS_PATH = pathlib.Path(__file__).parent.parent / "chroma_db"
VECTOR_DB_PATH = VECTORS_PATH / "inventory_vdb"


def read_csv_to_dict(filepath: pathlib.Path) -> List[Dict]:
    """Lee un archivo CSV y lo convierte en una lista de diccionarios"""
    print(f" Leyendo archivo CSV desde {filepath}")

    if not filepath.exists():
        raise FileNotFoundError(f"No existe el archivo: {filepath}")

    with open(filepath, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        data = list(reader)

    if not data:
        raise ValueError("El CSV está vacío")
    
    print(f" Se leyeron {len(data)} registros")
    return data


class OllamaEmbedder(EmbeddingFunction):
    """
    EmbeddingFunction compatible con ChromaDB usando Ollama + Qwen3
    """

    def __init__(
        self,
        model_name: str = MODEL_NAME,
        num_gpu: int = 1,
        main_gpu: int = 0,
        base_url="http://localhost:11434"
    ):
        self.model_name = model_name
        self.options = {
            "num_gpu": num_gpu,
            "main_gpu": main_gpu,
            base_url: base_url,
        }

    def __call__(self, input_texts: List[str]) -> List[List[float]]:
        response = ollama.embed(
            model=self.model_name,
            input=input_texts,
            options=self.options,
        )

        embeddings = response.get("embeddings")
        if not embeddings:
            raise RuntimeError("Ollama no devolvió embeddings")

        return embeddings


def prepare_inventory_data():
    data = read_csv_to_dict(CSV_FILE)

    # Validar columnas requeridas
    #required = {"codigo_medicamento", "nombre_medicamento", "grupo_medicamento"}
    required = {"Codigo","Medicamento","Accion Terapeutica","Laboratorio"}

    
          
    if not required.issubset(data[0]):
        raise ValueError("El CSV no contiene las columnas requeridas")

    # Validar IDs duplicados
    ids = [item["Codigo"] for item in data]
    if len(ids) != len(set(ids)):
        raise ValueError("Existen códigos de medicamento duplicados en el CSV")

    # Texto optimizado semánticamente para embeddings
    processed_texts = [
        (
            f"Codigo {item['Codigo']}. "
            f"Nombre {item['Medicamento']}. "
            f"Accion Terapeutica  {item['Accion Terapeutica']}. "
            f"Laboratorio {item['Laboratorio']}."
        )
        for item in data
    ]

    metadatas = [
        {
            "Codigo": item["Codigo"],
            "Medicamento": item["Medicamento"],
            "Accion Terapeutica": item["Accion Terapeutica"],
        }
        for item in data
    ]

    return processed_texts, metadatas, ids


def update_vector_db():
    print(f"Creando embeddings con el modelo {MODEL_NAME} ")
    client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
    embedder = OllamaEmbedder()

    # Obtener o crear la colección SIN borrar nada
    try:
        collection = client.get_collection(name=COLLECTION_NAME)
        print("Colección existente encontrada. Se realizará UPSERT incremental.")
    except chromadb.errors.NotFoundError:
        collection = client.create_collection(
            name=COLLECTION_NAME,
            metadata={
                "hnsw:space": "cosine",
            },
        )
        print("Colección creada por primera vez.")

    texts, metas, ids = prepare_inventory_data()
    total = len(texts)

    print(f"Iniciando upsert de {total} artículos...")
    start_time = time.time()

    for i in range(0, total, BATCH_SIZE):
        batch_texts = texts[i : i + BATCH_SIZE]
        batch_metas = metas[i : i + BATCH_SIZE]
        batch_ids = ids[i : i + BATCH_SIZE]

        embeddings = embedder(batch_texts)

        collection.upsert(
            documents=batch_texts,
            embeddings=embeddings,
            metadatas=batch_metas,
            ids=batch_ids,
        )

        print(f"Upsert {min(i + BATCH_SIZE, total)}/{total}")

    

    end_time = time.time()
    print(f"Upsert finalizado en {end_time - start_time:.2f} segundos.")


if __name__ == "__main__":
    update_vector_db()
