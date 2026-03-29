# Szybki start - Chat z Bazą Wiedzy DXF

## Instalacja i uruchomienie w 5 krokach

### Krok 1: Zainstaluj zależności

```bash
pip install -r requirements.txt
```

**Uwaga**: Instalacja może potrwać kilka minut, ponieważ pobierane są duże biblioteki (PyTorch, transformers).

### Krok 2: Przygotuj dane

#### Pliki DXF
Umieść pliki DXF w katalogu:
```
data/dxf_drawings/
```

#### Plik Excel
Plik Excel został już utworzony z przykładowymi danymi w:
```
data/properties.xlsx
```

Możesz go edytować lub zastąpić własnymi danymi.

### Krok 3: Uruchom aplikację

```bash
python3 chat_app.py
```

### Krok 4: Otwórz interfejs

Otwórz przeglądarkę i przejdź do:
```
http://localhost:7860
```

### Krok 5: Inicjalizacja

W interfejsie aplikacji wykonaj następujące kroki:

1. **Kliknij "Inicjalizuj aplikację"**
   - Uruchomi to bazę wektorową ChromaDB

2. **Kliknij "Załaduj model LLM"**
   - Załaduje model Bielik (może potrwać 2-5 minut)
   - Wymaga około 7GB RAM

3. **Kliknij "Przetwórz pliki DXF"**
   - Przetworzy wszystkie pliki DXF z katalogu `data/dxf_drawings/`

4. **Kliknij "Przetwórz plik Excel"**
   - Przetworzy dane z pliku `data/properties.xlsx`

5. **Zadaj pytanie!**
   - Wpisz pytanie w polu tekstowym
   - Naciśnij Enter lub kliknij "Wyślij"

## Przykładowe pytania

- "Jaka jest całkowita długość elementów?"
- "Ile metrów kwadratowych powierzchni jest w rysunku?"
- "Jaki jest szacowany czas wykonania?"
- "Ile sztuk elementów typu belka?"
- "Jakie są właściwości belki głównej A?"

## Rozwiązywanie problemów

### Problem: "python: not found"
Użyj `python3` zamiast `python`:
```bash
python3 chat_app.py
```

### Problem: Błąd importu modułów
Zainstaluj zależności:
```bash
pip install -r requirements.txt
```

### Problem: Model nie ładuje się
- Upewnij się, że masz wystarczająco dużo RAM (minimum 16GB)
- Sprawdź połączenie internetowe (pierwsze uruchomienie pobiera model)

### Problem: Brak wyników
- Upewnij się, że przetworzyłeś pliki DXF i Excel
- Sprawdź czy pliki istnieją w odpowiednich katalogach

## Struktura katalogów

```
freeKasia/
├── chat_app.py           # Główna aplikacja
├── config.py             # Konfiguracja
├── dxf_processor.py      # Przetwarzanie DXF
├── excel_processor.py    # Przetwarzanie Excel
├── vector_db.py          # Baza wektorowa
├── llm_integration.py    # Integracja LLM
├── setup.py              # Skrypt inicjalizacji
├── requirements.txt      # Zależności
├── README.md             # Pełna dokumentacja
├── QUICKSTART.md         # Ten plik
├── data/
│   ├── dxf_drawings/     # Pliki DXF
│   └── properties.xlsx   # Dane z Excel
├── vector_db/            # Baza wektorowa
└── models/               # Modele LLM
```

## Następne kroki

Po uruchomieniu aplikacji:

1. **Dodaj własne pliki DXF** do katalogu `data/dxf_drawings/`
2. **Zmodyfikuj plik Excel** z własnymi danymi
3. **Dostosuj konfigurację** w pliku `config.py`
4. **Przetestuj różne pytania** aby zobaczyć jak działa system

## Wsparcie

W przypadku problemów, sprawdź:
- `README.md` - pełna dokumentacja
- `config.py` - konfiguracja aplikacji
- Logi w terminalu - szczegóły błędów
