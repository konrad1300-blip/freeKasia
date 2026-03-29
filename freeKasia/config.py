"""
Konfiguracja aplikacji chat z bazą wektorową i LLM Bielik
"""

import os
from pathlib import Path

# Ścieżki bazowe
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
VECTOR_DB_DIR = BASE_DIR / "vector_db"
MODELS_DIR = BASE_DIR / "models"

# Tworzenie katalogów jeśli nie istnieją
DATA_DIR.mkdir(exist_ok=True)
VECTOR_DB_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)

# Konfiguracja plików danych
EXCEL_FILE = DATA_DIR / "properties.xlsx"
DXF_DIR = DATA_DIR / "dxf_drawings"

# Konfiguracja bazy wektorowej
VECTOR_DB_NAME = "properties_db"
COLLECTION_NAME = "dxf_properties"
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Konfiguracja LLM Bielik
BIELIK_MODEL_NAME = "speakleash/Bielik-7B-Instruct-v0.1"
BIELIK_MODEL_PATH = MODELS_DIR / "bielik-7b-instruct"

# Parametry generacji LLM
LLM_TEMPERATURE = 0.1  # Niska temperatura = mniej halucynacji
LLM_MAX_NEW_TOKENS = 1024
LLM_TOP_P = 0.9
LLM_REPETITION_PENALTY = 1.1

# Konfiguracja przetwarzania DXF
DXF_PROPERTIES = {
    "lengths": "Długości elementów (metry bieżące)",
    "areas": "Powierzchnie elementów (metry kwadratowe)",
    "quantities": "Ilości elementów (sztuki)",
    "times": "Czasy wykonania (godziny)"
}

# Konfiguracja interfejsu
APP_TITLE = "Chat z Bazą Wiedzy DXF"
APP_DESCRIPTION = """
Aplikacja chat do analizy rysunków DXF i właściwości elementów.
Zadaj pytanie dotyczące właściwości, długości, powierzchni, ilości lub czasów wykonania.
"""

# Instrukcje systemowe dla LLM
SYSTEM_PROMPT = """Jesteś asystentem AI specjalizującym się w analizie rysunków technicznych DXF i właściwości elementów.

Twoje zadania:
1. Odpowiadać na pytania dotyczące właściwości elementów z rysunków DXF
2. Podawać informacje o długościach, powierzchniach, ilościach i czasach wykonania
3. Analizować dane z bazy wektorowej i udzielać precyzyjnych odpowiedzi

Zasady:
- Odpowiadaj TYLKO na podstawie danych z bazy wektorowej
- Jeśli nie masz wystarczających danych, powiedz "Nie wiem" lub "Nie mam wystarczających informacji"
- Nie zgaduj ani nie wymyślaj informacji
- Podawaj konkretne wartości liczbowe gdy są dostępne
- Używaj jednostek miary (metry, metry kwadratowe, sztuki, godziny)
- Odpowiadaj w języku polskim
- Bądź zwięzły i precyzyjny

Przykłady odpowiedzi:
- "Długość elementu A wynosi 5.2 metra bieżącego."
- "Powierzchnia płyty B to 12.5 metra kwadratowego."
- "Ilość elementów typu C: 15 sztuk."
- "Szacowany czas wykonania: 8 godzin."
- "Nie mam informacji o tym elemencie w bazie danych."
"""
