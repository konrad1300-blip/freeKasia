"""
Moduł bazy wektorowej ChromaDB
Zarządzanie embeddingami i wyszukiwanie semantyczne
"""

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VectorDatabase:
    """Klasa do zarządzania bazą wektorową ChromaDB"""
    
    def __init__(self, db_path: Path, collection_name: str, embedding_model_name: str):
        """
        Inicjalizacja bazy wektorowej
        
        Args:
            db_path: Ścieżka do katalogu bazy danych
            collection_name: Nazwa kolekcji
            embedding_model_name: Nazwa modelu embeddingów
        """
        self.db_path = db_path
        self.collection_name = collection_name
        self.embedding_model_name = embedding_model_name
        
        # Inicjalizacja klienta ChromaDB
        self.client = chromadb.PersistentClient(path=str(db_path))
        
        # Ładowanie modelu embeddingów
        logger.info(f"Ładowanie modelu embeddingów: {embedding_model_name}")
        self.embedding_model = SentenceTransformer(embedding_model_name)
        
        # Pobieranie lub tworzenie kolekcji
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        logger.info(f"Zainicjalizowano bazę wektorową: {collection_name}")
    
    def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """
        Dodaje dokumenty do bazy wektorowej
        
        Args:
            documents: Lista dokumentów z polami 'id', 'text' i metadanymi
        """
        if not documents:
            logger.warning("Brak dokumentów do dodania")
            return
        
        # Przygotowanie danych do dodania
        ids = []
        texts = []
        metadatas = []
        
        for doc in documents:
            if "id" not in doc or "text" not in doc:
                logger.warning(f"Dokument nie ma wymaganych pól: {doc}")
                continue
            
            ids.append(str(doc["id"]))
            texts.append(doc["text"])
            
            # Przygotowanie metadanych (usuwanie pola text)
            metadata = {k: v for k, v in doc.items() if k not in ["id", "text"]}
            # Konwersja wartości na typy obsługiwane przez ChromaDB
            metadata = self._sanitize_metadata(metadata)
            metadatas.append(metadata)
        
        if not ids:
            logger.warning("Brak poprawnych dokumentów do dodania")
            return
        
        # Generowanie embeddingów
        logger.info(f"Generowanie embeddingów dla {len(texts)} dokumentów...")
        embeddings = self.embedding_model.encode(texts).tolist()
        
        # Dodawanie do kolekcji
        self.collection.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas
        )
        
        logger.info(f"Dodano {len(ids)} dokumentów do bazy wektorowej")
    
    def _sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanityzuje metadane do formatu obsługiwanego przez ChromaDB
        
        Args:
            metadata: Oryginalne metadane
            
        Returns:
            Zsanitowane metadane
        """
        sanitized = {}
        
        for key, value in metadata.items():
            if isinstance(value, (str, int, float, bool)):
                sanitized[key] = value
            elif isinstance(value, list):
                # Konwersja list na stringi
                sanitized[key] = json.dumps(value, ensure_ascii=False)
            elif isinstance(value, dict):
                # Konwersja słowników na stringi
                sanitized[key] = json.dumps(value, ensure_ascii=False)
            else:
                # Konwersja innych typów na stringi
                sanitized[key] = str(value)
        
        return sanitized
    
    def search(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        Wyszukuje dokumenty na podstawie zapytania
        
        Args:
            query: Zapytanie tekstowe
            n_results: Liczba wyników do zwrócenia
            
        Returns:
            Lista pasujących dokumentów z wynikami podobieństwa
        """
        if not query.strip():
            logger.warning("Puste zapytanie")
            return []
        
        # Generowanie embeddingu zapytania
        query_embedding = self.embedding_model.encode([query]).tolist()[0]
        
        # Wyszukiwanie w kolekcji
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )
        
        # Formatowanie wyników
        formatted_results = []
        
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                result = {
                    "id": results["ids"][0][i],
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i],
                    "similarity": 1 - results["distances"][0][i]  # Konwersja odległości na podobieństwo
                }
                formatted_results.append(result)
        
        logger.info(f"Znaleziono {len(formatted_results)} wyników dla zapytania: {query[:50]}...")
        
        return formatted_results
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Pobiera statystyki kolekcji
        
        Returns:
            Słownik ze statystykami
        """
        count = self.collection.count()
        
        return {
            "collection_name": self.collection_name,
            "document_count": count,
            "embedding_model": self.embedding_model_name
        }
    
    def delete_collection(self) -> None:
        """Usuwa kolekcję"""
        try:
            self.client.delete_collection(self.collection_name)
            logger.info(f"Usunięto kolekcję: {self.collection_name}")
        except Exception as e:
            logger.error(f"Błąd usuwania kolekcji: {str(e)}")
    
    def clear_collection(self) -> None:
        """Czyści kolekcję (usuwa wszystkie dokumenty)"""
        try:
            self.delete_collection()
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Wyczyszczono kolekcję: {self.collection_name}")
        except Exception as e:
            logger.error(f"Błąd czyszczenia kolekcji: {str(e)}")
    
    def update_document(self, doc_id: str, document: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Aktualizuje dokument w bazie
        
        Args:
            doc_id: ID dokumentu
            document: Nowy tekst dokumentu
            metadata: Nowe metadane (opcjonalnie)
        """
        try:
            # Generowanie nowego embeddingu
            embedding = self.embedding_model.encode([document]).tolist()[0]
            
            # Przygotowanie metadanych
            if metadata:
                metadata = self._sanitize_metadata(metadata)
            
            # Aktualizacja dokumentu
            self.collection.update(
                ids=[doc_id],
                documents=[document],
                embeddings=[embedding],
                metadatas=[metadata] if metadata else None
            )
            
            logger.info(f"Zaktualizowano dokument: {doc_id}")
            
        except Exception as e:
            logger.error(f"Błąd aktualizacji dokumentu {doc_id}: {str(e)}")
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Pobiera dokument po ID
        
        Args:
            doc_id: ID dokumentu
            
        Returns:
            Dokument lub None jeśli nie znaleziono
        """
        try:
            result = self.collection.get(
                ids=[doc_id],
                include=["documents", "metadatas"]
            )
            
            if result["ids"]:
                return {
                    "id": result["ids"][0],
                    "document": result["documents"][0],
                    "metadata": result["metadatas"][0] if result["metadatas"] else {}
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Błąd pobierania dokumentu {doc_id}: {str(e)}")
            return None


def create_vector_db(db_path: Path, collection_name: str, embedding_model_name: str) -> VectorDatabase:
    """
    Tworzy instancję bazy wektorowej
    
    Args:
        db_path: Ścieżka do katalogu bazy danych
        collection_name: Nazwa kolekcji
        embedding_model_name: Nazwa modelu embeddingów
        
    Returns:
        Instancja VectorDatabase
    """
    return VectorDatabase(db_path, collection_name, embedding_model_name)


if __name__ == "__main__":
    # Test bazy wektorowej
    from config import VECTOR_DB_DIR, COLLECTION_NAME, EMBEDDING_MODEL
    
    print("Test bazy wektorowej ChromaDB...")
    
    # Tworzenie bazy
    db = create_vector_db(VECTOR_DB_DIR, COLLECTION_NAME, EMBEDDING_MODEL)
    
    # Dodawanie przykładowych dokumentów
    sample_docs = [
        {
            "id": "test_1",
            "text": "Element konstrukcyjny o długości 5 metrów bieżących",
            "length": 5.0,
            "type": "beam"
        },
        {
            "id": "test_2",
            "text": "Płyta o powierzchni 12 metrów kwadratowych",
            "area": 12.0,
            "type": "plate"
        },
        {
            "id": "test_3",
            "text": "Śruba M10, ilość 20 sztuk",
            "quantity": 20,
            "type": "bolt"
        }
    ]
    
    db.add_documents(sample_docs)
    
    # Test wyszukiwania
    results = db.search("jaka jest długość elementu?")
    
    print(f"\nWyniki wyszukiwania:")
    for result in results:
        print(f"  - {result['document']} (podobieństwo: {result['similarity']:.2f})")
    
    # Statystyki
    stats = db.get_collection_stats()
    print(f"\nStatystyki bazy:")
    print(f"  Dokumentów: {stats['document_count']}")
    print(f"  Model: {stats['embedding_model']}")
