# Chat z Bazą Wiedzy DXF

Aplikacja chat do analizy rysunków DXF i właściwości elementów z wykorzystaniem LLM Bielik i bazy wektorowej ChromaDB.

## Opis

Aplikacja umożliwia zadawanie pytań w języku naturalnym dotyczących właściwości elementów z rysunków DXF i danych z plików Excel. System przetwarza dane na embeddingi, tworzy bazę wektorową i wykorzystuje model LLM Bielik do generowania odpowiedzi.

### Główne funkcje:

- **Przetwarzanie plików DXF**: Ekstrakcja długości, powierzchni, ilości i czasów wykonania
- **Przetwarzanie plików Excel**: Odczyt właściwości elementów z arkuszy kalkulacyjnych
- **Baza wektorowa ChromaDB**: Przechowywanie i wyszukiwanie semantyczne
- **LLM Bielik**: Generowanie odpowiedzi na pytania użytkownika
- **Interfejs chat**: Przyjazny interfejs użytkownika Gradio
- **Praca lokalna**: Całkowicie offline, bez połączenia z internetem

## Wymagania systemowe

- Python 3.10+
- CUDA (opcjonalnie, dla przyspieszenia GPU)
- Minimum 16GB RAM (zalecane 32GB dla modelu Bielik)
- 10GB wolnego miejsca na dysku (dla modelu i danych)

## Instalacja

### 1. Sklonuj repozytorium

```bash
git clone <repo-url>
cd freeKasia
```

### 2. Utwórz środowisko wirtualne

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# lub
venv\Scripts\activate  # Windows
```

### 3. Zainstaluj zależności

```bash
pip install -r requirements.txt
```

### 4. Przygotuj dane

#### Pliki DXF
Umieść pliki DXF w katalogu `data/dxf_drawings/`:

```bash
mkdir -p data/dxf_drawings
# Skopiuj pliki DXF do tego katalogu
```

#### Plik Excel
Umieść plik Excel z właściwościami elementów w `data/properties.xlsx`:

Plik Excel powinien zawierać kolumny takie jak:
- `nazwa` / `name` - nazwa elementu
- `długość` / `length` - długość w metrach bieżących
- `powierzchnia` / `area` - powierzchnia w metrach kwadratowych
- `ilość` / `quantity` - ilość w sztukach
- `czas` / `time` - czas wykonania w godzinach
- `opis` / `description` - opis elementu

## Uruchomienie

### 1. Uruchom aplikację

```bash
python chat_app.py
```

### 2. Otwórz interfejs

Otwórz przeglądarkę i przejdź do: `http://localhost:7860`

### 3. Inicjalizacja

W interfejsie aplikacji:

1. Kliknij **"Inicjalizuj aplikację"** - uruchomi to bazę wektorową
2. Kliknij **"Załaduj model LLM"** - załaduje model Bielik (może potrwać kilka minut)
3. Kliknij **"Przetwórz pliki DXF"** - przetworzy wszystkie pliki DXF z katalogu
4. Kliknij **"Przetwórz plik Excel"** - przetworzy plik Excel

### 4. Zadawaj pytania

Po inicjalizacji możesz zadawać pytania w języku naturalnym, np.:

- "Jaka jest całkowita długość elementów?"
- "Ile metrów kwadratowych powierzchni jest w rysunku?"
- "Jaki jest szacowany czas wykonania?"
- "Ile sztuk elementów typu A?"
- "Jakie są właściwości elementu B?"

## Struktura projektu

```
freeKasia/
├── chat_app.py           # Główna aplikacja chat
├── config.py             # Konfiguracja aplikacji
├── dxf_processor.py      # Przetwarzanie plików DXF
├── excel_processor.py    # Przetwarzanie plików Excel
├── vector_db.py          # Baza wektorowa ChromaDB
├── llm_integration.py    # Integracja z LLM Bielik
├── requirements.txt      # Zależności Python
├── README.md             # Dokumentacja
├── data/                 # Katalog z danymi
│   ├── dxf_drawings/     # Pliki DXF
│   └── properties.xlsx   # Plik Excel z właściwościami
├── vector_db/            # Baza wektorowa ChromaDB
└── models/               # Modele LLM
```

## Konfiguracja

Główne parametry konfiguracyjne znajdują się w pliku `config.py`:

### Parametry LLM

```python
LLM_TEMPERATURE = 0.1      # Niska temperatura = mniej halucynacji
LLM_MAX_NEW_TOKENS = 1024  # Maksymalna długość odpowiedzi
LLM_TOP_P = 0.9            # Parametr top_p
LLM_REPETITION_PENALTY = 1.1  # Kara za powtórzenia
```

