# Plan Budowy Aplikacji FreeKasi

## Spis Treści

1. [Wprowadzenie](#wprowadzenie)
2. [Faza 0: Przygotowanie środowiska](#faza-0-przygotowanie-środowiska)
3. [Faza 1: Warstwa danych - Normalizator i procesory](#faza-1-warstwa-danych---normalizator-i-procesory)
4. [Faza 2: Warstwa pośrednia - Katalog JSON](#faza-2-warstwa-pośrednia---katalog-json)
5. [Faza 3: Warstwa wyszukiwania - Embedding i ChromaDB](#faza-3-warstwa-wyszukiwania---embedding-i-chromadb)
6. [Faza 4: Warstwa odpowiedzi - LLM](#faza-4-warstwa-odpowiedzi---llm)
7. [Faza 5: Interfejs użytkownika](#faza-5-interfejs-użytkownika)
8. [Faza 6: Testowanie i walidacja](#faza-6-testowanie-i-walidacja)
9. [Faza 7: Wdrożenie i optymalizacja](#faza-7-wdrożenie-i-optymalizacja)
10. [Podsumowanie techniczne](#podsumowanie-techniczne)

---

## Wprowadzenie

### Cel projektu

Stworzenie systemu RAG (Retrieval-Augmented Generation) dla firmy produkcyjnej, który łączy dane z:
- Systemu ERP/Excel (dane produkcyjne)
- Plików DXF (rysunki techniczne)
- Dokumentów PDF (instrukcje, specyfikacje)

System ma odpowiadać na pytania dotyczące produktów, procesów produkcyjnych i parametrów technicznych.

### Założenia techniczne

| Komponent | Specyfikacja |
|-----------|--------------|
| Procesor | AMD Ryzen 5 5600G (6C/12T) |
| RAM | 16 GB |
| GPU | Zintegrowany Radeon (brak CUDA) |
| System | CPU-only |

**Kluczowa decyzja**: Cały system projektowany pod CPU. Brak GPU oznacza konieczność wyboru lekkich modeli i optymalizacji pod kątem pamięci.

### Wybrane technologie

| Warstwa | Technologia | Uzasadnienie |
|---------|-------------|--------------|
| **LLM (budowa)** | Gemma 3 4B / Qwen2.5 3B | Lekkie, szybkie, dobre po polsku |
| **LLM (docelowo)** | Bielik 4B (GGUF) | Polski model, gdy będzie stabilny |
| **Embedding** | BAAI bge-m3 / nomic-embed-text | Specjalistyczne modele, małe wymagania |
| **Baza wektorowa** | ChromaDB | Lekka, Python, lokalna, darmowa |
| **Framework LLM** | llama.cpp / Ollama | Obsługa CPU, GGUF |

---

## Faza 0: Przygotowanie środowiska

### 0.1 Instalacja podstawowych narzędzi

```bash
# Instalacja Python 3.10+
# Instalacja Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pobranie modeli
ollama pull gemma3:4b
ollama pull qwen2.5:3b
ollama pull bge-m3
ollama pull nomic-embed-text

# Alternatywnie - llama.cpp
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
make
```

### 0.2 Struktura projektu

```
freekasi/
├── src/
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── excel_processor.py
│   │   ├── dxf_processor.py
│   │   ├── pdf_processor.py
│   │   └── normalizer.py
│   ├── embedding/
│   │   ├── __init__.py
│   │   └── embedder.py
│   ├── vector_db/
│   │   ├── __init__.py
│   │   └── chroma_client.py
│   ├── llm/
│   │   ├── __init__.py
│   │   └── llm_client.py
│   ├── pipeline/
│   │   ├── __init__.py
│   │   └── rag_pipeline.py
│   └── utils/
│       ├── __init__.py
│       └── validators.py
├── data/
│   ├── raw/          # Pliki źródłowe (Excel, DXF, PDF)
│   ├── staging/      # Ujednolicone JSON
│   ├── chroma/       # Baza wektorowa
│   └── tests/        # Zestawy testowe
├── tests/
│   ├── test_processors.py
│   ├── test_embedding.py
│   └── test_pipeline.py
├── config/
│   └── config.yaml
├── requirements.txt
└── README.md
```

### 0.3 Zależności Python

```txt
# requirements.txt
chromadb>=0.4.0
pandas>=2.0.0
openpyxl>=3.1.0
ezdxf>=1.0.0
pypdf>=3.0.0
pyyaml>=6.0
pydantic>=2.0.0
python-dotenv>=1.0.0
ollama>=0.1.0
numpy>=1.24.0
tiktoken>=0.5.0
sentence-transformers>=2.2.0  # alternatywa dla Ollama
pytest>=7.0.0
```

---

## Faza 1: Warstwa danych - Normalizator i procesory

### 1.1 Normalizator danych

**Cel**: Ujednolicenie danych technicznych z różnych źródeł.

**Zasady normalizacji**:

| Typ danych | Format docelowy | Przykład |
|------------|-----------------|----------|
| Długość | metry (m) | 2.4 m |
| Powierzchnia | m² | 0.52 m² |
| Objętość | m³ | 0.03 m³ |
| Masa | kilogramy (kg) | 3.2 kg |
| Czas | minuty | 18 min |
| Numer produktu | oryginalny | AI-000123 |
| Materiał | oryginalna nazwa | S235JR |

**Implementacja**:

```python
# src/processors/normalizer.py

import re
import json
from typing import Dict, Any, Optional

class DataNormalizer:
    """Normalizator danych technicznych."""
    
    def __init__(self, use_llm_for_ambiguous: bool = False):
        self.use_llm_for_ambiguous = use_llm_for_ambiguous
        
    def normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalizuje dane techniczne.
        
        Args:
            data: Słownik z danymi do normalizacji
            
        Returns:
            Dict: Ujednolicone dane
        """
        normalized = {}
        
        for key, value in data.items():
            if key in ['długość', 'length', 'dlugosc']:
                normalized[key] = self._normalize_length(value)
            elif key in ['powierzchnia', 'area', 'pole']:
                normalized[key] = self._normalize_area(value)
            elif key in ['masa', 'weight', 'waga']:
                normalized[key] = self._normalize_weight(value)
            elif key in ['czas', 'time', 'produkcja']:
                normalized[key] = self._normalize_time(value)
            elif key in ['numer', 'id', 'product_id']:
                normalized[key] = self._normalize_product_id(value)
            elif key in ['material', 'materiał']:
                normalized[key] = self._normalize_material(value)
            else:
                normalized[key] = value
                
        return normalized
    
    def _normalize_length(self, value: str) -> str:
        """Normalizuje długość do metrów."""
        # Usuń spacje i zamień przecinek na kropkę
        value = value.replace(' ', '').replace(',', '.')
        
        # Wykryj jednostkę
        if 'mm' in value:
            num = float(re.search(r'([\d.]+)', value).group(1))
            return f"{num / 1000:.2f} m"
        elif 'cm' in value:
            num = float(re.search(r'([\d.]+)', value).group(1))
            return f"{num / 100:.2f} m"
        elif 'm' in value:
            num = float(re.search(r'([\d.]+)', value).group(1))
            return f"{num:.2f} m"
        else:
            # Zakładamy, że to metry
            num = float(re.search(r'([\d.]+)', value).group(1))
            return f"{num:.2f} m"
    
    def _normalize_area(self, value: str) -> str:
        """Normalizuje powierzchnię do m²."""
        value = value.replace(' ', '').replace(',', '.')
        
        if 'mm²' in value or 'mm2' in value:
            num = float(re.search(r'([\d.]+)', value).group(1))
            return f"{num / 1e6:.4f} m²"
        elif 'cm²' in value or 'cm2' in value:
            num = float(re.search(r'([\d.]+)', value).group(1))
            return f"{num / 1e4:.4f} m²"
        elif 'm²' in value or 'm2' in value:
            num = float(re.search(r'([\d.]+)', value).group(1))
            return f"{num:.4f} m²"
        else:
            num = float(re.search(r'([\d.]+)', value).group(1))
            return f"{num:.4f} m²"
    
    def _normalize_weight(self, value: str) -> str:
        """Normalizuje masę do kilogramów."""
        value = value.replace(' ', '').replace(',', '.')
        
        if 'g' in value and 'kg' not in value:
            num = float(re.search(r'([\d.]+)', value).group(1))
            return f"{num / 1000:.3f} kg"
        elif 'kg' in value:
            num = float(re.search(r'([\d.]+)', value).group(1))
            return f"{num:.3f} kg"
        else:
            num = float(re.search(r'([\d.]+)', value).group(1))
            return f"{num:.3f} kg"
    
    def _normalize_time(self, value: str) -> str:
        """Normalizuje czas do minut."""
        value = value.replace(' ', '').replace(',', '.')
        
        if 'h' in value or 'godz' in value:
            num = float(re.search(r'([\d.]+)', value).group(1))
            return f"{num * 60:.1f} min"
        elif 'min' in value or 'm' in value:
            num = float(re.search(r'([\d.]+)', value).group(1))
            return f"{num:.1f} min"
        else:
            num = float(re.search(r'([\d.]+)', value).group(1))
            return f"{num:.1f} min"
    
    def _normalize_product_id(self, value: str) -> str:
        """Normalizuje numer produktu."""
        # Usuń spacje i zbędne znaki
        value = value.strip().upper()
        
        # Jeśli nie ma myślnika, dodaj
        if '-' not in value and len(value) > 3:
            parts = re.match(r'([A-Z]+)(\d+)', value)
            if parts:
                prefix, number = parts.groups()
                return f"{prefix}-{number.zfill(6)}"
        
        return value
    
    def _normalize_material(self, value: str) -> str:
        """Normalizuje nazwę materiału."""
        # Tylko standaryzacja zapisu
        return value.strip().upper()
    
    def normalize_with_llm(self, text: str) -> Dict[str, Any]:
        """
        Normalizuje złożone dane za pomocą LLM.
        Używane tylko w trudnych przypadkach.
        """
        if not self.use_llm_for_ambiguous:
            raise ValueError("LLM normalization disabled")
            
        prompt = """
Jesteś procesorem normalizacji danych technicznych.

Nie interpretuj danych.
Nie zgaduj.
Nie dopisuj informacji.

Twoim zadaniem jest wyłącznie ujednolicenie danych.

Zastosuj następujące zasady:
- długości zapisuj wyłącznie w metrach (m)
- powierzchnie w m²
- objętości w m³
- masa w kg
- czas wyłącznie w minutach
- numer produktu pozostaw dokładnie taki jaki otrzymałeś
- materiał zapisuj oryginalną nazwą
- nie zmieniaj nazw własnych
- nie usuwaj żadnych informacji

Wynik zwróć jako JSON.
"""
        # Implementacja wywołania LLM
        # ...
```

### 1.2 Procesor Excel

**Cel**: Odczyt i walidacja danych z plików Excel/ERP.

```python
# src/processors/excel_processor.py

import pandas as pd
from typing import Dict, List, Any, Optional
from pathlib import Path

class ExcelProcessor:
    """Procesor danych z plików Excel."""
    
    REQUIRED_COLUMNS = [
        'numer_produktu',
        'material',
        'dlugosc',
        'szerokosc',
        'wysokosc',
        'masa',
        'czas_produkcji'
    ]
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.normalizer = DataNormalizer()
        
    def process(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Przetwarza plik Excel.
        
        Returns:
            List[Dict]: Lista produktów z danymi
        """
        # Odczyt pliku
        df = pd.read_excel(file_path)
        
        # Walidacja
        self._validate(df)
        
        # Przetwarzanie każdego wiersza
        products = []
        for _, row in df.iterrows():
            product = self._process_row(row)
            products.append(product)
            
        return products
    
    def _validate(self, df: pd.DataFrame) -> None:
        """Waliduje strukturę danych."""
        missing = set(self.REQUIRED_COLUMNS) - set(df.columns)
        if missing:
            raise ValueError(f"Brak wymaganych kolumn: {missing}")
    
    def _process_row(self, row: pd.Series) -> Dict[str, Any]:
        """Przetwarza pojedynczy wiersz."""
        product = {
            'numer_produktu': str(row['numer_produktu']),
            'material': str(row['material']),
            'dlugosc': self.normalizer._normalize_length(str(row['dlugosc'])),
            'szerokosc': self.normalizer._normalize_length(str(row['szerokosc'])),
            'wysokosc': self.normalizer._normalize_length(str(row['wysokosc'])),
            'masa': self.normalizer._normalize_weight(str(row['masa'])),
            'czas_produkcji': self.normalizer._normalize_time(str(row['czas_produkcji']))
        }
        
        # Dodatkowe kolumny
        for col in row.index:
            if col not in self.REQUIRED_COLUMNS:
                product[col] = str(row[col]) if pd.notna(row[col]) else None
                
        return product
```

### 1.3 Procesor DXF

**Cel**: Ekstrakcja danych z plików DXF.

```python
# src/processors/dxf_processor.py

import ezdxf
from pathlib import Path
from typing import Dict, Any, List, Optional
import re

class DXFProcessor:
    """Procesor plików DXF."""
    
    def __init__(self):
        self.normalizer = DataNormalizer()
        
    def process(self, file_path: Path) -> Dict[str, Any]:
        """
        Przetwarza plik DXF.
        
        Returns:
            Dict: Wyodrębnione dane techniczne
        """
        doc = ezdxf.readfile(file_path)
        msp = doc.modelspace()
        
        # Podstawowe informacje
        result = {
            'numer_produktu': self._extract_product_id(file_path),
            'material': self._extract_material(doc),
            'dlugosc_ciecia': self._calculate_cut_length(msp),
            'liczba_otworow': self._count_holes(msp),
            'pole_blachy': self._calculate_sheet_area(msp),
            'czas_produkcji': None  # Szacowane przez LLM lub z Excela
        }
        
        # Normalizacja
        result = self.normalizer.normalize(result)
        
        return result
    
    def _extract_product_id(self, file_path: Path) -> str:
        """Wyodrębnia numer produktu z nazwy pliku."""
        filename = file_path.stem
        # Szukaj wzorca: AI-123, AI123, itp.
        match = re.search(r'([A-Z]+[-]?\d+)', filename)
        if match:
            return match.group(1)
        return filename
    
    def _extract_material(self, doc: ezdxf.document.Drawing) -> str:
        """Wyodrębnia materiał z DXF (np. z warstw)."""
        # Szukaj w nazwach warstw
        materials = set()
        for layer in doc.layers:
            name = layer.dxf.name.lower()
            if 's235' in name or 's355' in name:
                materials.add(name.upper())
                
        if materials:
            return next(iter(materials))
        return "Nieznany"
    
    def _calculate_cut_length(self, msp) -> float:
        """Oblicza całkowitą długość cięcia."""
        total_length = 0.0
        
        for entity in msp:
            if entity.dxftype() == 'LINE':
                total_length += entity.dxf.length
            elif entity.dxftype() == 'LWPOLYLINE':
                total_length += entity.length
            elif entity.dxftype() == 'CIRCLE':
                total_length += 2 * 3.14159 * entity.dxf.radius
                
        return total_length
    
    def _count_holes(self, msp) -> int:
        """Liczy otwory w rysunku."""
        count = 0
        
        for entity in msp:
            if entity.dxftype() == 'CIRCLE':
                # Małe koła to otwory
                if entity.dxf.radius < 50:  # Próg dla otworów
                    count += 1
            elif entity.dxftype() == 'INSERT':
                # Bloki mogą zawierać otwory
                pass
                
        return count
    
    def _calculate_sheet_area(self, msp) -> float:
        """Oblicza pole blachy."""
        # Uproszczone: pole prostokąta obejmującego rysunek
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        
        for entity in msp:
            try:
                points = entity.vertices() if hasattr(entity, 'vertices') else []
                for point in points:
                    if hasattr(point, 'x'):
                        min_x = min(min_x, point.x)
                        max_x = max(max_x, point.x)
                        min_y = min(min_y, point.y)
                        max_y = max(max_y, point.y)
            except:
                continue
                
        if min_x != float('inf'):
            width = max_x - min_x
            height = max_y - min_y
            return width * height
            
        return 0.0
```

### 1.4 Procesor PDF

**Cel**: Ekstrakcja danych z dokumentów PDF.

```python
# src/processors/pdf_processor.py

import pypdf
from pathlib import Path
from typing import Dict, Any, List, Optional
import re

class PDFProcessor:
    """Procesor plików PDF."""
    
    def __init__(self):
        self.normalizer = DataNormalizer()
        
    def process(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Przetwarza plik PDF.
        
        Returns:
            List[Dict]: Wyodrębnione sekcje z danymi
        """
        reader = pypdf.PdfReader(file_path)
        text = ""
        
        for page in reader.pages:
            text += page.extract_text()
            
        # Podział na sekcje
        sections = self._split_into_sections(text)
        
        # Przetwarzanie każdej sekcji
        results = []
        for section in sections:
            data = self._extract_data_from_section(section)
            if data:
                results.append(data)
                
        return results
    
    def _split_into_sections(self, text: str) -> List[str]:
        """Dzieli tekst na sekcje."""
        # Szukaj nagłówków sekcji
        headers = re.finditer(r'(?m)^(?:[A-Z][A-Z\s]+:|\d+\.\s+[A-Z])', text)
        
        sections = []
        last_pos = 0
        
        for match in headers:
            if last_pos > 0:
                sections.append(text[last_pos:match.start()].strip())
            last_pos = match.start()
            
        if last_pos < len(text):
            sections.append(text[last_pos:].strip())
            
        return sections or [text]
    
    def _extract_data_from_section(self, section: str) -> Dict[str, Any]:
        """Wyodrębnia dane z sekcji."""
        data = {}
        
        # Szukaj par klucz: wartość
        pairs = re.findall(r'([A-Za-ząćęłńóśźżĄĆĘŁŃÓŚŹŻ\s]+):\s*([^\n]+)', section)
        
        for key, value in pairs:
            key_clean = key.strip().lower()
            
            if 'numer' in key_clean or 'id' in key_clean:
                data['numer_produktu'] = value.strip()
            elif 'materiał' in key_clean or 'material' in key_clean:
                data['material'] = value.strip()
            elif 'długość' in key_clean or 'dlugosc' in key_clean:
                data['dlugosc'] = value.strip()
            elif 'powierzchnia' in key_clean:
                data['powierzchnia'] = value.strip()
            elif 'masa' in key_clean or 'waga' in key_clean:
                data['masa'] = value.strip()
            elif 'czas' in key_clean:
                data['czas_produkcji'] = value.strip()
                
        return data
```

---

## Faza 2: Warstwa pośrednia - Katalog JSON

### 2.1 Struktura JSON

**Cel**: Ujednolicone repozytorium danych produktów.

**Format**:

```json
{
  "product_id": "AI-000123",
  "source_files": {
    "excel": "produkty_2024.xlsx",
    "dxf": "AI-123.dxf",
    "pdf": "specyfikacja_AI-123.pdf"
  },
  "data": {
    "material": "S235JR",
    "dimensions": {
      "dlugosc": "2.50 m",
      "szerokosc": "1.20 m",
      "wysokosc": "0.80 m"
    },
    "mass": "3.2 kg",
    "production_time": "18.0 min",
    "cutting": {
      "dlugosc_ciecia": "12.0 m",
      "liczba_otworow": 4,
      "pole_blachy": "0.52 m²"
    },
    "additional": {
      "numer_rysunku": "R-123-01",
      "wersja": "A",
      "data_aktualizacji": "2024-01-15"
    }
  },
  "normalized_description": "Produkt AI-000123 wykonany z materiału S235JR. Wymiary: 2.50 m x 1.20 m x 0.80 m. Masa: 3.2 kg. Czas produkcji: 18.0 minut. Wymaga cięcia laserem o długości 12.0 m. Zawiera 4 otwory o średnicy 10 mm. Pole blachy: 0.52 m².",
  "metadata": {
    "processed_at": "2024-01-20T10:30:00",
    "processors_version": "1.0.0",
    "validation_status": "valid"
  }
}
```

### 2.2 Manager katalogu JSON

```python
# src/pipeline/staging_manager.py

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import hashlib

class StagingManager:
    """Manager warstwy pośredniej JSON."""
    
    def __init__(self, staging_dir: Path):
        self.staging_dir = Path(staging_dir)
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        
    def get_product_path(self, product_id: str) -> Path:
        """Zwraca ścieżkę do pliku JSON produktu."""
        return self.staging_dir / f"{product_id}.json"
    
    def load_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Ładuje dane produktu z JSON."""
        path = self.get_product_path(product_id)
        if not path.exists():
            return None
            
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_product(self, product_id: str, data: Dict[str, Any]) -> None:
        """Zapisuje dane produktu do JSON."""
        path = self.get_product_path(product_id)
        
        # Dodaj metadane
        if 'metadata' not in data:
            data['metadata'] = {}
        data['metadata']['processed_at'] = datetime.now().isoformat()
        data['metadata']['checksum'] = self._calculate_checksum(data)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def merge_product_data(self, product_id: str, source: str, data: Dict[str, Any]) -> None:
        """Łączy dane z nowego źródła z istniejącymi."""
        current = self.load_product(product_id)
        
        if current is None:
            current = {
                'product_id': product_id,
                'source_files': {},
                'data': {},
                'normalized_description': None,
                'metadata': {}
            }
        
        # Aktualizacja źródła
        current['source_files'][source] = data.get('source_file', 'unknown')
        
        # Aktualizacja danych
        if 'data' not in current:
            current['data'] = {}
        current['data'].update(data.get('data', {}))
        
        # Zapisz
        self.save_product(product_id, current)
    
    def is_complete(self, product_id: str) -> bool:
        """Sprawdza, czy produkt ma wszystkie wymagane dane."""
        data = self.load_product(product_id)
        if not data:
            return False
            
        # Wymagane pola
        required = ['material', 'dimensions', 'mass', 'production_time']
        return all(field in data.get('data', {}) for field in required)
    
    def get_all_products(self) -> List[str]:
        """Zwraca listę wszystkich ID produktów."""
        return [p.stem for p in self.staging_dir.glob("*.json")]
    
    def _calculate_checksum(self, data: Dict[str, Any]) -> str:
        """Oblicza sumę kontrolną danych."""
        # Usuń metadane przed obliczeniem
        data_copy = {k: v for k, v in data.items() if k != 'metadata'}
        json_str = json.dumps(data_copy, sort_keys=True)
        return hashlib.md5(json_str.encode()).hexdigest()
```

### 2.3 Pipeline integracji danych

```python
# src/pipeline/data_pipeline.py

from pathlib import Path
from typing import Dict, Any, List
from ..processors.excel_processor import ExcelProcessor
from ..processors.dxf_processor import DXFProcessor
from ..processors.pdf_processor import PDFProcessor
from ..processors.normalizer import DataNormalizer
from .staging_manager import StagingManager

class DataPipeline:
    """Pipeline integracji danych z różnych źródeł."""
    
    def __init__(self, staging_dir: Path):
        self.staging = StagingManager(staging_dir)
        self.excel_processor = ExcelProcessor()
        self.dxf_processor = DXFProcessor()
        self.pdf_processor = PDFProcessor()
        self.normalizer = DataNormalizer()
        
    def process_excel(self, file_path: Path) -> None:
        """Przetwarza plik Excel."""
        products = self.excel_processor.process(file_path)
        
        for product in products:
            product_id = product.get('numer_produktu')
            if product_id:
                # Zapisz do staging
                self.staging.merge_product_data(
                    product_id, 
                    'excel', 
                    {'data': product, 'source_file': file_path.name}
                )
    
    def process_dxf(self, file_path: Path) -> None:
        """Przetwarza plik DXF."""
        data = self.dxf_processor.process(file_path)
        product_id = data.get('numer_produktu')
        
        if product_id:
            self.staging.merge_product_data(
                product_id,
                'dxf',
                {'data': data, 'source_file': file_path.name}
            )
    
    def process_pdf(self, file_path: Path) -> None:
        """Przetwarza plik PDF."""
        sections = self.pdf_processor.process(file_path)
        
        for section in sections:
            product_id = section.get('numer_produktu')
            if product_id:
                self.staging.merge_product_data(
                    product_id,
                    'pdf',
                    {'data': section, 'source_file': file_path.name}
                )
    
    def generate_description(self, product_id: str) -> str:
        """Generuje opis techniczny produktu."""
        data = self.staging.load_product(product_id)
        if not data:
            return ""
            
        product_data = data.get('data', {})
        dims = product_data.get('dimensions', {})
        
        description_parts = [
            f"Produkt {product_id}",
            f"wykonany z materiału {product_data.get('material', 'nieznany')}",
        ]
        
        if dims:
            desc = f"Wymiary: {dims.get('dlugosc', '')} x {dims.get('szerokosc', '')} x {dims.get('wysokosc', '')}"
            description_parts.append(desc)
        
        if 'mass' in product_data:
            description_parts.append(f"Masa: {product_data['mass']}")
        
        if 'production_time' in product_data:
            description_parts.append(f"Czas produkcji: {product_data['production_time']}")
        
        if 'cutting' in product_data:
            cutting = product_data['cutting']
            if 'dlugosc_ciecia' in cutting:
                description_parts.append(f"Wymaga cięcia o długości {cutting['dlugosc_ciecia']}")
            if 'liczba_otworow' in cutting:
                description_parts.append(f"Zawiera {cutting['liczba_otworow']} otworów")
            if 'pole_blachy' in cutting:
                description_parts.append(f"Pole blachy: {cutting['pole_blachy']}")
        
        description = ". ".join(description_parts) + "."
        
        # Zapisz opis
        data['normalized_description'] = description
        self.staging.save_product(product_id, data)
        
        return description
```

---

## Faza 3: Warstwa wyszukiwania - Embedding i ChromaDB

### 3.1 Embedding

**Cel**: Konwersja tekstu na wektory dla wyszukiwania semantycznego.

```python
# src/embedding/embedder.py

import ollama
from typing import List, Union
import numpy as np
from sentence_transformers import SentenceTransformer

class Embedder:
    """Klasa do generowania embeddingów."""
    
    def __init__(self, model_name: str = "bge-m3", use_ollama: bool = True):
        """
        Inicjalizacja embeddera.
        
        Args:
            model_name: Nazwa modelu ("bge-m3", "nomic-embed-text")
            use_ollama: Czy używać Ollama (True) czy sentence-transformers (False)
        """
        self.model_name = model_name
        self.use_ollama = use_ollama
        
        if not use_ollama:
            self.model = SentenceTransformer(f"BAAI/{model_name}")
    
    def embed(self, text: str) -> List[float]:
        """Generuje embedding dla pojedynczego tekstu."""
        if self.use_ollama:
            response = ollama.embeddings(model=self.model_name, prompt=text)
            return response['embedding']
        else:
            return self.model.encode(text).tolist()
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generuje embeddingi dla wielu tekstów."""
        if self.use_ollama:
            return [self.embed(text) for text in texts]
        else:
            return self.model.encode(texts).tolist()
    
    def embed_product(self, product_data: Dict[str, Any]) -> List[float]:
        """
        Generuje embedding dla całego produktu.
        
        Args:
            product_data: Dane produktu ze staging
        """
        # Użyj znormalizowanego opisu
        description = product_data.get('normalized_description')
        
        if not description:
            # Stwórz opis z danych
            data = product_data.get('data', {})
            description = self._build_description(product_data['product_id'], data)
        
        return self.embed(description)
    
    def _build_description(self, product_id: str, data: Dict[str, Any]) -> str:
        """Buduje opis z danych produktu."""
        parts = [f"Produkt {product_id}"]
        
        if 'material' in data:
            parts.append(f"materiał {data['material']}")
        
        dims = data.get('dimensions', {})
        if dims:
            dims_str = " x ".join([str(v) for v in dims.values()])
            parts.append(f"wymiary {dims_str}")
        
        if 'mass' in data:
            parts.append(f"masa {data['mass']}")
        
        if 'production_time' in data:
            parts.append(f"czas produkcji {data['production_time']}")
        
        return ". ".join(parts) + "."
```

### 3.2 Baza wektorowa ChromaDB

```python
# src/vector_db/chroma_client.py

import chromadb
from chromadb.utils import embedding_functions
from pathlib import Path
from typing import Dict, Any, List, Optional

class ChromaManager:
    """Manager bazy wektorowej ChromaDB."""
    
    def __init__(self, persist_dir: Path, collection_name: str = "products"):
        """
        Inicjalizacja bazy ChromaDB.
        
        Args:
            persist_dir: Katalog do przechowywania bazy
            collection_name: Nazwa kolekcji
        """
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir)
        )
        
        self.collection_name = collection_name
        self.collection = None
        
        # Funkcja embeddingowa dla Ollama
        self.embedding_function = embedding_functions.OllamaEmbeddingFunction(
            model_name="bge-m3",
            url="http://localhost:11434/api/embeddings"
        )
    
    def initialize(self) -> None:
        """Inicjalizuje kolekcję."""
        try:
            self.collection = self.client.get_collection(self.collection_name)
        except:
            self.collection = self.client.create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function
            )
    
    def add_product(self, product_id: str, description: str, metadata: Dict[str, Any] = None) -> None:
        """
        Dodaje produkt do bazy.
        
        Args:
            product_id: ID produktu
            description: Opis produktu
            metadata: Dodatkowe metadane
        """
        if self.collection is None:
            self.initialize()
            
        self.collection.add(
            documents=[description],
            metadatas=[metadata or {"product_id": product_id}],
            ids=[product_id]
        )
    
    def add_products_batch(self, products: List[Dict[str, Any]]) -> None:
        """
        Dodaje wiele produktów do bazy.
        
        Args:
            products: Lista produktów ze staging
        """
        if self.collection is None:
            self.initialize()
            
        documents = []
        metadatas = []
        ids = []
        
        for product in products:
            description = product.get('normalized_description')
            if not description:
                continue
                
            documents.append(description)
            metadatas.append({
                "product_id": product['product_id'],
                "source_files": list(product.get('source_files', {}).values())
            })
            ids.append(product['product_id'])
        
        if documents:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
    
    def search(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        Wyszukuje produkty podobne do zapytania.
        
        Args:
            query: Zapytanie tekstowe
            n_results: Liczba wyników
            
        Returns:
            List[Dict]: Lista znalezionych produktów
        """
        if self.collection is None:
            self.initialize()
            
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        # Formatowanie wyników
        formatted = []
        if results and results['ids']:
            for i, doc_id in enumerate(results['ids'][0]):
                formatted.append({
                    'id': doc_id,
                    'document': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else None
                })
        
        return formatted
    
    def delete_product(self, product_id: str) -> None:
        """Usuwa produkt z bazy."""
        if self.collection is None:
            self.initialize()
            
        self.collection.delete(ids=[product_id])
    
    def update_product(self, product_id: str, description: str, metadata: Dict[str, Any] = None) -> None:
        """Aktualizuje produkt w bazie."""
        if self.collection is None:
            self.initialize()
            
        self.collection.update(
            ids=[product_id],
            documents=[description],
            metadatas=[metadata or {"product_id": product_id}]
        )
    
    def count(self) -> int:
        """Zwraca liczbę produktów w bazie."""
        if self.collection is None:
            self.initialize()
            
        return self.collection.count()
```

### 3.3 Synchronizacja staging → ChromaDB

```python
# src/pipeline/indexing_pipeline.py

from pathlib import Path
from typing import List, Dict, Any
from ..embedding.embedder import Embedder
from ..vector_db.chroma_client import ChromaManager
from .staging_manager import StagingManager

class IndexingPipeline:
    """Pipeline indeksowania danych do bazy wektorowej."""
    
    def __init__(self, staging_dir: Path, chroma_dir: Path):
        self.staging = StagingManager(staging_dir)
        self.chroma = ChromaManager(chroma_dir)
        self.embedder = Embedder(model_name="bge-m3")
        
    def index_all(self) -> None:
        """Indeksuje wszystkie produkty ze staging."""
        products = self._load_all_products()
        self.chroma.add_products_batch(products)
        
    def index_product(self, product_id: str) -> None:
        """Indeksuje pojedynczy produkt."""
        product = self.staging.load_product(product_id)
        if not product:
            raise ValueError(f"Produkt {product_id} nie istnieje w staging")
            
        description = product.get('normalized_description')
        if not description:
            # Wygeneruj opis
            from .data_pipeline import DataPipeline
            pipeline = DataPipeline(self.staging.staging_dir)
            description = pipeline.generate_description(product_id)
            product['normalized_description'] = description
            
        self.chroma.add_product(
            product_id=product_id,
            description=description,
            metadata={"product_id": product_id}
        )
        
    def reindex_all(self) -> None:
        """Przebudowuje całą bazę."""
        # Usuń starą kolekcję
        self.chroma.client.delete_collection(self.chroma.collection_name)
        self.chroma.collection = None
        self.chroma.initialize()
        
        # Indeksuj od nowa
        self.index_all()
        
    def _load_all_products(self) -> List[Dict[str, Any]]:
        """Ładuje wszystkie produkty ze staging."""
        products = []
        for product_id in self.staging.get_all_products():
            product = self.staging.load_product(product_id)
            if product and self.staging.is_complete(product_id):
                # Upewnij się, że opis istnieje
                if not product.get('normalized_description'):
                    from .data_pipeline import DataPipeline
                    pipeline = DataPipeline(self.staging.staging_dir)
                    product['normalized_description'] = pipeline.generate_description(product_id)
                    self.staging.save_product(product_id, product)
                    
                products.append(product)
                
        return products
    
    def get_index_status(self) -> Dict[str, Any]:
        """Zwraca status indeksowania."""
        staging_count = len(self.staging.get_all_products())
        chroma_count = self.chroma.count()
        
        return {
            'staging_products': staging_count,
            'chroma_products': chroma_count,
            'complete_products': len([p for p in self.staging.get_all_products() 
                                     if self.staging.is_complete(p)]),
            'missing': staging_count - chroma_count
        }
```

---

## Faza 4: Warstwa odpowiedzi - LLM

### 4.1 Klient LLM

```python
# src/llm/llm_client.py

import ollama
from typing import List, Dict, Any, Optional
import json

class LLMClient:
    """Klient dla modeli LLM."""
    
    def __init__(self, model_name: str = "gemma3:4b", use_ollama: bool = True):
        """
        Inicjalizacja klienta LLM.
        
        Args:
            model_name: Nazwa modelu ("gemma3:4b", "qwen2.5:3b", "bielik:4b")
            use_ollama: Czy używać Ollama
        """
        self.model_name = model_name
        self.use_ollama = use_ollama
        
        # Sprawdź dostępność modelu
        if use_ollama:
            self._check_model_available()
    
    def _check_model_available(self) -> None:
        """Sprawdza, czy model jest dostępny w Ollama."""
        try:
            models = ollama.list()
            available = [m['name'] for m in models.get('models', [])]
            if self.model_name not in available:
                raise ValueError(f"Model {self.model_name} nie jest dostępny. " +
                               f"Dostępne modele: {available}")
        except Exception as e:
            raise RuntimeError(f"Nie można połączyć się z Ollama: {e}")
    
    def generate(self, prompt: str, context: str, system_prompt: Optional[str] = None) -> str:
        """
        Generuje odpowiedź na podstawie promptu i kontekstu.
        
        Args:
            prompt: Pytanie użytkownika
            context: Kontekst z bazy wektorowej
            system_prompt: Opcjonalny system prompt
            
        Returns:
            str: Odpowiedź modelu
        """
        full_prompt = self._build_prompt(prompt, context)
        
        if self.use_ollama:
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt or self._get_default_system_prompt()},
                    {"role": "user", "content": full_prompt}
                ],
                options={
                    "temperature": 0.3,  # Niska temperatura dla precyzyjnych odpowiedzi
                    "top_p": 0.9,
                    "num_predict": 1024
                }
            )
            return response['message']['content']
        
        # Alternatywna implementacja dla llama.cpp
        # ...
    
    def _build_prompt(self, query: str, context: str) -> str:
        """Buduje pełny prompt."""
        return f"""
Na podstawie poniższych informacji technicznych odpowiedz na pytanie.

KONTEKST:
{context}

PYTANIE:
{query}

ODPOWIEDŹ:
"""
    
    def _get_default_system_prompt(self) -> str:
        """Zwraca domyślny system prompt."""
        return """
Jesteś asystentem technicznym w firmie produkcyjnej. 
Twoim zadaniem jest udzielanie precyzyjnych odpowiedzi na pytania dotyczące produktów, 
procesów produkcyjnych i parametrów technicznych.

Zasady:
1. Odpowiadaj wyłącznie na podstawie dostarczonego kontekstu.
2. Jeśli kontekst nie zawiera informacji, przyznaj to wyraźnie.
3. Nie zgaduj ani nie uzupełniaj brakujących informacji.
4. Używaj precyzyjnego języka technicznego.
5. Podawaj wartości z jednostkami miary.
6. Jeśli pytanie dotyczy porównania, wyraźnie wskaż różnice.
"""
    
    def generate_with_rag(self, query: str, context_documents: List[Dict[str, Any]]) -> str:
        """
        Generuje odpowiedź z wykorzystaniem kontekstu z RAG.
        
        Args:
            query: Pytanie użytkownika
            context_documents: Dokumenty z ChromaDB
            
        Returns:
            str: Odpowiedź modelu
        """
        # Zbuduj kontekst z dokumentów
        context = self._build_context(context_documents)
        
        # Wygeneruj odpowiedź
        return self.generate(query, context)
    
    def _build_context(self, documents: List[Dict[str, Any]]) -> str:
        """Buduje kontekst z dokumentów."""
        context_parts = []
        
        for i, doc in enumerate(documents, 1):
            product_id = doc.get('metadata', {}).get('product_id', f"Produkt {i}")
            content = doc.get('document', '')
            context_parts.append(f"--- {product_id} ---\n{content}")
        
        return "\n\n".join(context_parts)
    
    def verify_model_performance(self, test_questions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Weryfikuje wydajność modelu.
        
        Args:
            test_questions: Lista pytań testowych z oczekiwanymi odpowiedziami
            
        Returns:
            Dict: Statystyki wydajności
        """
        results = {
            'total': len(test_questions),
            'correct': 0,
            'partial': 0,
            'incorrect': 0,
            'details': []
        }
        
        for test in test_questions:
            query = test['query']
            expected = test['expected']
            
            # Pobierz kontekst (symulacja)
            # W rzeczywistości użyj ChromaDB
            context = test.get('context', '')
            
            response = self.generate(query, context)
            
            # Ocena odpowiedzi (uproszczona)
            score = self._evaluate_response(response, expected)
            
            results['details'].append({
                'query': query,
                'response': response,
                'expected': expected,
                'score': score
            })
            
            if score >= 0.8:
                results['correct'] += 1
            elif score >= 0.5:
                results['partial'] += 1
            else:
                results['incorrect'] += 1
        
        return results
    
    def _evaluate_response(self, response: str, expected: str) -> float:
        """Ocena odpowiedzi (uproszczona)."""
        # W praktyce użyj bardziej zaawansowanej metryki
        # np. BLEU, ROUGE, lub LLM-as-judge
        response_words = set(response.lower().split())
        expected_words = set(expected.lower().split())
        
        intersection = response_words.intersection(expected_words)
        union = response_words.union(expected_words)
        
        if not union:
            return 0.0
            
        return len(intersection) / len(union)
```

### 4.2 Kompletny pipeline RAG

```python
# src/pipeline/rag_pipeline.py

from pathlib import Path
from typing import Dict, Any, List, Optional
from ..vector_db.chroma_client import ChromaManager
from ..llm.llm_client import LLMClient

class RAGPipeline:
    """Kompletny pipeline RAG."""
    
    def __init__(self, chroma_dir: Path, model_name: str = "gemma3:4b"):
        """
        Inicjalizacja pipeline RAG.
        
        Args:
            chroma_dir: Katalog bazy ChromaDB
            model_name: Nazwa modelu LLM
        """
        self.chroma = ChromaManager(chroma_dir)
        self.chroma.initialize()
        
        self.llm = LLMClient(model_name=model_name)
        
        # Domyślny system prompt
        self.system_prompt = """
Jesteś asystentem technicznym w firmie produkcyjnej FreeKasi.
Twoim zadaniem jest udzielanie precyzyjnych odpowiedzi na pytania dotyczące produktów.

Zasady:
1. Odpowiadaj wyłącznie na podstawie dostarczonego kontekstu.
2. Jeśli kontekst nie zawiera informacji, powiedz: "Nie mam informacji na ten temat."
3. Nie zgaduj ani nie uzupełniaj brakujących informacji.
4. Używaj precyzyjnego języka technicznego.
5. Podawaj wartości z jednostkami miary.
6. Jeśli podajesz dane liczbowe, używaj formatu z jednostkami (np. 2.5 m, 3.2 kg).
"""
    
    def ask(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        """
        Zadaje pytanie do systemu.
        
        Args:
            query: Pytanie użytkownika
            n_results: Liczba dokumentów do pobrania
            
        Returns:
            Dict: Odpowiedź z metadanymi
        """
        # 1. Wyszukaj odpowiednie produkty
        results = self.chroma.search(query, n_results=n_results)
        
        if not results:
            return {
                'query': query,
                'answer': "Nie znaleziono produktów pasujących do zapytania.",
                'context': [],
                'sources': []
            }
        
        # 2. Przygotuj kontekst
        context = self._build_context(results)
        sources = [r['metadata'].get('product_id', r['id']) for r in results]
        
        # 3. Wygeneruj odpowiedź
        answer = self.llm.generate(query, context, self.system_prompt)
        
        return {
            'query': query,
            'answer': answer,
            'context': results,
            'sources': sources,
            'model': self.llm.model_name
        }
    
    def ask_with_fallback(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        """
        Zadaje pytanie z mechanizmem fallback.
        Jeśli odpowiedź jest niepewna, rozszerza kontekst.
        """
        # Pierwsze zapytanie
        response = self.ask(query, n_results)
        
        # Sprawdź, czy odpowiedź jest użyteczna
        if "Nie mam informacji" in response['answer'] and n_results < 10:
            # Rozszerz kontekst
            response = self.ask(query, n_results + 3)
            
        return response
    
    def _build_context(self, results: List[Dict[str, Any]]) -> str:
        """Buduje kontekst z wyników wyszukiwania."""
        context_parts = []
        
        for i, result in enumerate(results, 1):
            product_id = result['metadata'].get('product_id', result['id'])
            content = result['document']
            distance = result.get('distance', 0)
            
            context_parts.append(
                f"--- Produkt {i}: {product_id} (dopasowanie: {1-distance:.2f}) ---\n"
                f"{content}"
            )
        
        return "\n\n".join(context_parts)
    
    def get_relevant_products(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Zwraca tylko listę odpowiednich produktów."""
        return self.chroma.search(query, n_results)
    
    def get_product_info(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Zwraca informacje o konkretnym produkcie."""
        results = self.chroma.search(f"Produkt {product_id}", n_results=1)
        
        for result in results:
            if result['id'] == product_id:
                return {
                    'id': product_id,
                    'description': result['document'],
                    'metadata': result['metadata']
                }
        return None
```

---

## Faza 5: Interfejs użytkownika

### 5.1 CLI - Podstawowy interfejs

```python
# src/cli.py

import argparse
import sys
from pathlib import Path
from pipeline.data_pipeline import DataPipeline
from pipeline.indexing_pipeline import IndexingPipeline
from pipeline.rag_pipeline import RAGPipeline
from utils.config import load_config

def main():
    parser = argparse.ArgumentParser(description="FreeKasi - System RAG dla produkcji")
    subparsers = parser.add_subparsers(dest='command', help='Polecenia')
    
    # Polecenie: process
    process_parser = subparsers.add_parser('process', help='Przetwarzanie plików')
    process_parser.add_argument('--excel', help='Ścieżka do pliku Excel')
    process_parser.add_argument('--dxf', help='Ścieżka do pliku DXF')
    process_parser.add_argument('--pdf', help='Ścieżka do pliku PDF')
    process_parser.add_argument('--dir', help='Katalog z plikami')
    
    # Polecenie: index
    index_parser = subparsers.add_parser('index', help='Indeksowanie danych')
    index_parser.add_argument('--all', action='store_true', help='Indeksuj wszystkie produkty')
    index_parser.add_argument('--product', help='ID produktu do indeksowania')
    index_parser.add_argument('--reindex', action='store_true', help='Przebuduj bazę')
    
    # Polecenie: ask
    ask_parser = subparsers.add_parser('ask', help='Zadaj pytanie')
    ask_parser.add_argument('query', help='Pytanie')
    ask_parser.add_argument('--n', type=int, default=5, help='Liczba wyników')
    
    # Polecenie: status
    status_parser = subparsers.add_parser('status', help='Status systemu')
    
    # Polecenie: serve
    serve_parser = subparsers.add_parser('serve', help='Uruchom API')
    serve_parser.add_argument('--port', type=int, default=8000, help='Port')
    
    args = parser.parse_args()
    
    # Wczytaj konfigurację
    config = load_config()
    
    if args.command == 'process':
        _handle_process(args, config)
    elif args.command == 'index':
        _handle_index(args, config)
    elif args.command == 'ask':
        _handle_ask(args, config)
    elif args.command == 'status':
        _handle_status(config)
    elif args.command == 'serve':
        _handle_serve(args, config)
    else:
        parser.print_help()

def _handle_process(args, config):
    """Obsługa polecenia process."""
    from pipeline.data_pipeline import DataPipeline
    
    pipeline = DataPipeline(config['staging_dir'])
    
    if args.excel:
        print(f"Przetwarzanie Excel: {args.excel}")
        pipeline.process_excel(Path(args.excel))
    
    if args.dxf:
        print(f"Przetwarzanie DXF: {args.dxf}")
        pipeline.process_dxf(Path(args.dxf))
    
    if args.pdf:
        print(f"Przetwarzanie PDF: {args.pdf}")
        pipeline.process_pdf(Path(args.pdf))
    
    if args.dir:
        dir_path = Path(args.dir)
        for file in dir_path.glob("*.xlsx"):
            pipeline.process_excel(file)
        for file in dir_path.glob("*.dxf"):
            pipeline.process_dxf(file)
        for file in dir_path.glob("*.pdf"):
            pipeline.process_pdf(file)
    
    print("Przetwarzanie zakończone.")

def _handle_index(args, config):
    """Obsługa polecenia index."""
    pipeline = IndexingPipeline(
        config['staging_dir'],
        config['chroma_dir']
    )
    
    if args.reindex:
        print("Przebudowa bazy...")
        pipeline.reindex_all()
    elif args.all:
        print("Indeksowanie wszystkich produktów...")
        pipeline.index_all()
    elif args.product:
        print(f"Indeksowanie produktu: {args.product}")
        pipeline.index_product(args.product)
    else:
        print("Podaj --all, --product lub --reindex")
        return
    
    status = pipeline.get_index_status()
    print(f"Indeksowanie zakończone. Status:")
    print(f"  Produkty w staging: {status['staging_products']}")
    print(f"  Produkty w ChromaDB: {status['chroma_products']}")

def _handle_ask(args, config):
    """Obsługa polecenia ask."""
    pipeline = RAGPipeline(
        config['chroma_dir'],
        config.get('llm_model', 'gemma3:4b')
    )
    
    print(f"Pytanie: {args.query}")
    print("Szukanie odpowiedzi...")
    
    response = pipeline.ask(args.query, args.n)
    
    print("\n" + "="*50)
    print("ODPOWIEDŹ:")
    print("="*50)
    print(response['answer'])
    print("\n" + "="*50)
    print("ŹRÓDŁA:")
    for i, source in enumerate(response['sources'], 1):
        print(f"  {i}. {source}")
    print("="*50)

def _handle_status(config):
    """Obsługa polecenia status."""
    from pipeline.indexing_pipeline import IndexingPipeline
    
    pipeline = IndexingPipeline(
        config['staging_dir'],
        config['chroma_dir']
    )
    
    status = pipeline.get_index_status()
    
    print("STATUS SYSTEMU:")
    print(f"  Produkty w staging: {status['staging_products']}")
    print(f"  Produkty w ChromaDB: {status['chroma_products']}")
    print(f"  Kompletne produkty: {status['complete_products']}")
    if status['missing'] > 0:
        print(f"  ⚠️ Do indeksowania: {status['missing']}")

def _handle_serve(args, config):
    """Obsługa polecenia serve."""
    from api import create_app
    app = create_app(config)
    app.run(host='0.0.0.0', port=args.port)

if __name__ == "__main__":
    main()
```

### 5.2 API REST (FastAPI)

```python
# src/api.py

from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from pathlib import Path
import tempfile
import shutil

from pipeline.data_pipeline import DataPipeline
from pipeline.indexing_pipeline import IndexingPipeline
from pipeline.rag_pipeline import RAGPipeline

# Modele danych
class QuestionRequest(BaseModel):
    query: str
    n_results: int = 5

class AnswerResponse(BaseModel):
    query: str
    answer: str
    sources: List[str]
    model: str

class StatusResponse(BaseModel):
    staging_products: int
    chroma_products: int
    complete_products: int
    missing: int

def create_app(config: Dict[str, Any]):
    app = FastAPI(
        title="FreeKasi API",
        description="System RAG dla produkcji",
        version="1.0.0"
    )
    
    # Inicjalizacja pipeline'ów
    data_pipeline = DataPipeline(config['staging_dir'])
    index_pipeline = IndexingPipeline(
        config['staging_dir'],
        config['chroma_dir']
    )
    rag_pipeline = RAGPipeline(
        config['chroma_dir'],
        config.get('llm_model', 'gemma3:4b')
    )
    
    @app.get("/")
    async def root():
        return {"status": "ok", "service": "FreeKasi RAG"}
    
    @app.get("/status", response_model=StatusResponse)
    async def get_status():
        """Zwraca status systemu."""
        status = index_pipeline.get_index_status()
        return StatusResponse(**status)
    
    @app.post("/ask", response_model=AnswerResponse)
    async def ask_question(request: QuestionRequest):
        """Zadaje pytanie do systemu."""
        response = rag_pipeline.ask(request.query, request.n_results)
        return AnswerResponse(
            query=response['query'],
            answer=response['answer'],
            sources=response['sources'],
            model=response['model']
        )
    
    @app.post("/process/excel")
    async def process_excel(file: UploadFile = File(...)):
        """Przetwarza plik Excel."""
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(400, "Dozwolone tylko pliki Excel")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = Path(tmp.name)
        
        try:
            data_pipeline.process_excel(tmp_path)
            return {"status": "ok", "message": "Plik przetworzony"}
        finally:
            tmp_path.unlink(missing_ok=True)
    
    @app.post("/process/dxf")
    async def process_dxf(file: UploadFile = File(...)):
        """Przetwarza plik DXF."""
        if not file.filename.endswith('.dxf'):
            raise HTTPException(400, "Dozwolone tylko pliki DXF")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.dxf') as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = Path(tmp.name)
        
        try:
            data_pipeline.process_dxf(tmp_path)
            return {"status": "ok", "message": "Plik przetworzony"}
        finally:
            tmp_path.unlink(missing_ok=True)
    
    @app.post("/index/all")
    async def index_all():
        """Indeksuje wszystkie produkty."""
        index_pipeline.index_all()
        return {"status": "ok", "message": "Indeksowanie zakończone"}
    
    @app.post("/index/reindex")
    async def reindex_all():
        """Przebudowuje bazę."""
        index_pipeline.reindex_all()
        return {"status": "ok", "message": "Baza przebudowana"}
    
    @app.get("/products")
    async def list_products():
        """Zwraca listę produktów."""
        from pipeline.staging_manager import StagingManager
        staging = StagingManager(config['staging_dir'])
        return {"products": staging.get_all_products()}
    
    @app.get("/products/{product_id}")
    async def get_product(product_id: str):
        """Zwraca dane produktu."""
        from pipeline.staging_manager import StagingManager
        staging = StagingManager(config['staging_dir'])
        product = staging.load_product(product_id)
        
        if not product:
            raise HTTPException(404, "Produkt nie znaleziony")
        
        return product
    
    return app
```

### 5.3 Prostyla aplikacja webowa (Streamlit)

```python
# app.py

import streamlit as st
import requests
import json
from pathlib import Path

st.set_page_config(
    page_title="FreeKasi - Asystent Produkcji",
    page_icon="🏭",
    layout="wide"
)

st.title("🏭 FreeKasi - Asystent Produkcji")
st.markdown("System RAG dla danych produkcyjnych")

# Sidebar
with st.sidebar:
    st.header("Konfiguracja")
    
    api_url = st.text_input("API URL", value="http://localhost:8000")
    
    st.header("Status systemu")
    if st.button("Sprawdź status"):
        try:
            response = requests.get(f"{api_url}/status")
            if response.status_code == 200:
                status = response.json()
                st.success("System działa")
                st.write(f"📦 Produkty w staging: {status['staging_products']}")
                st.write(f"🗄️ Produkty w bazie: {status['chroma_products']}")
                if status['missing'] > 0:
                    st.warning(f"⚠️ Do indeksowania: {status['missing']}")
            else:
                st.error("Nie można połączyć się z API")
        except:
            st.error("Błąd połączenia")
    
    st.header("Zarządzanie danymi")
    
    uploaded_file = st.file_uploader(
        "Załaduj plik",
        type=['xlsx', 'dxf', 'pdf']
    )
    
    if uploaded_file:
        if st.button("Przetwórz plik"):
            file_type = uploaded_file.name.split('.')[-1]
            endpoint = {
                'xlsx': '/process/excel',
                'dxf': '/process/dxf',
                'pdf': '/process/pdf'
            }.get(file_type)
            
            if endpoint:
                files = {'file': uploaded_file}
                response = requests.post(f"{api_url}{endpoint}", files=files)
                if response.status_code == 200:
                    st.success("Plik przetworzony")
                else:
                    st.error(f"Błąd: {response.text}")
    
    if st.button("🔄 Indeksuj wszystkie"):
        response = requests.post(f"{api_url}/index/all")
        if response.status_code == 200:
            st.success("Indeksowanie zakończone")
        else:
            st.error("Błąd indeksowania")
    
    if st.button("🔨 Przebuduj bazę"):
        response = requests.post(f"{api_url}/index/reindex")
        if response.status_code == 200:
            st.success("Baza przebudowana")
        else:
            st.error("Błąd")

# Główny panel - zadawanie pytań
st.header("💬 Zadaj pytanie")

query = st.text_input("Wpisz pytanie o produktach, procesach lub parametrach:")
n_results = st.slider("Liczba wyników", 1, 10, 5)

if query and st.button("Szukaj"):
    with st.spinner("Szukanie odpowiedzi..."):
        try:
            response = requests.post(
                f"{api_url}/ask",
                json={"query": query, "n_results": n_results}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Wyświetl odpowiedź
                st.subheader("📝 Odpowiedź")
                st.markdown(data['answer'])
                
                # Źródła
                st.subheader("📚 Źródła")
                for i, source in enumerate(data['sources'], 1):
                    st.write(f"{i}. {source}")
                
                # Szczegóły
                with st.expander("Szczegóły techniczne"):
                    st.write(f"Model: {data['model']}")
                    
            else:
                st.error(f"Błąd: {response.text}")
                
        except Exception as e:
            st.error(f"Błąd połączenia: {e}")

# Lista produktów
st.header("📋 Produkty")
if st.button("Pokaż produkty"):
    try:
        response = requests.get(f"{api_url}/products")
        if response.status_code == 200:
            products = response.json()['products']
            st.write(f"Znaleziono {len(products)} produktów")
            
            for product_id in products[:10]:
                with st.expander(f"📦 {product_id}"):
                    prod_response = requests.get(f"{api_url}/products/{product_id}")
                    if prod_response.status_code == 200:
                        st.json(prod_response.json())
        else:
            st.error("Błąd pobierania listy")
    except:
        st.error("Błąd połączenia")
```

---

## Faza 6: Testowanie i walidacja

### 6.1 Testy procesorów

```python
# tests/test_processors.py

import pytest
from pathlib import Path
from src.processors.excel_processor import ExcelProcessor
from src.processors.dxf_processor import DXFProcessor
from src.processors.normalizer import DataNormalizer

class TestExcelProcessor:
    """Testy procesora Excel."""
    
    def test_required_columns(self):
        """Sprawdza walidację wymaganych kolumn."""
        processor = ExcelProcessor()
        # Test z brakującymi kolumnami
        # ...
    
    def test_data_normalization(self):
        """Sprawdza normalizację danych z Excela."""
        # ...

class TestNormalizer:
    """Testy normalizatora."""
    
    def test_length_normalization(self):
        normalizer = DataNormalizer()
        
        test_cases = [
            ("2.5 m", "2.50 m"),
            ("2500 mm", "2.50 m"),
            ("250 cm", "2.50 m"),
            ("2,4 m", "2.40 m"),
        ]
        
        for input_val, expected in test_cases:
            result = normalizer._normalize_length(input_val)
            assert result == expected
    
    def test_weight_normalization(self):
        normalizer = DataNormalizer()
        
        test_cases = [
            ("3.2 kg", "3.200 kg"),
            ("3200 g", "3.200 kg"),
        ]
        
        for input_val, expected in test_cases:
            result = normalizer._normalize_weight(input_val)
            assert result == expected
    
    def test_product_id_normalization(self):
        normalizer = DataNormalizer()
        
        test_cases = [
            ("AI123", "AI-000123"),
            ("AI-123", "AI-000123"),
            ("A123", "A-000123"),
        ]
        
        for input_val, expected in test_cases:
            result = normalizer._normalize_product_id(input_val)
            assert result == expected

class TestDXFProcessor:
    """Testy procesora DXF."""
    
    def test_cut_length_calculation(self):
        """Sprawdza obliczanie długości cięcia."""
        # ...
    
    def test_hole_counting(self):
        """Sprawdza liczenie otworów."""
        # ...
```

### 6.2 Testy embedding i wyszukiwania

```python
# tests/test_retrieval.py

import pytest
from src.embedding.embedder import Embedder
from src.vector_db.chroma_client import ChromaManager
from src.pipeline.indexing_pipeline import IndexingPipeline

class TestRetrieval:
    """Testy wyszukiwania semantycznego."""
    
    @pytest.fixture
    def test_queries(self):
        """Zestaw pytań testowych."""
        return [
            {
                "query": "który produkt ma największą masę?",
                "expected_product": "AI-000456",
                "keywords": ["3.2 kg", "największą masę"]
            },
            {
                "query": "jakie materiały są używane?",
                "expected_product": None,
                "keywords": ["S235JR", "S355"]
            },
            {
                "query": "co to jest produkt AI-000123?",
                "expected_product": "AI-000123",
                "keywords": ["materiał S235JR", "2.5 m"]
            }
        ]
    
    def test_semantic_search(self, test_queries):
        """Test wyszukiwania semantycznego."""
        embedder = Embedder(model_name="bge-m3")
        chroma = ChromaManager(Path("data/chroma_test"))
        chroma.initialize()
        
        # Dodaj testowe produkty
        # ...
        
        for test in test_queries:
            results = chroma.search(test["query"], n_results=3)
            
            # Sprawdź, czy oczekiwany produkt jest w wynikach
            if test["expected_product"]:
                found = any(r['id'] == test["expected_product"] for r in results)
                assert found, f"Produkt {test['expected_product']} nie znaleziony"
            
            # Sprawdź, czy wyniki zawierają oczekiwane słowa kluczowe
            for keyword in test["keywords"]:
                found = any(keyword.lower() in r['document'].lower() for r in results)
                assert found, f"Słowo kluczowe '{keyword}' nie znalezione"
```

### 6.3 Testy RAG pipeline

```python
# tests/test_rag.py

import pytest
from src.pipeline.rag_pipeline import RAGPipeline
from src.pipeline.indexing_pipeline import IndexingPipeline

class TestRAG:
    """Testy pipeline RAG."""
    
    @pytest.fixture
    def rag_pipeline(self):
        """Przygotowanie pipeline RAG z testową bazą."""
        # Użyj testowej bazy
        chroma_dir = Path("data/chroma_test")
        pipeline = RAGPipeline(chroma_dir, model_name="qwen2.5:3b")
        return pipeline
    
    def test_question_about_material(self, rag_pipeline):
        """Test pytania o materiał."""
        response = rag_pipeline.ask("z jakiego materiału jest produkt AI-000123?")
        assert "S235JR" in response['answer'] or "S355" in response['answer']
    
    def test_question_about_dimensions(self, rag_pipeline):
        """Test pytania o wymiary."""
        response = rag_pipeline.ask("jakie są wymiary produktu AI-000456?")
        # Sprawdź, czy odpowiedź zawiera wymiary z jednostkami
        assert "m" in response['answer']
        assert "x" in response['answer'] or "×" in response['answer']
    
    def test_question_no_context(self, rag_pipeline):
        """Test pytania bez kontekstu."""
        response = rag_pipeline.ask("jaki jest kolor produktu AI-000123?")
        assert "Nie mam informacji" in response['answer']
```

### 6.4 Testy wydajnościowe

```python
# tests/test_performance.py

import time
import pytest
from src.embedding.embedder import Embedder
from src.llm.llm_client import LLMClient

class TestPerformance:
    """Testy wydajnościowe."""
    
    def test_embedding_speed(self):
        """Test szybkości embeddingu."""
        embedder = Embedder(model_name="bge-m3")
        texts = ["Produkt AI-123 wykonany z S235JR"] * 10
        
        start = time.time()
        for text in texts:
            embedder.embed(text)
        end = time.time()
        
        # Embedding powinien być szybki (< 0.5s na tekst)
        avg_time = (end - start) / len(texts)
        assert avg_time < 0.5, f"Embedding zbyt wolny: {avg_time:.2f}s"
    
    def test_llm_speed(self):
        """Test szybkości odpowiedzi LLM."""
        llm = LLMClient(model_name="qwen2.5:3b")
        prompt = "Opisz produkt wykonany z S235JR o wymiarach 2.5 m x 1.2 m x 0.8 m"
        context = "Testowy kontekst"
        
        start = time.time()
        response = llm.generate(prompt, context)
        end = time.time()
        
        # Odpowiedź powinna być szybka (< 3s)
        assert (end - start) < 3, f"LLM zbyt wolny: {(end-start):.2f}s"
    
    def test_memory_usage(self):
        """Test zużycia pamięci."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        
        # Załaduj modele
        embedder = Embedder(model_name="bge-m3")
        embedder.embed("test")
        
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_used = memory_after - memory_before
        
        # Zużycie pamięci powinno być < 2GB
        assert memory_used < 2048, f"Zużycie pamięci zbyt wysokie: {memory_used:.2f}MB"
```

---

## Faza 7: Wdrożenie i optymalizacja

### 7.1 Plik konfiguracyjny

```yaml
# config/config.yaml

# Ścieżki
data_dir: ./data
staging_dir: ./data/staging
chroma_dir: ./data/chroma
raw_dir: ./data/raw
logs_dir: ./logs

# Modele
llm:
  model: gemma3:4b
  # Alternatywy: qwen2.5:3b, bielik:4b
  temperature: 0.3
  max_tokens: 1024

embedding:
  model: bge-m3
  # Alternatywy: nomic-embed-text
  use_ollama: true

# Baza wektorowa
chroma:
  collection: products
  batch_size: 100

# Procesory
processors:
  excel:
    required_columns:
      - numer_produktu
      - material
      - dlugosc
      - szerokosc
      - wysokosc
      - masa
      - czas_produkcji
  
  dxf:
    hole_radius_threshold: 50
    material_layers:
      - S235
      - S355
  
  pdf:
    section_pattern: '(?m)^(?:[A-Z][A-Z\s]+:|\d+\.\s+[A-Z])'

# Testy
tests:
  query_file: ./tests/test_queries.json
  n_test_queries: 50
  top_k_threshold: 3

# API
api:
  host: 0.0.0.0
  port: 8000
  workers: 1

# Logowanie
logging:
  level: INFO
  format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  file: ./logs/freekasi.log
```

### 7.2 Skrypt uruchomieniowy

```bash
#!/bin/bash
# start.sh

echo "🚀 Uruchamianie FreeKasi..."

# Sprawdź Ollama
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama nie jest zainstalowane"
    exit 1
fi

# Sprawdź modele
echo "Sprawdzanie modeli..."
ollama list

# Uruchom API
echo "Uruchamianie API..."
python -m src.cli serve --port 8000 &

# Uruchom interfejs webowy (opcjonalnie)
echo "Uruchamianie interfejsu webowego..."
streamlit run app.py --server.port 8501 &

echo "✅ FreeKasi uruchomione!"
echo "📝 API: http://localhost:8000"
echo "🌐 Interfejs: http://localhost:8501"
```

### 7.3 Dockerfile

```dockerfile
# Dockerfile

FROM python:3.10-slim

WORKDIR /app

# Instalacja zależności systemowych
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Instalacja Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Kopiowanie zależności Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiowanie kodu
COPY . .

# Pobranie modeli
RUN ollama pull gemma3:4b
RUN ollama pull qwen2.5:3b
RUN ollama pull bge-m3

# Porty
EXPOSE 8000 8501

# Uruchomienie
CMD ["bash", "start.sh"]
```

---

## Podsumowanie techniczne

### Wybrane technologie

| Komponent | Wybór | Uzasadnienie |
|-----------|-------|--------------|
| **LLM** | Gemma 3 4B (budowa), Bielik 4B (docelowo) | Lekkie, szybkie na CPU, dobre po polsku |
| **Embedding** | BAAI bge-m3 / nomic-embed-text | Specjalistyczne, małe wymagania, dobre po polsku |
| **Baza wektorowa** | ChromaDB | Lekka, Python, lokalna, darmowa |
| **Framework LLM** | Ollama / llama.cpp | Obsługa CPU, GGUF |
| **Normalizacja** | Python + LLM (trudne przypadki) | 90% regułami, 10% LLM |
| **Warstwa pośrednia** | JSON staging | Debugowanie, walidacja, łatwe przebudowy |

### Kluczowe decyzje architektoniczne

1. **CPU-only design** – wszystkie komponenty zoptymalizowane pod procesor
2. **Warstwa pośrednia JSON** – łatwe debugowanie i walidacja
3. **Normalizacja regułami** – szybsza i tańsza niż LLM
4. **Oddzielne modele** – embedding i LLM to różne modele
5. **Testowanie każdego procesora** – jakość systemu zależy od każdego elementu

### Plan implementacji krok po kroku

| Etap | Czas | Opis |
|------|------|------|
| **1** | 1 dzień | Środowisko, struktura, config |
| **2** | 2 dni | Procesor Excel + Normalizator |
| **3** | 2 dni | Procesor DXF |
| **4** | 1 dzień | Procesor PDF |
| **5** | 1 dzień | Warstwa JSON staging |
| **6** | 1 dzień | Embedding + ChromaDB |
| **7** | 1 dzień | Pipeline RAG + LLM |
| **8** | 1 dzień | API + interfejs |
| **9** | 2 dni | Testy + walidacja |
| **10** | 1 dzień | Optymalizacja + wdrożenie |

### Najczęstsze problemy i rozwiązania

| Problem | Rozwiązanie |
|---------|-------------|
| Wolne embeddingi | Użyj batch processing, mniejszy model |
| Duże zużycie RAM | Mniejsze modele, limit batcha |
| Niska jakość odpowiedzi | Więcej kontekstu, lepsze chunking |
| Brak odpowiedzi | Fallback z szerszym kontekstem |
| Błędy normalizacji | Testy jednostkowe, reguły wyjątków |
| Wolne wyszukiwanie | Optymalizacja ChromaDB, mniejsza baza |

### Perspektywy rozwoju

1. **Bielik 4B** – gdy pojawi się stabilna wersja GGUF
2. **Milvus/Qdrant** – dla większych baz danych
3. **Reranking** – poprawa jakości wyszukiwania
4. **Hybrydowe wyszukiwanie** – semantyczne + keyword
5. **Multimodalność** – obrazy z DXF i PDF

---

*Plan został opracowany na podstawie analizy potrzeb i specyfikacji technicznej FreeKasi. System został zaprojektowany pod kątem wydajności na CPU i łatwości rozwoju.*
