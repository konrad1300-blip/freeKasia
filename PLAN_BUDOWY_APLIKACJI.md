# Plan Budowy Aplikacji RAG: Analiza DXF, Excel, PDF z Pętlą Samodoskonalenia

## 1. Wstęp i Nowa Architektura Systemu

Aplikacja **freeKasia (v2.0)** to lokalny system RAG (Retrieval-Augmented Generation) zoptymalizowany pod kątem pracy z technicznymi plikami CAD (DXF), arkuszami kalkulacyjnymi (Excel) oraz dokumentacją w formatach PDF.

Wersja 2.0 zastępuje dotychczasowy stos technologiczny (ChromaDB + Bielik 7B) nowym, wysokowydajnym zestawem nakierowanym na dane ścisłe i tabele:
* **LLM Engine**: **Qwen 2.5 14B Instruct** (kwantyzacja Q4_K_M przez silnik Ollama).
* **Baza Wektorowa**: **Qdrant** (z wyszukiwaniem hybrydowym: Dense Vectors + Sparse BM25 Keyword Search).
* **Nowe procesory**: Dedykowany procesor PDF (`pdf_processor.py`) oraz silnik sprzężenia zwrotnego i samodoskonalenia (`feedback_processor.py`).

### Specyfikacja Sprzętowa i Alokacja VRAM (GPU 16GB VRAM)
| Komponent | Zużycie Pamięci VRAM / RAM | Opis |
| :--- | :--- | :--- |
| **Qwen 2.5 14B Instruct (Q4_K_M)** | ~9.0 GB VRAM | Model podstawowy ładowany do GPU przez Ollama |
| **KV Cache & Kontekst (do 32k tokenów)** | ~4.5 GB VRAM | Bufor na długie pytania i konteksty dokumentów |
| **Embedding Model (`bge-m3` / `paraphrase-multilingual`)** | ~1.0 GB VRAM / RAM | Generowanie wektorów gęstych dla tekstu |
| **Qdrant Vector DB (In-Process / Docker)** | ~1.5 GB RAM | Baza przechowywana w RAM / na dysku SSD |
| **Zapas bezpiecznika GPU** | ~1.5 GB VRAM | Zabezpieczenie przed przepełnieniem (OOM) |

---

## 2. Interaktywny Plan Działania (Action Plan)

### Hipoteza początkowa
Połączenie hybrydowego wyszukiwania semantyczno-hasłowego (Qdrant Dense + BM25) z modelem o wysokiej precyzji w naukach ścisłych (Qwen 2.5 14B) oraz pętlą samodoskonalenia (selektywna archiwizacja i ponowna wektoryzacja zweryfikowanych przez człowieka odpowiedzi) pozwoli wyeliminować halucynacje w obliczeniach technicznych o ponad 90% i stworzy system adaptujący się do slangu zakładowego ERP/CAD bez dostrajania wag modelu (fine-tuningu).

### Mapa działania
1. **Faza I – Przygotowanie środowiska i migracji (Dni 1-2)**:
   * Instalacja i konfiguracja Ollama z modelem `qwen2.5:14b-instruct-q4_K_M`.
   * Inicjalizacja hybrydowej bazy Qdrant (`qdrant-client`).
   * Utworzenie schematu bazy relacyjnej SQLite dla logów i historii sesji.
2. **Faza II – Rozbudowa warstwy procesorów danych (Dni 3-5)**:
   * Refaktoryzacja `dxf_processor.py` i `excel_processor.py` pod kątem ekstrakcji słów kluczowych do BM25.
   * Implementacja `pdf_processor.py` (ekstrakcja strukturalna: nagłówki, strony, tabele).
3. **Faza III – Wdrożenie Pętli Samodoskonalenia (Dni 6-7)**:
   * Implementacja `feedback_processor.py` do rejestracji ocen i edycji odpowiedzi.
   * Utworzenie kolekcji `verified_chat_history` w Qdrant i mechanizmu automatycznego re-indeksowania.
