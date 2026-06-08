# FMCG – automatyzacja raportu sprzedażowego

*[English version](README.en.md)*

🔗 **Demo na żywo:** https://fmcg-raport-automat-vgeevdu7bdryikyfrmdccx.streamlit.app/

Narzędzie, które bierze surowe, brudne pliki sprzedażowe (takie, jakie realnie
trafiają z systemów do działu raportowania), **wykrywa i naprawia błędy w danych**,
a następnie generuje czysty, sformatowany raport w Excelu - bez ręcznej dłubaniny.
Dostępne jako aplikacja webowa (wgraj pliki → pobierz raport) oraz z linii poleceń.

Cel: pokazać, że typową comiesięczną robotę reporting analyst (godziny czyszczenia
danych w Excelu) można sprowadzić do jednego kliknięcia, **z mierzalnym raportem
jakości danych** na wejściu.

## Problem

Dane sprzedażowe rzadko przychodzą czyste. Tu mamy miesięczne pliki CSV, każdy
wyeksportowany w innym formacie, z typowymi błędami:

| Kategoria błędu | Przykład |
|---|---|
| Różne formaty dat | `2025-01-21`, `21.02.2025`, `15/03/2025` |
| Liczby jako tekst z przecinkiem | `"4,29"` zamiast `4.29` |
| Ujemne ilości | `-112` sztuk |
| Puste pola | brak sprzedawcy, brak ceny |
| Literówki / niespójne nazwy regionów | `Wielkopolska`, `wielkopolskie`, `Wlkp` |
| Literówki / niespójne nazwy produktów | `Chipsy paprykowe 150g` vs `chipsy papryk. 150g` |
| Zduplikowane wiersze | ten sam wiersz skopiowany |
| Niezgodna wartość | `wartość ≠ ilość × cena` |
| Nadmiarowe spacje | `"  Nowak "` |

Dane są **syntetyczne i generowane**: `generuj_dane.py` tworzy zestaw demo
z kontrolowaną liczbą błędów w 9 kategoriach, a `generuj_dane_test.py` tworzy
zestaw testowy z przypadkami brzegowymi dla warstwy fuzzy. Każdy skrypt raportuje
dokładne liczby przy **każdym uruchomieniu** - dzięki temu rezultat jest mierzalny
i weryfikowalny na konkretnych danych, a nie deklaratywny.

## Jak to działa

1. **Wczytanie i konsolidacja** - wszystkie wgrane pliki CSV są walidowane
   (sprawdzenie kolumn) i łączone w jedną tabelę.
2. **Czyszczenie** - daty (3 formaty → jeden typ `datetime`), liczby (cena, ilość),
   standaryzacja regionów i produktów, uzupełnienie sprzedawców, przeliczenie
   wartości.
3. **Dopasowanie rozmyte (fuzzy)** - literówki w nazwach regionów/produktów
   (np. `mazowiekcie`) są automatycznie poprawiane na podstawie podobieństwa do
   znanej listy (rapidfuzz, próg dobrany na danych). Auto-poprawki są raportowane
   **osobno do audytu** - to zgadywanie, więc człowiek może je zweryfikować lub
   cofnąć. Wartości poniżej progu (naprawdę nowe nazwy) trafiają do ręcznej poprawy.
4. **Flagowanie duplikatów** - potencjalne powtórki są oznaczane do weryfikacji,
   a **nie** usuwane (patrz: Założenia i ograniczenia).
5. **Raport jakości** - co i ile zostało naprawione, z rozbiciem na kategorie,
   plus lista nierozpoznanych wartości z namiarem na plik i instrukcją poprawy.
6. **Eksport do Excela** - sformatowany skoroszyt z pięcioma zakładkami: czyste
   dane, podsumowanie sprzedaży, raport jakości, lista do poprawienia i
   auto-poprawki fuzzy do sprawdzenia.

## Uruchomienie

### Aplikacja webowa (lokalnie)

```bash
python3 -m venv venv
source venv/bin/activate        # macOS / Linux
pip install -r requirements.txt
streamlit run app.py
```

