"""
Moduł przetwarzania plików Excel
Odczyt i przetwarzanie właściwości z arkuszy kalkulacyjnych
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExcelProcessor:
    """Klasa do przetwarzania plików Excel z właściwościami elementów"""
    
    def __init__(self):
        self.data = None
        self.processed_data = []
    
    def load_excel(self, file_path: Path, sheet_name: Optional[str] = None) -> bool:
        """
        Wczytuje plik Excel
        
        Args:
            file_path: Ścieżka do pliku Excel
            sheet_name: Nazwa arkusza (opcjonalnie)
            
        Returns:
            True jeśli wczytano pomyślnie
        """
        try:
            logger.info(f"Wczytywanie pliku Excel: {file_path}")
            
            if sheet_name:
                self.data = pd.read_excel(file_path, sheet_name=sheet_name)
            else:
                self.data = pd.read_excel(file_path)
            
            logger.info(f"Wczytano {len(self.data)} wierszy z {len(self.data.columns)} kolumnami")
            logger.info(f"Kolumny: {list(self.data.columns)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Błąd wczytywania pliku Excel: {str(e)}")
            return False
    
    def process_data(self) -> List[Dict[str, Any]]:
        """
        Przetwarza dane z Excela na format odpowiedni do embeddingu
        
        Returns:
            Lista przetworzonych rekordów
        """
        if self.data is None:
            logger.error("Nie wczytano danych z Excela")
            return []
        
        self.processed_data = []
        
        for idx, row in self.data.iterrows():
            try:
                record = self._process_row(row, idx)
                if record:
                    self.processed_data.append(record)
            except Exception as e:
                logger.warning(f"Błąd przetwarzania wiersza {idx}: {str(e)}")
        
        logger.info(f"Przetworzono {len(self.processed_data)} rekordów")
        return self.processed_data
    
    def _process_row(self, row: pd.Series, row_idx: int) -> Optional[Dict[str, Any]]:
        """
        Przetwarza pojedynczy wiersz danych
        
        Args:
            row: Wiersz danych z pandas
            row_idx: Indeks wiersza
            
        Returns:
            Słownik z przetworzonymi danymi
        """
        record = {
            "id": f"excel_row_{row_idx}",
            "source": "excel",
            "row_index": row_idx
        }
        
        # Mapowanie kolumn na standardowe właściwości
        column_mapping = {
            # Nazwy elementów
            "nazwa": "name",
            "name": "name",
            "element": "name",
            "typ": "type",
            "type": "type",
            
            # Wymiary
            "długość": "length",
            "dlugosc": "length",
            "length": "length",
            "dł": "length",
            "dl": "length",
            
            # Powierzchnie
            "powierzchnia": "area",
            "area": "area",
            "pow": "area",
            
            # Ilości
            "ilość": "quantity",
            "ilosc": "quantity",
            "quantity": "quantity",
            "sztuki": "quantity",
            "szt": "quantity",
            
            # Czasy
            "czas": "time",
            "time": "time",
            "czas_h": "time",
            "godziny": "time",
            
            # Jednostki
            "jednostka": "unit",
            "unit": "unit",
            
            # Opisy
            "opis": "description",
            "description": "description",
            "komentarz": "description",
            
            # Kategorie
            "kategoria": "category",
            "category": "category",
            "grupa": "category"
        }
        
        # Przetwarzanie kolumn
        for col_name, value in row.items():
            if pd.isna(value):
                continue
            
            col_lower = str(col_name).lower().strip()
            
            # Mapowanie nazw kolumn
            standard_name = None
            for key, mapped in column_mapping.items():
                if key in col_lower:
                    standard_name = mapped
                    break
            
            if standard_name:
                # Konwersja wartości
                if standard_name in ["length", "area", "quantity", "time"]:
                    try:
                        record[standard_name] = float(value)
                    except (ValueError, TypeError):
                        record[standard_name] = value
                else:
                    record[standard_name] = str(value).strip()
            else:
                # Zachowanie oryginalnych kolumn
                record[f"original_{col_name}"] = str(value).strip()
        
        # Tworzenie tekstu do embeddingu
        record["text"] = self._create_embedding_text(record)
        
        return record
    
    def _create_embedding_text(self, record: Dict[str, Any]) -> str:
        """
        Tworzy tekst do embeddingu na podstawie rekordu
        
        Args:
            record: Rekord z danymi
            
        Returns:
            Tekst gotowy do embeddingu
        """
        parts = []
        
        # Nazwa elementu
        if "name" in record:
            parts.append(f"Element: {record['name']}")
        
        # Typ elementu
        if "type" in record:
            parts.append(f"Typ: {record['type']}")
        
        # Kategoria
        if "category" in record:
            parts.append(f"Kategoria: {record['category']}")
        
        # Właściwości liczbowe
        if "length" in record:
            parts.append(f"Długość: {record['length']} metrów bieżących")
        
        if "area" in record:
            parts.append(f"Powierzchnia: {record['area']} metrów kwadratowych")
        
        if "quantity" in record:
            parts.append(f"Ilość: {record['quantity']} sztuk")
        
        if "time" in record:
            parts.append(f"Czas wykonania: {record['time']} godzin")
        
        # Opis
        if "description" in record:
            parts.append(f"Opis: {record['description']}")
        
        # Jednostka
        if "unit" in record:
            parts.append(f"Jednostka: {record['unit']}")
        
        # Dodatkowe oryginalne kolumny
        for key, value in record.items():
            if key.startswith("original_"):
                col_name = key.replace("original_", "")
                parts.append(f"{col_name}: {value}")
        
        return ". ".join(parts)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Oblicza statystyki z przetworzonych danych
        
        Returns:
            Słownik ze statystykami
        """
        if not self.processed_data:
            return {}
        
        stats = {
            "total_records": len(self.processed_data),
            "records_with_length": 0,
            "records_with_area": 0,
            "records_with_quantity": 0,
            "records_with_time": 0,
            "total_length": 0.0,
            "total_area": 0.0,
            "total_quantity": 0.0,
            "total_time": 0.0
        }
        
        for record in self.processed_data:
            if "length" in record and isinstance(record["length"], (int, float)):
                stats["records_with_length"] += 1
                stats["total_length"] += record["length"]
            
            if "area" in record and isinstance(record["area"], (int, float)):
                stats["records_with_area"] += 1
                stats["total_area"] += record["area"]
            
            if "quantity" in record and isinstance(record["quantity"], (int, float)):
                stats["records_with_quantity"] += 1
                stats["total_quantity"] += record["quantity"]
            
            if "time" in record and isinstance(record["time"], (int, float)):
                stats["records_with_time"] += 1
                stats["total_time"] += record["time"]
        
        return stats
    
    def search_records(self, query: str, field: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Wyszukuje rekordy na podstawie zapytania
        
        Args:
            query: Zapytanie tekstowe
            field: Pole do przeszukania (opcjonalnie)
            
        Returns:
            Lista pasujących rekordów
        """
        if not self.processed_data:
            return []
        
        query_lower = query.lower()
        results = []
        
        for record in self.processed_data:
            match = False
            
            if field:
                # Przeszukiwanie konkretnego pola
                if field in record:
                    field_value = str(record[field]).lower()
                    if query_lower in field_value:
                        match = True
            else:
                # Przeszukiwanie wszystkich pól
                for key, value in record.items():
                    if isinstance(value, str) and query_lower in value.lower():
                        match = True
                        break
                    elif isinstance(value, (int, float)) and query_lower in str(value):
                        match = True
                        break
            
            if match:
                results.append(record)
        
        return results
    
    def export_to_json(self, output_path: Path) -> None:
        """Eksportuje przetworzone dane do pliku JSON"""
        import json
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.processed_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Wyeksportowano dane do: {output_path}")
        except Exception as e:
            logger.error(f"Błąd eksportu do JSON: {str(e)}")


def process_excel_file(file_path: Path) -> List[Dict[str, Any]]:
    """
    Przetwarza plik Excel i zwraca przetworzone dane
    
    Args:
        file_path: Ścieżka do pliku Excel
        
    Returns:
        Lista przetworzonych rekordów
    """
    processor = ExcelProcessor()
    
    if processor.load_excel(file_path):
        return processor.process_data()
    
    return []


if __name__ == "__main__":
    # Test przetwarzania
    from config import EXCEL_FILE
    
    print("Test przetwarzania pliku Excel...")
    
    if EXCEL_FILE.exists():
        results = process_excel_file(EXCEL_FILE)
        
        print(f"\nPrzetworzono {len(results)} rekordów")
        
        for i, record in enumerate(results[:5]):  # Pokaż pierwsze 5
            print(f"\nRekord {i+1}:")
            print(f"  Tekst: {record.get('text', 'Brak tekstu')}")
    else:
        print(f"Plik Excel nie istnieje: {EXCEL_FILE}")
        print("Utwórz przykładowy plik Excel z danymi elementów.")
