import chromadb
from typing import List, Dict
from ollama_embeddings import OllamaEmbedder
import pathlib

VECTORS_PATH = pathlib.Path(__file__).parent.parent / "chroma_db"
VECTOR_DB_PATH = VECTORS_PATH / "inventory_vdb"
COLLECTION_NAME = "medicamentos_inventario"


class InventoryRetriever:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
        self.collection = self.client.get_collection(name=COLLECTION_NAME)
        self.embedder = OllamaEmbedder()

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Busca artículos relevantes usando embeddings consistentes
        """
        query_embedding = self.embedder([query])[0]

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["metadatas", "documents", "distances"],
        )
        items = []
        for i in range(len(results["ids"][0])):
            items.append(
                {
                    "codigo": results["metadatas"][0][i]["Codigo"],
                    "nombre": results["metadatas"][0][i]["Medicamento"],
                    "Accion Terapeutica": results["metadatas"][0][i]["Accion Terapeutica"],
                    "score": results["distances"][0][i],
                }
            )

        return items


if __name__ == "__main__":
    retriever = InventoryRetriever()
    items = retriever.search("zulexta")

    
    for item in items:
        if item['score'] < 0.5:  # Adjust the threshold as
            print(item)