Aplikacja otworzy się w przeglądarce: wgraj pliki CSV, zobacz raport jakości,
pobierz gotowy raport Excel.

### Z linii poleceń (na danych z folderu `dane_surowe/`)

```bash
python czyszczenie.py        # wypisuje podsumowanie napraw
python eksport_excel.py      # generuje raporty/raport_sprzedaz.xlsx
python generuj_dane.py       # (opcjonalnie) świeży zestaw danych demo
python generuj_dane_test.py  # (opcjonalnie) zestaw z literówkami - demo fuzzy
```

## Struktura
```bash
fmcg-raport-automat/
├── dane_surowe/          # przykładowy (czysty) zestaw demo - brudne pliki CSV
├── dane_test/            # zestaw z literówkami i nieznanymi wartościami (demo fuzzy)
├── generuj_dane.py       # generator zestawu demo (z kontrolowanymi błędami)
├── generuj_dane_test.py  # generator zestawu testowego (przypadki brzegowe fuzzy)
├── czyszczenie.py        # silnik czyszczenia (funkcja wyczysc_dane)
├── eksport_excel.py      # eksport do Excela (na dysk i do pamięci/BytesIO)
├── app.py                # interfejs webowy (Streamlit)
├── requirements.txt
└── README.md
```
Logika czyszczenia (`czyszczenie.py`) jest niezależna od formatu wyjścia
(`eksport_excel.py`) i od interfejsu (`app.py`). Każdy moduł wystawia funkcje,
więc można je wywołać z aplikacji webowej, skryptu czy harmonogramu.

## Stack

Python (pandas, openpyxl, rapidfuzz), Streamlit. Bez baz danych - celowo lekkie.

## Założenia i ograniczenia

Narzędzie podejmuje kilka świadomych założeń biznesowych. W realnym wdrożeniu
uzgodniłoby się je z zespołem, który zna źródło danych:

- **Format dat:** zakładany jest europejski zapis dzień-pierwszy (`DD.MM.RRRR`,
  `DD/MM/RRRR`), bo dane pochodzą z polskiej firmy. Pojedynczej dwuznacznej daty
  (np. `03-04-2023`) nie da się rozstrzygnąć między formatem europejskim a
  amerykańskim. Przy danych z mieszanych źródeł US/EU należałoby wykrywać format
  per plik albo wymusić ISO (`RRRR-MM-DD`) na wejściu.
- **Ujemne ilości** są traktowane jako literówka znaku (brana wartość bezwzględna).
  Alternatywna interpretacja - zwroty towaru - wymagałaby liczenia osobno.
- **Niezgodna wartość transakcji** jest przeliczana jako `ilość × cena`, czyli
  ilość i cena traktowane są jako źródło prawdy (dane pierwotne).
- **Duplikaty nie są usuwane**, tylko oznaczane do weryfikacji - bez znacznika
  czasu lub ID transakcji nie da się odróżnić technicznej powtórki od dwóch
  prawdziwych identycznych transakcji tego samego dnia.
- **Puste pola sprzedawcy** uzupełniane są wartością `Nieznany` (nie zgadujemy
  nazwiska), a transakcja pozostaje w danych, bo sama sprzedaż jest prawdziwa.

## Status / roadmap

- [x] Wczytanie i konsolidacja wielu plików (z walidacją kolumn)
- [x] Normalizacja dat (3 formaty → jeden typ `datetime`)
- [x] Czyszczenie liczb (cena, ilość)
- [x] Standaryzacja regionów i produktów (z raportem nierozpoznanych)
- [x] Flagowanie duplikatów do weryfikacji
- [x] Uzupełnienie sprzedawców i przeliczenie wartości
- [x] Raport jakości danych
- [x] Eksport do sformatowanego Excela
- [x] Dopasowanie rozmyte literówek do znanej listy (rapidfuzz) z raportem auto-poprawek
- [x] Interfejs webowy (Streamlit) + wdrożenie w chmurze