import pandas as pd
import glob
import os

# Ustalamy ze względu na jakosc danych
OCZEKIWANE_KOLUMNY = {"data_sprzedazy", "region", "sprzedawca",
                      "produkt", "ilosc", "cena_jednostkowa", "wartosc"}

# Wczytanie i polaczenie wszystkich plikow z folderu ---

def wczytaj_dane(folder="dane_surowe"):
    # Kod służy do znalezienia wszystkich plików z rozszerzeniem .csv,
    # które znajdują się w określonym katalogu, i zwrócenia ich w postaci listy uporządkowanej 
    sciezki = sorted(glob.glob(os.path.join(folder, "*.csv")))
    
    ramki = []
    for sciezka in sciezki:
        # Wczytujemy wszystko jako tekst, aby uniknąć konfliktów typów przy łączeniu plików 
        # (np. gdy Pandas różnie zinterpretuje "129,00" w różnych plikach). 
        # Właściwe rzutowanie typów zrobimy ręcznie w kolejnym kroku.
        df = pd.read_csv(sciezka, dtype=str)
        # WALIDACJA: sprawdzamy kolumny KAZDEGO pliku tuz po wczytaniu.
        kolumny_pliku = set(df.columns)
        if kolumny_pliku != OCZEKIWANE_KOLUMNY:
            brakujace = OCZEKIWANE_KOLUMNY - kolumny_pliku   # sa oczekiwane, nie ma ich w pliku
            nadmiarowe = kolumny_pliku - OCZEKIWANE_KOLUMNY  # sa w pliku, nie powinny byc
            raise ValueError(
                f"Plik {sciezka} ma zle kolumny.\n"
                f"  Zamień: {nadmiarowe or 'brak'}"
                f"  Na:  {brakujace or 'brak'}\n"
            )
        df["plik_zrodlowy"] = os.path.basename(sciezka)
        ramki.append(df)

    # concat sklada liste ramek w jedna, jedna pod druga.
    # ignore_index=True = przenumeruj wiersze od 0
    polaczone = pd.concat(ramki, ignore_index=True)
    return polaczone


# Czyszczenie dat (3 formaty -> jeden prawdziwy typ daty) ---

def czysc_daty(df, raport):
    # Mamy 3 formaty w 3 plikach: 2025-01-21 / 21.02.2025 / 21/03/2025.
    # pd.to_datetime z format="mixed" - rozpoznanie kazdego formatu 
    # KAZDEGO wiersza z osobna, a dayfirst=True mowi: gdy zobaczysz
    # "21.02.2025", potraktuj 21 jako DZIEN (europejski zapis), nie miesiac.
    # errors="coerce" = jesli czegos nie da sie sparsowac, wstaw NaT (pusta
    # data) zamiast wywalic caly skrypt. Dzieki temu mozemy potem policzyc, ile dat bylo zepsutych.
    przed = df["data_sprzedazy"].copy()
    df["data_sprzedazy"] = pd.to_datetime(
        df["data_sprzedazy"], format="mixed", dayfirst=True, errors="coerce"
    )

    # ile dat nie dalo sie sparsowac (czyli bylo realnie zepsutych)?
    niesparsowane = df["data_sprzedazy"].isna().sum()
    raport["daty_niesparsowane"] = int(niesparsowane)

    # ile dat NIE bylo w formacie docelowym (czyli wymagalo konwersji)?
    # prosty wskaznik: ile oryginalnych tekstow nie zaczyna sie od "2025-"
    przeksztalcone = (~przed.str.startswith("2025-")).sum()
    raport["daty_przeksztalcone"] = int(przeksztalcone)
    return df


if __name__ == "__main__":
    raport = {}  # tu zbieramy statystyki napraw na potrzeby raportu jakosci
    df = wczytaj_dane()
    print(f"Wczytano {len(df)} wierszy z {df['plik_zrodlowy'].nunique()} plikow\n")

    print("PRZED czyszczeniem dat - przyklady z roznych plikow:")
    print(df.groupby("plik_zrodlowy")["data_sprzedazy"].first().to_string())

    df = czysc_daty(df, raport)

    print("\nPO czyszczeniu dat - ten sam typ, jeden format:")
    print(df.groupby("plik_zrodlowy")["data_sprzedazy"].first().to_string())
    print(f"\nTyp kolumny daty: {df['data_sprzedazy'].dtype}  (datetime, nie tekst!)")
    print(f"Dat przeksztalconych z innego formatu: {raport['daty_przeksztalcone']}")
    print(f"Dat niesparsowanych (zepsutych): {raport['daty_niesparsowane']}")