4. **Faza IV – Integracja RAG i Prompt Engineering (Dni 8-9)**:
   * Implementacja hybrydowego wyszukiwacza RAG łączącego 4 źródła: DXF, Excel, PDF i Zweryfikowaną Historię.
   * Konstrukcja ustrukturyzowanych promptów systemowych z wymuszeniem formatu JSON/Markdown.
5. **Faza V – Interfejs i Testy (Dni 10-12)**:
   * Budowa nowego UI w Gradio / Streamlit z obsługą podglądu źródeł i przyciskami feedbacku.
   * Testy wydajnościowe na GPU 16GB VRAM i weryfikacja dokładności obliczeń.

### Punkty krytyczne (Konieczne działania użytkownika)
* **Zatwierdzanie wpisów do pamięci**: Aplikacja NIE indeksuje automatycznie każdej odpowiedzi. Użytkownik musi kliknąć przycisk "Zatwierdź" lub wpisać poprawną wersję.
* **Przygotowanie skanów PDF (OCR)**: Jeśli plik PDF zawiera nieprzeszukiwalne obrazy/skany rysunków, użytkownik musi uruchomić zewnętrzny moduł OCR lub udostępnić plik PDF z warstwą tekstową.

### Rola użytkownika – Ścieżki
1. **Ścieżka Analityczna (Użytkownik Standardowy)**: Wgrywanie plików, zadawanie pytań i pobieranie gotowych zestawień.
2. **Ścieżka Trenera (Ekspert Domenowy)**: Ocenianie odpowiedzi, korygowanie błędów w interpretacji rysunków DXF/norm PDF oraz zasilanie bazy wiedzy.

---

## 3. Architektura Przepływu Danych i Layout Interfejsu

### Schemat Przepływu Danych (ASCII Flow Diagram)

```
[ Wgrywanie Plików ]
   ├── Pliki DXF ───────> ( dxf_processor ) ──────┐
   ├── Pliki Excel ─────> ( excel_processor ) ────┼──> [ Qdrant Engine ]
   └── Pliki PDF ───────> ( pdf_processor ) ──────┘     ├── Kolekcja: dxf_properties
                                                        ├── Kolekcja: excel_data
                                                        ├── Kolekcja: pdf_documents
                                                        └── Kolekcja: verified_chat_history
                                                                  ▲
[ Pytań Użytkownika ] ────────┐                                   │ (Autokorekta)
                              ▼                                   │
                     [ Hybrydowy RAG ] ───────────────────────────┤
                     (Dense + Sparse BM25)                        │
                              │                                   │
                              ▼                                   │
                   [ Context Construction ]                       │
                              │                                   │
                              ▼                                   │
                  [ Ollama: Qwen 2.5 14B ]                        │
                              │                                   │
                              ▼                                   │
                    [ Wyświetlenie Odpowiedzi ]                   │
                              │                                   │
                   [ Ocena Użytkownika ] ─────────────────────────┘
                    👍 / 👎 / ✏️ Korekta ──> ( feedback_processor ) ──> [ SQLite Log ]
```

### Layout Interfejsu Użytkownika (ASCII Wireframe)

```
+-----------------------------------------------------------------------------------+
|  freeKasia v2.0 - Asystent CAD/ERP z Pętlą Samodoskonalenia                       |
+----------------------------------------------------+------------------------------+
| LEWY PANEL: Baza Wiedzy & Pliki                    | PRAWY PANEL: Okno Chatu      |
+----------------------------------------------------+------------------------------+
| 📁 Przetwarzanie Dokumentów                        | 💬 Konwersacja               |
| [ Wybierz pliki DXF / PDF / Excel                ] |                               |
| Przycisk: [ ⚙️ Indeksuj Wszystkie Pliki          ] | Użytkownik: Jaka jest powie- |
|                                                    | rzchnia elementu A i opis    |
| Status Indeksowania:                               | z normy ISO w PDF?           |
| - DXF: 12 plików zindeksowanych                    |                              |
| - Excel: properties.xlsx (450 wierszy)             | Qwen 2.5 14B:                |
| - PDF: 3 specyfikacje (84 strony)                  | Powierzchnia elementu A:     |
| - Pamięć Korekt: 28 zweryfikowanych odpowiedzi     | 14.2 m2 (Rysunek: A12.dxf).  |
|                                                    | Zgodnie z PDF (str. 12):     |
| -------------------------------------------------- | Norma nakłada tolerancję ±2%.|
| 📊 Statystyki Systemu                              | Źródła: [A12.dxf], [norma.pdf]|
| - GPU VRAM: 11.2 / 16.0 GB                         | ---------------------------- |
| - Qdrant Vector Count: 1,420                      | Ocena odpowiedzi:            |
| - Model Status: Qwen 2.5 14B (Ready)               | [ 👍 Zatwierdź ] [ 👎 Błąd ] |
|                                                    | [ ✏️ Edytuj i Zapisz Wzorzec]|
+----------------------------------------------------+------------------------------+
| Wpisz pytanie: [                                                        ] [ Wyślij ]
+-----------------------------------------------------------------------------------+
```

