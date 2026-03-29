"""
Skrypt inicjalizacji projektu
Tworzy niezbędne katalogi i przykładowe pliki
"""

import os
from pathlib import Path
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_directories():
    """Tworzy niezbędne katalogi"""
    directories = [
        "data",
        "data/dxf_drawings",
        "vector_db",
        "models"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logger.info(f"Utworzono katalog: {directory}")


def create_sample_excel():
    """Tworzy przykładowy plik Excel z danymi"""
    sample_data = {
        "nazwa": [
            "Belka główna A",
            "Belka główna B",
            "Płyta podłogowa 1",
            "Płyta podłogowa 2",
            "Kolumna K1",
            "Kolumna K2",
            "Śruba M10",
            "Śruba M12",
            "Kątownik 50x50",
            "Rura fi 100"
        ],
        "typ": [
            "belka",
            "belka",
            "płyta",
            "płyta",
            "kolumna",
            "kolumna",
            "łączenie",
            "łączenie",
            "profil",
            "rura"
        ],
        "długość": [5.2, 4.8, 0, 0, 3.0, 3.0, 0.1, 0.12, 2.5, 6.0],
        "powierzchnia": [0, 0, 12.5, 10.8, 0, 0, 0, 0, 0, 0],
        "ilość": [2, 2, 1, 1, 4, 4, 50, 30, 10, 8],
        "czas": [4.5, 4.2, 2.0, 1.8, 3.0, 3.0, 0.5, 0.6, 1.5, 2.0],
        "jednostka": [
            "metry bieżące",
            "metry bieżące",
            "metry kwadratowe",
            "metry kwadratowe",
            "metry bieżące",
            "metry bieżące",
            "sztuki",
            "sztuki",
            "metry bieżące",
            "metry bieżące"
        ],
        "opis": [
            "Belka główna konstrukcji nośnej, przekrój IPE 300",
            "Belka główna konstrukcji nośnej, przekrój IPE 300",
            "Płyta podłogowa z betonu zbrojonego",
            "Płyta podłogowa z betonu zbrojonego",
            "Kolumna nośna, przekrój HEA 200",
            "Kolumna nośna, przekrój HEA 200",
            "Śruba z łbem sześciocznym, klasa 8.8",
            "Śruba z łbem sześciocznym, klasa 8.8",
            "Kątownik równoramienny stalowy",
            "Rura stalowa bez szwu"
        ]
    }
    
    df = pd.DataFrame(sample_data)
    
    excel_path = Path("data/properties.xlsx")
    df.to_excel(excel_path, index=False, engine='openpyxl')
    
    logger.info(f"Utworzono przykładowy plik Excel: {excel_path}")
    logger.info(f"Zawiera {len(df)} rekordów")


def create_sample_dxf_info():
    """Tworzy plik informacyjny o przykładowych plikach DXF"""
    info_content = """# Przykładowe pliki DXF

Umieść pliki DXF w katalogu `data/dxf_drawings/`

## Wspierane obiekty DXF

### Długości (metry bieżące)
- LINE - linie
- LWPOLYLINE - polilinie lekkie
- POLYLINE - polilinie
- ARC - łuki
- CIRCLE - okręgi (obwody)
- ELLIPSE - elipsy (obwody)
- SPLINE - krzywe spline

### Powierzchnie (metry kwadratowe)
- LWPOLYLINE (zamknięte) - polilinie zamknięte
- CIRCLE - okręgi
- ELLIPSE - elipsy

### Ilości (sztuki)
- INSERT - bloki
- TEXT - teksty jednoliniowe
- MTEXT - teksty wieloliniowe
- DIMENSION - wymiary

## Przykładowe pliki

Możesz pobrać przykładowe pliki DXF z:
- https://www.example.com/sample-dxf (przykład)
- Utworzyć własne w programie CAD (AutoCAD, FreeCAD, LibreCAD)

## Format plików

Pliki powinny być w formacie DXF (Drawing Exchange Format):
- Wersja DXF: R2010 lub nowsza
- Kodowanie: UTF-8
- Jednostki: metry (zalecane)
"""
    
    info_path = Path("data/dxf_drawings/README.md")
    info_path.write_text(info_content, encoding='utf-8')
    
    logger.info(f"Utworzono plik informacyjny: {info_path}")


def create_env_file():
    """Tworzy plik .env z konfiguracją"""
    env_content = """# Konfiguracja aplikacji Chat z Bazą Wiedzy DXF

# Ścieżki
DATA_DIR=data
VECTOR_DB_DIR=vector_db
MODELS_DIR=models

# Model LLM
BIELIK_MODEL_NAME=speakleash/Bielik-7B-Instruct-v0.1

# Parametry generacji
LLM_TEMPERATURE=0.1
LLM_MAX_NEW_TOKENS=1024
LLM_TOP_P=0.9
LLM_REPETITION_PENALTY=1.1

# Baza wektorowa
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
VECTOR_DB_NAME=properties_db
COLLECTION_NAME=dxf_properties

# Interfejs
APP_PORT=7860
APP_HOST=0.0.0.0
"""
    
    env_path = Path(".env")
    env_path.write_text(env_content, encoding='utf-8')
    
    logger.info(f"Utworzono plik konfiguracyjny: {env_path}")


def create_gitignore():
    """Tworzy plik .gitignore"""
    gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
ENV/
env/
*.egg-info/
dist/
build/

# Modele LLM
models/
*.bin
*.safetensors
*.pt
*.pth

# Baza wektorowa
vector_db/
chroma_db/

# Dane
data/
*.xlsx
*.xls
*.dxf

# IDE
.vscode/
.idea/
*.swp
*.swo

# System
.DS_Store
Thumbs.db

# Logi
*.log
logs/

# Środowisko
.env
.env.local
"""
    
    gitignore_path = Path(".gitignore")
    gitignore_path.write_text(gitignore_content, encoding='utf-8')
    
    logger.info(f"Utworzono plik .gitignore: {gitignore_path}")


def main():
    """Główna funkcja inicjalizacji"""
    print("=" * 60)
    print("Inicjalizacja projektu Chat z Bazą Wiedzy DXF")
    print("=" * 60)
    
    try:
        # Tworzenie katalogów
        print("\n1. Tworzenie katalogów...")
        create_directories()
        
        # Tworzenie przykładowego pliku Excel
        print("\n2. Tworzenie przykładowego pliku Excel...")
        create_sample_excel()
        
        # Tworzenie pliku informacyjnego DXF
        print("\n3. Tworzenie pliku informacyjnego DXF...")
        create_sample_dxf_info()
        
        # Tworzenie pliku .env
        print("\n4. Tworzenie pliku konfiguracyjnego...")
        create_env_file()
        
        # Tworzenie pliku .gitignore
        print("\n5. Tworzenie pliku .gitignore...")
        create_gitignore()
        
        print("\n" + "=" * 60)
        print("Inicjalizacja zakończona pomyślnie!")
        print("=" * 60)
        
        print("\nNastępne kroki:")
        print("1. Zainstaluj zależności: pip install -r requirements.txt")
        print("2. Umieść pliki DXF w katalogu data/dxf_drawings/")
        print("3. Uruchom aplikację: python chat_app.py")
        print("4. Otwórz przeglądarkę: http://localhost:7860")
        
    except Exception as e:
        logger.error(f"Błąd inicjalizacji: {str(e)}")
        raise


if __name__ == "__main__":
    main()
