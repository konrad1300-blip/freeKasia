"""
Główna aplikacja chat z bazą wektorową i LLM Bielik
Integracja wszystkich modułów w interfejs Gradio
"""

import gradio as gr
from pathlib import Path
from typing import List, Dict, Any, Tuple
import logging
import json

from config import (
    VECTOR_DB_DIR, COLLECTION_NAME, EMBEDDING_MODEL,
    BIELIK_MODEL_NAME, LLM_TEMPERATURE, LLM_MAX_NEW_TOKENS,
    SYSTEM_PROMPT, APP_TITLE, APP_DESCRIPTION,
    EXCEL_FILE, DXF_DIR
)
from vector_db import VectorDatabase, create_vector_db
from llm_integration import BielikLLM, create_llm
from dxf_processor import DXFProcessor, process_dxf_directory
from excel_processor import ExcelProcessor, process_excel_file

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChatApplication:
    """Główna klasa aplikacji chat"""
    
    def __init__(self):
        """Inicjalizacja aplikacji"""
        self.vector_db = None
        self.llm = None
        self.is_initialized = False
        self.chat_history = []
        
        logger.info("Inicjalizacja aplikacji chat...")
    
    def initialize(self) -> Tuple[bool, str]:
        """
        Inicjalizuje wszystkie komponenty aplikacji
        
        Returns:
            Tuple (sukces, komunikat)
        """
        try:
            # Inicjalizacja bazy wektorowej
            logger.info("Inicjalizacja bazy wektorowej...")
            self.vector_db = create_vector_db(
                VECTOR_DB_DIR, 
                COLLECTION_NAME, 
                EMBEDDING_MODEL
            )
            
            # Inicjalizacja LLM
            logger.info("Inicjalizacja LLM Bielik...")
            self.llm = create_llm(
                BIELIK_MODEL_NAME,
                LLM_TEMPERATURE,
                LLM_MAX_NEW_TOKENS
            )
            
            self.is_initialized = True
            logger.info("Aplikacja zainicjalizowana pomyślnie")
            
            return True, "Aplikacja zainicjalizowana pomyślnie"
            
        except Exception as e:
            error_msg = f"Błąd inicjalizacji: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def load_model(self) -> Tuple[bool, str]:
        """
        Ładuje model LLM
        
        Returns:
            Tuple (sukces, komunikat)
        """
        if not self.is_initialized:
            return False, "Aplikacja nie jest zainicjalizowana"
        
        try:
            logger.info("Ładowanie modelu LLM...")
            success = self.llm.load_model()
            
            if success:
                return True, "Model załadowany pomyślnie"
            else:
                return False, "Błąd ładowania modelu"
                
        except Exception as e:
            error_msg = f"Błąd ładowania modelu: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def process_dxf_files(self) -> Tuple[bool, str, int]:
        """
        Przetwarza pliki DXF i dodaje do bazy wektorowej
        
        Returns:
            Tuple (sukces, komunikat, liczba dokumentów)
        """
        if not self.is_initialized:
            return False, "Aplikacja nie jest zainicjalizowana", 0
        
        try:
            logger.info("Przetwarzanie plików DXF...")
            
            # Sprawdzenie czy katalog istnieje
            if not DXF_DIR.exists():
                return False, f"Katalog DXF nie istnieje: {DXF_DIR}", 0
            
            # Przetwarzanie plików DXF
            processor = DXFProcessor()
            results = process_dxf_directory(DXF_DIR)
            
            if not results:
                return False, "Nie znaleziono plików DXF do przetworzenia", 0
            
            # Konwersja na dokumenty do bazy wektorowej
            documents = []
            for result in results:
                if "error" not in result:
                    doc = {
                        "id": f"dxf_{result['file_name']}",
                        "text": self._create_dxf_text(result),
                        "source": "dxf",
                        "file_name": result["file_name"],
                        "statistics": json.dumps(result["statistics"], ensure_ascii=False)
                    }
                    documents.append(doc)
            
            # Dodawanie do bazy wektorowej
            if documents:
                self.vector_db.add_documents(documents)
                return True, f"Przetworzono {len(documents)} plików DXF", len(documents)
            else:
                return False, "Nie udało się przetworzyć żadnego pliku DXF", 0
                
        except Exception as e:
            error_msg = f"Błąd przetwarzania plików DXF: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, 0
    
    def _create_dxf_text(self, result: Dict[str, Any]) -> str:
        """
        Tworzy tekst opisowy z wyników przetwarzania DXF
        
        Args:
            result: Wynik przetwarzania pliku DXF
            
        Returns:
            Tekst opisowy
        """
        stats = result.get("statistics", {})
        
        parts = [f"Plik DXF: {result['file_name']}"]
        
        if stats.get("total_elements"):
            parts.append(f"Liczba elementów: {stats['total_elements']}")
        
        if stats.get("total_length"):
            parts.append(f"Całkowita długość: {stats['total_length']:.2f} metrów bieżących")
        
        if stats.get("total_area"):
            parts.append(f"Całkowita powierzchnia: {stats['total_area']:.2f} metrów kwadratowych")
        
        if stats.get("total_quantity"):
            parts.append(f"Liczba elementów (sztuki): {stats['total_quantity']}")
        
        if stats.get("estimated_time_hours"):
            parts.append(f"Szacowany czas wykonania: {stats['estimated_time_hours']:.2f} godzin")
        
        return ". ".join(parts)
    
    def process_excel_file(self) -> Tuple[bool, str, int]:
        """
        Przetwarza plik Excel i dodaje do bazy wektorowej
        
        Returns:
            Tuple (sukces, komunikat, liczba dokumentów)
        """
        if not self.is_initialized:
            return False, "Aplikacja nie jest zainicjalizowana", 0
        
        try:
            logger.info("Przetwarzanie pliku Excel...")
            
            # Sprawdzenie czy plik istnieje
            if not EXCEL_FILE.exists():
                return False, f"Plik Excel nie istnieje: {EXCEL_FILE}", 0
            
            # Przetwarzanie pliku Excel
            processor = ExcelProcessor()
            if not processor.load_excel(EXCEL_FILE):
                return False, "Nie udało się wczytać pliku Excel", 0
            
            records = processor.process_data()
            
            if not records:
                return False, "Nie znaleziono danych w pliku Excel", 0
            
            # Konwersja na dokumenty do bazy wektorowej
            documents = []
            for record in records:
                doc = {
                    "id": f"excel_{record.get('id', len(documents))}",
                    "text": record.get("text", ""),
                    "source": "excel",
                    **{k: v for k, v in record.items() if k not in ["id", "text"]}
                }
                documents.append(doc)
            
            # Dodawanie do bazy wektorowej
            if documents:
                self.vector_db.add_documents(documents)
                return True, f"Przetworzono {len(documents)} rekordów z Excela", len(documents)
            else:
                return False, "Nie udało się przetworzyć danych z Excela", 0
                
        except Exception as e:
            error_msg = f"Błąd przetwarzania pliku Excel: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, 0
    
    def chat(self, message: str, history: List[List[str]]) -> Tuple[str, List[List[str]]]:
        """
        Główna funkcja chatu
        
        Args:
            message: Wiadomość użytkownika
            history: Historia czatu
            
        Returns:
            Tuple (odpowiedź, zaktualizowana historia)
        """
        if not self.is_initialized:
            return "Aplikacja nie jest zainicjalizowana. Kliknij 'Inicjalizuj aplikację'.", history
        
        if not self.llm.is_loaded():
            return "Model LLM nie jest załadowany. Kliknij 'Załaduj model LLM'.", history
        
        try:
            # Wyszukiwanie w bazie wektorowej
            logger.info(f"Wyszukiwanie dla zapytania: {message[:50]}...")
            search_results = self.vector_db.search(message, n_results=3)
            
            # Przygotowanie kontekstu
            context = self._prepare_context(search_results)
            
            # Generowanie odpowiedzi
            logger.info("Generowanie odpowiedzi...")
            response = self.llm.generate_with_context(
                question=message,
                context=context,
                system_prompt=SYSTEM_PROMPT
            )
            
            # Aktualizacja historii
            history.append([message, response])
            
            return "", history
            
        except Exception as e:
            error_msg = f"Błąd podczas przetwarzania zapytania: {str(e)}"
            logger.error(error_msg)
            return error_msg, history
    
    def _prepare_context(self, search_results: List[Dict[str, Any]]) -> str:
        """
        Przygotowuje kontekst z wyników wyszukiwania
        
        Args:
            search_results: Wyniki wyszukiwania z bazy wektorowej
            
        Returns:
            Sformatowany kontekst
        """
        if not search_results:
            return "Brak dostępnych danych w bazie."
        
        context_parts = []
        
        for i, result in enumerate(search_results, 1):
            similarity = result.get("similarity", 0)
            document = result.get("document", "")
            metadata = result.get("metadata", {})
            
            # Dodawanie tylko wyników z wystarczającym podobieństwem
            if similarity > 0.3:
                part = f"Wynik {i} (podobieństwo: {similarity:.2f}):\n{document}"
                
                # Dodawanie metadanych jeśli dostępne
                if metadata:
                    meta_str = ", ".join([f"{k}: {v}" for k, v in metadata.items() 
                                         if k not in ["source", "id"]])
                    if meta_str:
                        part += f"\nDodatkowe informacje: {meta_str}"
                
                context_parts.append(part)
        
        if not context_parts:
            return "Nie znaleziono wystarczająco podobnych danych w bazie."
        
        return "\n\n".join(context_parts)
    
    def get_status(self) -> str:
        """
        Pobiera status aplikacji
        
        Returns:
            Tekst statusu
        """
        status_parts = []
        
        status_parts.append(f"Zainicjalizowana: {'Tak' if self.is_initialized else 'Nie'}")
        
        if self.is_initialized:
            # Status bazy wektorowej
            db_stats = self.vector_db.get_collection_stats()
            status_parts.append(f"Dokumentów w bazie: {db_stats['document_count']}")
            
            # Status LLM
            llm_info = self.llm.get_model_info()
            status_parts.append(f"Model załadowany: {'Tak' if llm_info['is_loaded'] else 'Nie'}")
            status_parts.append(f"Temperatura: {llm_info['temperature']}")
        
        return "\n".join(status_parts)
    
    def clear_history(self) -> List[List[str]]:
        """Czyści historię czatu"""
        self.chat_history = []
        return []