---

## 4. Struktura Katalogów Projektu

```
freeKasia/
├── README.md                     # Dokumentacja główna projektu
├── PLAN_BUDOWY_APLIKACJI.md      # Niniejszy plik z planem architektonicznym
├── requirements.txt              # Zależności bibliotek Python
├── config.py                     # Centralna konfiguracja (ścieżki, parametry VRAM, Qdrant)
│
├── app/
│   ├── __init__.py
│   ├── main.py                   # Główny punkt wejścia aplikacji
│   │
│   ├── processors/               # Warstwa przetwarzania plików źródłowych
│   │   ├── __init__.py
│   │   ├── dxf_processor.py      # Ekstrakcja geometrii i warstw z DXF
│   │   ├── excel_processor.py    # Odczyt arkuszy i mapowanie kolumn ERP
│   │   ├── pdf_processor.py      # Ekstrakcja tekstu, tabel i metadanych z PDF
│   │   └── feedback_processor.py # Obsługa korekt, ocen i samodoskonalenia
│   │
│   ├── database/                 # Warstwa przechowywania danych
│   │   ├── __init__.py
│   │   ├── vector_db.py          # Klient Qdrant (Hybrid Search, Dense + BM25)
│   │   └── sqlite_db.py          # Baza relacyjna na sesje chatu i logi ocen
│   │
│   ├── llm/                      # Integracja z modelem językowym
│   │   ├── __init__.py
│   │   ├── llm_integration.py    # Obsługa API Ollama (Qwen 2.5 14B)
│   │   └── prompt_templates.py   # Szablony promptów systemowych i Few-Shot
│   │
│   └── ui/                       # Interfejs graficzny
│       ├── __init__.py
│       └── gradio_app.py         # Ekran chatu, wgrywania plików i paneli oceny
│
├── data/                         # Katalog przechowywania plików
│   ├── dxf_drawings/             # Surowe pliki DXF
│   ├── pdf_documents/            # Pliki specyfikacji PDF
│   ├── excel_files/              # Pliki właściwości Excel
│   └── qdrant_storage/           # Lokalny katalog danych Qdrant (embedded)
│
└── storage/                      # Pliki baz relacyjnych i logów
    ├── app_database.db           # Baza SQLite
    └── app.log                   # Logi systemowe
```

---

## 5. Dokument PRD (Product Requirements Document) dla Modułów

### PRD 1: Procesor Rysunków Technicznych DXF (`dxf_processor.py`)
1. **Cel funkcji**: Ekstrakcja obiektów geometrycznych, wymiarów, powierzchni i warstw z rysunków DXF na potrzeby wyszukiwania wektorowego.
2. **User Flow**:
   1. Użytkownik umieszcza pliki DXF w katalogu lub wgrywa je przez UI.
   2. Użytkownik uruchamia przetwarzanie DXF.
   3. Moduł parsuje geometrie (linie, polilinie, łuki, bloki, teksty).
   4. Moduł oblicza sumaryczne długości, pola powierzchni i zlicza elementy.
   5. Moduł przekazuje ustrukturyzowane rekordy do bazy Qdrant.
