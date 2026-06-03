# FMCG – automatyzacja raportu sprzedażowego

Narzędzie, które bierze surowe, brudne pliki sprzedażowe (takie, jakie realnie
trafiają z systemów do działu raportowania), **wykrywa i naprawia błędy w danych**,
a następnie generuje czysty, sformatowany raport w Excelu — bez ręcznej dłubaniny.

Cel: pokazać, że typową comiesięczną robotę reporting analyst (godziny czyszczenia
danych w Excelu) można sprowadzić do jednego uruchomienia, **z mierzalnym raportem
jakości danych** na wejściu.

## Problem

Dane sprzedażowe rzadko przychodzą czyste. Tu mamy trzy miesięczne pliki CSV, każdy
wyeksportowany w innym formacie, z typowymi błędami:

| Kategoria błędu | Przykład |
|---|---|
| Różne formaty dat | `2025-01-21`, `21.02.2025`, `15/03/2025` |
| Liczby jako tekst z przecinkiem | `"4,29"` zamiast `4.29` |
| Ujemne ilości | `-112` sztuk |
| Puste pola | brak sprzedawcy, brak ceny |
| Literówki / niespójne nazwy regionów | `Wielkopolska`, `wielkopolskie`, `Wlkp` |
| Literówki / niespójne nazwy produktów | `Chipsy paprykowe 150g` vs `chipsy papryk. 150g` |
| Zduplikaty wierszy | ten sam wiersz skopiowany |
| Niezgodna wartość | `wartość ≠ ilość × cena` |
| Nadmiarowe spacje | `"  Nowak "` |

Dane są **syntetyczne i generowane** (`generuj_dane.py`) z kontrolowaną liczbą
błędów — dzięki temu wiadomo dokładnie, ile problemów jest na wejściu i można
zweryfikować, że narzędzie naprawiło wszystkie (klucz odpowiedzi: **258 błędów**).

## Jak to działa

1. **Wczytanie i konsolidacja** — `glob` łapie wszystkie pliki CSV z folderu
   (nowy miesiąc = nowy plik, zero zmian w kodzie), łączy w jedną tabelę.
2. **Czyszczenie kolumna po kolumnie** — daty, liczby, regiony, produkty, duplikaty.
3. **Raport jakości** — co i ile zostało naprawione, z rozbiciem na kategorie.
4. **Eksport do Excela** — sformatowany arkusz z podsumowaniem.

## Uruchomienie

```bash
# 1. utwórz i aktywuj środowisko wirtualne
python3 -m venv venv
source venv/bin/activate        # macOS / Linux

# 2. zainstaluj zależności
pip install -r requirements.txt

# 3. (opcjonalnie) wygeneruj świeży zestaw danych testowych
python generuj_dane.py

# 4. uruchom czyszczenie
python czyszczenie.py
```

## Struktura

```
fmcg-raport-automat/
├── dane_surowe/        # przykładowe brudne pliki CSV
├── generuj_dane.py     # generator danych testowych (z kontrolowanymi błędami)
├── czyszczenie.py      # silnik: wczytanie -> czyszczenie -> raport
├── requirements.txt
└── README.md
```

## Stack

Python (pandas), openpyxl. Bez baz danych — celowo lekkie, uruchamialne lokalnie.

## Założenia i ograniczenia

Narzędzie podejmuje kilka świadomych założeń biznesowych. W realnym wdrożeniu
uzgodniłoby się je z zespołem, który zna źródło danych:

- **Format dat:** zakładany jest europejski zapis dzień-pierwszy (`DD.MM.RRRR`,
  `DD/MM/RRRR`), bo dane pochodzą z polskiej firmy. Pojedynczej dwuznacznej daty
  (np. `03-04-2023`) nie da się rozstrzygnąć między formatem europejskim a
  amerykańskim. Przy danych z mieszanych źródeł US/EU należałoby wykrywać format
  per plik albo wymusić ISO (`RRRR-MM-DD`) na wejściu.
- **Ujemne ilości** są traktowane jako literówka znaku (brana wartość bezwzględna).
  Alternatywna interpretacja — zwroty towaru — wymagałaby liczenia osobno.
- **Niezgodna wartość transakcji** jest przeliczana jako `ilość × cena`, czyli
  ilość i cena traktowane są jako źródło prawdy (dane pierwotne).
- **Duplikaty nie są usuwane**, tylko oznaczane do weryfikacji — bez znacznika
  czasu lub ID transakcji nie da się odróżnić technicznej powtórki od dwóch
  prawdziwych identycznych transakcji tego samego dnia.
- **Puste pola sprzedawcy** uzupełniane są wartością `Nieznany` (nie zgadujemy
  nazwiska), a transakcja pozostaje w danych, bo sama sprzedaż jest prawdziwa.
## Status / roadmap

- [x] Wczytanie i konsolidacja wielu plików
- [x] Normalizacja dat (3 formaty → jeden typ `datetime`)
- [ ] Czyszczenie liczb (cena, ilość)
- [ ] Standaryzacja regionów i produktów
- [ ] Usuwanie duplikatów i przeliczenie wartości
- [ ] Raport jakości danych
- [ ] Eksport do sformatowanego Excela
- [ ] Interfejs dla użytkownika nietechnicznego (planowane)