def create_interface() -> gr.Blocks:
    """
    Tworzy interfejs Gradio
    
    Returns:
        Interfejs Gradio
    """
    # Tworzenie instancji aplikacji
    app = ChatApplication()
    
    # Tworzenie interfejsu
    with gr.Blocks(title=APP_TITLE, theme=gr.themes.Soft()) as interface:
        gr.Markdown(f"# {APP_TITLE}")
        gr.Markdown(APP_DESCRIPTION)
        
        with gr.Row():
            # Lewa kolumna - sterowanie
            with gr.Column(scale=1):
                gr.Markdown("## Panel sterowania")
                
                init_btn = gr.Button("Inicjalizuj aplikację", variant="primary")
                load_model_btn = gr.Button("Załaduj model LLM", variant="secondary")
                
                gr.Markdown("---")
                
                process_dxf_btn = gr.Button("Przetwórz pliki DXF", variant="secondary")
                process_excel_btn = gr.Button("Przetwórz plik Excel", variant="secondary")
                
                gr.Markdown("---")
                
                status_btn = gr.Button("Odśwież status", variant="secondary")
                clear_btn = gr.Button("Wyczyść historię", variant="secondary")
                
                gr.Markdown("---")
                
                status_output = gr.Textbox(
                    label="Status aplikacji",
                    value="Aplikacja nie zainicjalizowana",
                    interactive=False,
                    lines=5
                )
                
                operation_output = gr.Textbox(
                    label="Wynik operacji",
                    value="",
                    interactive=False,
                    lines=3
                )
            
            # Prawa kolumna - chat
            with gr.Column(scale=2):
                gr.Markdown## Chat")
                
                chatbot = gr.Chatbot(
                    label="Rozmowa z asystentem",
                    height=500
                )
                
                with gr.Row():
                    msg_input = gr.Textbox(
                        label="Twoje pytanie",
                        placeholder="Zadaj pytanie dotyczące właściwości elementów...",
                        scale=4
                    )
                    send_btn = gr.Button("Wyślij", variant="primary", scale=1)
                
                gr.Markdown("""
                **Przykładowe pytania:**
                - Jaka jest całkowita długość elementów?
                - Ile metrów kwadratowych powierzchni jest w rysunku?
                - Jaki jest szacowany czas wykonania?
                - Ile sztuk elementów typu A?
                """)
        
        # Funkcje obsługi zdarzeń
        def initialize_app():
            success, message = app.initialize()
            status = app.get_status()
            return status, message
        
        def load_model():
            success, message = app.load_model()
            status = app.get_status()
            return status, message
        
        def process_dxf():
            success, message, count = app.process_dxf_files()
            status = app.get_status()
            return status, message
        
        def process_excel():
            success, message, count = app.process_excel_file()
            status = app.get_status()
            return status, message
        
        def refresh_status():
            return app.get_status()
        
        def clear_history():
            history = app.clear_history()
            return history, "Historia wyczyszczona"
        
        def chat_response(message, history):
            return app.chat(message, history)
        
        # Podłączanie zdarzeń
        init_btn.click(
            initialize_app,
            outputs=[status_output, operation_output]
        )
        
        load_model_btn.click(
            load_model,
            outputs=[status_output, operation_output]
        )
        
        process_dxf_btn.click(
            process_dxf,
            outputs=[status_output, operation_output]
        )
        
        process_excel_btn.click(
            process_excel,
            outputs=[status_output, operation_output]
        )
        
        status_btn.click(
            refresh_status,
            outputs=[status_output]
        )
        
        clear_btn.click(
            clear_history,
            outputs=[chatbot, operation_output]
        )
        
        send_btn.click(
            chat_response,
            inputs=[msg_input, chatbot],
            outputs=[msg_input, chatbot]
        )
        
        msg_input.submit(
            chat_response,
            inputs=[msg_input, chatbot],
            outputs=[msg_input, chatbot]
        )
    
    return interface


def main():
    """Główna funkcja uruchamiająca aplikację"""
    print("=" * 60)
    print(APP_TITLE)
    print("=" * 60)
    print("\nUruchamianie interfejsu...")
    print("Otwórz przeglądarkę pod adresem: http://localhost:7860")
    print("\nAby zakończyć, naciśnij Ctrl+C")
    print("=" * 60)
    
    # Tworzenie i uruchamianie interfejsu
    interface = create_interface()
    interface.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )


if __name__ == "__main__":
    main()