3. **Baza Danych**:
   * **Kolekcja Qdrant**: `dxf_properties`
   * **Payload (Metadata)**: `file_name` (string), `layer` (string), `total_length` (float), `total_area` (float), `entity_counts` (json), `text_annotations` (array of strings).
4. **Endpointy API**:
   * `POST /api/v1/dxf/process` – uruchamia skanowanie i indeksowanie plików DXF.
   * `GET /api/v1/dxf/summary/{file_name}` – zwraca podsumowanie wymiarowe wybranego rysunku.
5. **Kryteria DONE**:
   * Bezproblemowy odczyt geometrii i pól powierzchni z zamkniętych polilinii.
   * Poprawne wygenerowanie podsumowania tekstowego gotowego do zindeksowania.
   * Zapis rekordu w Qdrant z pełnymi metadanymi pliku źródłowego.

---

### PRD 2: Procesor Danych ERP/Excel (`excel_processor.py`)
1. **Cel funkcji**: Mapowanie struktury tabelarycznej plików Excel (ceny, czasy, właściwości materiałowe) na reprezentację semantyczno-hasłową.
2. **User Flow**:
   1. Użytkownik wgrywa plik Excel z właściwościami elementów.
   2. Moduł waliduje nagłówki kolumn (nazwa, ilość, czas, powierzchnia, opis).
   3. Moduł konwertuje każdy wiersz na czytelny dla LLM opis naturalny oraz zestaw atrybutów.
   4. Moduł generuje wektory gęste oraz indeksy słów kluczowych BM25.
   5. Moduł zapisuje dane w kolekcji Qdrant.
3. **Baza Danych**:
   * **Kolekcja Qdrant**: `excel_data`
   * **Payload**: `row_id` (int), `element_name` (string), `quantity` (float), `execution_time_h` (float), `raw_row_data` (json).
4. **Endpointy API**:
   * `POST /api/v1/excel/upload` – wgrywanie i walidacja struktury pliku `.xlsx`.
   * `POST /api/v1/excel/index` – konwersja wierszy i zapis do bazy wektorowej.
5. **Kryteria DONE**:
   * Automatyczne rozpoznanie kluczowych kolumn (niezależnie od wielkości liter i polskich znaków).
   * Poprawna interpretacja wartości liczbowych oraz jednostek miary.
   * Dostępność danych z Excela w wyszukiwaniu hybrydowym.

---

### PRD 3: Procesor Dokumentów PDF (`pdf_processor.py`)
1. **Cel funkcji**: Parsowanie specyfikacji technicznych, norm oraz kart katalogowych PDF z zachowaniem struktury stron i tabel.
2. **User Flow**:
   1. Użytkownik wgrywa dokument PDF.
   2. Moduł ekstrahuje tekst, nagłówki oraz układy tabelaryczne (przy użyciu `pdfplumber` / `pypdf`).
   3. Dokument jest dzielony na chunki semantyczne (200-500 słów) z nakładkowaniem (overlap 10%).
   4. Tabele są konwertowane do formatu Markdown/CSV i dołączane jako osobne bloki wiedzy.
   5. Chunki i tabele trafiają do kolekcji Qdrant z numeracją stron.
3. **Baza Danych**:
   * **Kolekcja Qdrant**: `pdf_documents`
   * **Payload**: `file_name` (string), `page_number` (int), `chunk_type` (string: "text" | "table"), `content` (string).
4. **Endpointy API**:
   * `POST /api/v1/pdf/process` – przetwarzanie i chunkowanie dokumentu PDF.
   * `GET /api/v1/pdf/search` – bezpośrednie wyszukiwanie fragmentu w PDF.
5. **Kryteria DONE**:
   * Wyekstrahowanie tabel bez utraty spójności kolumn i wierszy.
   * Dopisanie do każdego fragmentu dokładnego numeru strony źródłowej.
   * Indeksacja w Qdrant umożliwiająca precyzyjne odnalezienie zapisów normatywnych.

---

