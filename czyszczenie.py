import pandas as pd
import glob
import os

# --- KLOCEK 1: wczytanie i polaczenie wszystkich plikow z folderu ---

def wczytaj_dane(folder="dane_surowe"):
    # glob znajduje WSZYSTKIE pliki .csv w folderze - nowy miesiac = nowy plik,
    # i kod sam go zlapie, bez zadnych zmian. To wazne w realnej pracy:
    # raport ma dzialac co miesiac bez przepisywania sciezek.
    sciezki = sorted(glob.glob(os.path.join(folder, "*.csv")))

    ramki = []
    for sciezka in sciezki:
        # dtype=str = wczytaj WSZYSTKO jako tekst.
        # Kluczowe przy brudnych danych: gdyby pandas sam zgadywal typy,
        # "129,00" czy ujemne ilosci mialyby rozne typy w roznych plikach
        # i polaczenie by sie posypalo. Najpierw wczytujemy "na surowo",
        # a typy nadajemy SAMI, swiadomie, w kolejnych klockach.
        df = pd.read_csv(sciezka, dtype=str)

        # zapamietujemy, z ktorego pliku pochodzi wiersz - przyda sie
        # w raporcie jakosci ("w pliku lutowym bylo X bledow").
        df["plik_zrodlowy"] = os.path.basename(sciezka)
        ramki.append(df)

    # concat sklada liste ramek w jedna, jedna pod druga.
    # ignore_index=True = przenumeruj wiersze od 0 (inaczej kazdy plik
    # mialby wlasne 0,1,2... i indeks bylby zduplikowany).
    polaczone = pd.concat(ramki, ignore_index=True)
    return polaczone


# --- KLOCEK 2: czyszczenie dat (3 formaty -> jeden prawdziwy typ daty) ---

def czysc_daty(df, raport):
    # Mamy 3 formaty w 3 plikach: 2025-01-21 / 21.02.2025 / 21/03/2025.
    # pd.to_datetime z format="mixed" pozwala pandasowi rozpoznac format
    # KAZDEGO wiersza z osobna, a dayfirst=True mowi: gdy zobaczysz
    # "21.02.2025", potraktuj 21 jako DZIEN (europejski zapis), nie miesiac.
    # errors="coerce" = jesli czegos nie da sie sparsowac, wstaw NaT (pusta
    # data) zamiast wywalic caly skrypt. W realnej pracy NIGDY nie chcesz,
    # zeby jeden zepsuty wiersz zatrzymal raport - chcesz go ZLAPAC i zglosic.
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