### Parametry bazy wektorowej

```python
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
VECTOR_DB_NAME = "properties_db"
COLLECTION_NAME = "dxf_properties"
```

### Parametry modelu Bielik

```python
BIELIK_MODEL_NAME = "speakleash/Bielik-7B-Instruct-v0.1"
```

## Przetwarzanie DXF

Moduł `dxf_processor.py` ekstrahuje następujące właściwości z plików DXF:

### Długości (metry bieżące)
- Linie
- Polilinie
- Łuki
- Okręgi (obwody)
- Elipsy (obwody)
- Spline'y

### Powierzchnie (metry kwadratowe)
- Zamknięte polilinie
- Okręgi
- Elipsy

### Ilości (sztuki)
- Bloki
- Teksty
- Wymiary

### Czasy wykonania (godziny)
- Szacowane na podstawie długości, powierzchni i ilości

## Przetwarzanie Excel

Moduł `excel_processor.py` odczytuje dane z plików Excel i konwertuje je na format odpowiedni do embeddingu.

### Wspierane kolumny

| Kolumna | Opis | Jednostka |
|---------|------|-----------|
| nazwa/name | Nazwa elementu | - |
| długość/length | Długość | metry bieżące |
| powierzchnia/area | Powierzchnia | metry kwadratowe |
| ilość/quantity | Ilość | sztuki |
| czas/time | Czas wykonania | godziny |
| opis/description | Opis elementu | - |

## Baza wektorowa

Aplikacja wykorzystuje ChromaDB do przechowywania embeddingów i wyszukiwania semantycznego.

### Funkcje

- **Dodawanie dokumentów**: Automatyczne generowanie embeddingów
- **Wyszukiwanie semantyczne**: Znajdowanie najbardziej podobnych dokumentów
- **Aktualizacja**: Możliwość aktualizacji dokumentów
- **Statystyki**: Informacje o kolekcji

## LLM Bielik

Model Bielik-7B-Instruct jest polskim modelem językowym zoptymalizowanym do zadań instrukcyjnych.

### Konfiguracja

- **Temperatura**: 0.1 (niska = mniej halucynacji)
- **Kwantyzacja**: 4-bitowa (oszczędność pamięci)
- **Maksymalne tokeny**: 1024

### Zasady odpowiedzi

Model jest skonfigurowany do:
- Odpowiadania TYLKO na podstawie danych z bazy
- Mówienia "Nie wiem" gdy brakuje danych
- Podawania konkretnych wartości liczbowych
- Używania jednostek miary
- Odpowiadania w języku polskim

## Rozwiązywanie problemów

### Problem: Model nie ładuje się

**Rozwiązanie**: Upewnij się, że masz wystarczająco dużo RAM (minimum 16GB). Możesz zmniejszyć rozmiar modelu w `config.py`.

### Problem: Błąd przetwarzania DXF

**Rozwiązanie**: Sprawdź czy plik DXF jest poprawny i nie jest uszkodzony.

### Problem: Brak wyników wyszukiwania

**Rozwiązanie**: Upewnij się, że przetworzyłeś pliki DXF i Excel przed zadawaniem pytań.

### Problem: Aplikacja działa wolno

**Rozwiązanie**: 
- Użyj GPU z CUDA dla przyspieszenia
- Zmniejsz `LLM_MAX_NEW_TOKENS` w konfiguracji
- Zmniejsz liczbę wyników wyszukiwania

## Rozwój

### Dodawanie nowych typów plików

1. Utwórz nowy moduł procesora (np. `pdf_processor.py`)
2. Dodaj obsługę w `chat_app.py`
3. Zaktualizuj `config.py` z nowymi ścieżkami

### Zmiana modelu LLM

1. Zmień `BIELIK_MODEL_NAME` w `config.py`
2. Dostosuj `SYSTEM_PROMPT` do nowego modelu
3. Zaktualizuj format promptu w `llm_integration.py`

### Dodawanie nowych właściwości

1. Zaktualizuj `dxf_processor.py` z nowymi typami obiektów
2. Dodaj mapowanie kolumn w `excel_processor.py`
3. Zaktualizuj `SYSTEM_PROMPT` z nowymi zasadami

## Licencja

MIT License

## Autor

Aplikacja stworzona na potrzeby analizy rysunków technicznych DXF.
Analizy zawardości bazy ERP

## Wsparcie

W przypadku problemów lub pytań, sprawdź sekcję "Rozwiązywanie problemów" lub utwórz issue w repozytorium.