### PRD 4: Hybrydowa Baza Wektorowa Qdrant (`vector_db.py`)
1. **Cel funkcji**: Zapewnienie ultrawydajnego wyszukiwania hybrydowego (Dense + Sparse BM25) we wszystkich zasobach wiedzy.
2. **User Flow**:
   1. Moduł otrzymuje zapytanie tekstowe z komponentu RAG.
   2. Moduł generuje wektor gęsty (embedding) oraz wektor rzadki (BM25 tokens).
   3. Qdrant wykonuje równoległe wyszukiwanie w połączonych kolekcjach z użyciem Fused Rank (RRF).
   4. Zwracana jest lista N najbardziej trafnych kontekstów wraz ze wskaźnikiem pewności (score).
3. **Baza Danych**:
   * **Silnik**: Qdrant Engine (Embedded lub Docker).
   * **Kolekcje**: `dxf_properties`, `excel_data`, `pdf_documents`, `verified_chat_history`.
   * **Konfiguracja Wektorów**: Dense Vector Size: 1024 (np. BGE-M3), Sparse Vector Indexing enabled.
4. **Endpointy API**:
   * `POST /api/v1/vector/search` – hybrydowe wyszukiwanie po kolekcjach.
   * `DELETE /api/v1/vector/collection/{name}` – czyszczenie wybranej kolekcji.
5. **Kryteria DONE**:
   * Odnajdywanie ciągów znaków i kodów katalogowych z czystością 100% dzięki BM25.
   * Czas wyszukiwania ponżej 50 ms dla bazy 50 000 wektorów.
   * Poprawne scalanie wyników z wielu kolekcji jednocześnie.

---

### PRD 5: Integracja LLM Ollama & Qwen 2.5 14B (`llm_integration.py`)
1. **Cel funkcji**: Generowanie precyzyjnych odpowiedzi w języku polskim w oparciu o dostarczony kontekst techniczny oraz formatowanie ustrukturyzowane.
2. **User Flow**:
   1. Moduł otrzymuje zebrany kontekst z Qdrant oraz pytania użytkownika.
   2. Konstruowany jest prompt systemowy nakazujący brak halucynacji i powoływanie się na źródła.
   3. Zapytanie wysyłane jest do lokalnej instancji Ollama (`qwen2.5:14b-instruct-q4_K_M`).
   4. Model generuje strumieniowo odpowiedź (streaming response).
   5. Odpowiedź zostaje przekazana do interfejsu użytkownika.
3. **Baza Danych**:
   * Brak bezpośredniej bazy – obsługa komunikacji REST API z Ollama (`http://localhost:11434`).
4. **Endpointy API**:
   * `POST /api/v1/llm/generate` – generowanie odpowiedzi z podanym promptem kontekstowym.
   * `GET /api/v1/llm/status` – sprawdzanie stanu załadowania modelu do VRAM.
5. **Kryteria DONE**:
   * Generowanie odpowiedzi wyłącznie na podstawie przekazanego kontekstu (zasada "Nie wiem, jeśli brak w danych").
   * Wykorzystanie możliwości kontekstowych Qwen 2.5 do bezbłędnej analizy tabel.
   * Płynna generacja odpowiedzi na poziomie >15 tokenów/sekundę na GPU 16GB.

---

### PRD 6: Pętla Samodoskonalenia i Sprzężenie Zwrotne (`feedback_processor.py`)
1. **Cel funkcji**: Rejestracja ocen użytkowników, obsługa ręcznych korekt oraz zasilanie kolekcji `verified_chat_history` w celu ciagłego podnoszenia jakości odpowiedzi.
2. **User Flow**:
   1. Użytkownik przegląda odpowiedź generowaną przez model.
   2. Użytkownik klika "Zatwierdź" lub wpisuje poprawną wersję w polu "Edytuj i Zapisz Wzorzec".
   3. Moduł zapisuje oryginalne pytanie, odpowiedź i korektę w bazie SQLite.
   4. Moduł tworzy nowy obiekt wiedzy i wysyła go do kolekcji Qdrant `verified_chat_history`.
   5. Przy kolejnych pytaniach RAG włącza zweryfikowany wzorzec jako przykład Few-Shot.
3. **Baza Danych**:
   * **Baza SQLite (`storage/app_database.db`)**: Tabela `feedback_logs`:
     * `id` (INTEGER PK AUTOINCREMENT)
     * `timestamp` (DATETIME)
     * `user_query` (TEXT)
     * `model_response` (TEXT)
     * `corrected_response` (TEXT)
     * `rating` (INTEGER: 1 lub -1)
     * `status` (TEXT: "APPROVED" | "REJECTED" | "CORRECTED")
   * **Kolekcja Qdrant**: `verified_chat_history`
4. **Endpointy API**:
   * `POST /api/v1/feedback/submit` – zapis oceny lub korekty.
   * `GET /api/v1/feedback/history` – lista wszystkich zapisanych korekt.
5. **Kryteria DONE**:
   * Przycisk zatwierdzenia natychmiastowo zasila bazę Qdrant bez konieczności restartu aplikacji.
   * Zapisana korekta ma najwyższy priorytet w wyszukiwaniu RAG przy podobnych pytaniach.
   * Pełna historia poprawek jest dostępna do wglądu i edycji w bazie SQLite.

---

### PRD 7: Interfejs Chat & Panel Kontrolny (`gradio_app.py`)
1. **Cel funkcji**: Zapewnienie intuicyjnego, jednostronicowego interfejsu do pracy z dokumentami, prowadzenia rozmowy i zarządzania pamięcią systemu.
2. **User Flow**:
   1. Użytkownik uruchamia aplikację w przeglądarce (`http://localhost:7860`).
   2. W lewym panelu zarządza plikami źródłowymi i widzi stan załadowania bazy.
   3. W prawym panelu prowadzi chat, przegląda cytowane źródła i ocenia odpowiedzi.
   4. W razie błędu edytuje treść bezpośrednio w panelu feedbacku.
3. **Baza Danych**:
   * **Baza SQLite**: Tabela `chat_sessions` oraz `chat_messages` do utrzymania historii konwersacji.
4. **Endpointy API**:
   * `GET /` – widok aplikacji Gradio.
   * `POST /api/v1/chat/reset` – czyszczenie pamięci podręcznej rozmowy.
5. **Kryteria DONE**:
   * Czysty, bezżargonowy układ interfejsu (prosty jak na kartce).
   * Widoczność przypisanych źródeł (np. nazwa pliku DXF, strona PDF) przy każdej odpowiedzi.
   * Działające przyciski oceny i edycji wpisów.

---

## 6. Instrukcja Instalacji i Uruchomienia

### Krok 1: Wymagania wstępne
* Python 3.10 lub 3.11
* Karta graficzna Nvidia z 16GB VRAM (np. RTX 4080, RTX 3090, RTX 4070 Ti Super) + sterowniki CUDA 12.x
* Zainstalowana **Ollama** (https://ollama.com)

### Krok 2: Pobranie Modelu Qwen 2.5 14B w Ollama
```bash
ollama run qwen2.5:14b-instruct-q4_K_M
```

### Krok 3: Przygotowanie Środowiska Python
```bash
git clone <repo-url> freeKasia
cd freeKasia

python -m venv venv
# Linux / macOS:
source venv/bin/activate
# Windows:
venv\Scriptsctivate

pip install -r requirements.txt
```

### Krok 4: Zawartość pliku `requirements.txt`
```text
qdrant-client>=1.9.0
fastapi>=0.110.0
uvicorn>=0.28.0
gradio>=4.20.0
ezdxf>=1.1.0
openpyxl>=3.1.0
pandas>=2.2.0
pdfplumber>=0.11.0
pypdf>=4.1.0
sentence-transformers>=2.6.0
torch>=2.2.0
requests>=2.31.0
pydantic>=2.6.0
```

### Krok 5: Uruchomienie Aplikacji
```bash
python app/main.py
```
Aplikacja otworzy się automatycznie pod adresem: `http://localhost:7860`.

---
*Dokument wygenerowany jako interaktywny plan budowy dla projektu freeKasia v2.0.*
