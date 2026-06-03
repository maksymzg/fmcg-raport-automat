import pandas as pd
import glob
import os

# Ustalamy ze względu na jakosc danych
OCZEKIWANE_KOLUMNY = {"data_sprzedazy", "region", "sprzedawca",
                      "produkt", "ilosc", "cena_jednostkowa", "wartosc"}

# Mapy standaryzacji - klucze pisane MALYMI literami, bo mapujemy po normalizacji.
MAPA_REGIONOW = {
    "dolnoslaskie": "Dolnoslaskie",
    "dolny slask": "Dolnoslaskie",
    "malopolska": "Malopolskie",
    "malopolskie": "Malopolskie",
    "mazowieckie": "Mazowieckie",
    "mazowsze": "Mazowieckie",
    "pomorskie": "Pomorskie",
    "pomorze": "Pomorskie",
    "wielkopolska": "Wielkopolskie",
    "wielkopolskie": "Wielkopolskie",
    "wlkp": "Wielkopolskie",
}

MAPA_PRODUKTOW = {
    "baton czekol. 50g": "Baton czekoladowy 50g",
    "baton czekoladowy 50g": "Baton czekoladowy 50g",
    "chipsy papryk. 150g": "Chipsy paprykowe 150g",
    "chipsy paprykowe 150g": "Chipsy paprykowe 150g",
    "piwo jasne 0.5l": "Piwo jasne 0.5L",
    "sok pomaranczowy 1 l": "Sok pomaranczowy 1L",
    "sok pomaranczowy 1l": "Sok pomaranczowy 1L",
    "woda gaz. 1.5l": "Woda gazowana 1.5L",
    "woda gazowana 1.5l": "Woda gazowana 1.5L",
}
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

def _parsuj_daty(seria):
    # ISO (zaczyna sie od "RRRR-") parsujemy BEZ dayfirst - kolejnosc rok-miesiac-dzien
    # jest jednoznaczna, a dayfirst psulby ja (czytalby dzien jako miesiac).
    # Europejskie (DD.MM.RRRR / DD/MM/RRRR) parsujemy Z dayfirst i format="mixed",
    # bo dzien jest pierwszy, a separatory bywaja rozne (kropka i ukosnik).
    # ZALOZENIE: daty europejskie sa w formacie dzien-pierwszy (DD.MM / DD/MM),
    # bo dane pochodza z polskiej firmy. Pojedynczej dwuznacznej daty (np.
    # "03-04-2023") NIE da sie rozstrzygnac - nie wiadomo, czy to format EU
    # (3 kwietnia) czy US (4 marca). Przy danych z mieszanych zrodel US/EU
    # nalezaloby wykrywac format per plik albo wymusic ISO na wejsciu.
    # Patrz: README, sekcja "Zalozenia i ograniczenia".
    iso = seria.str.match(r"^\d{4}-").fillna(False)
    daty_iso = pd.to_datetime(seria.where(iso), format="ISO8601", errors="coerce")
    daty_eu = pd.to_datetime(seria.where(~iso), format="mixed", dayfirst=True, errors="coerce")
    return daty_iso.fillna(daty_eu)


def czysc_daty(df, raport):
    przed = df["data_sprzedazy"].copy()
    df["data_sprzedazy"] = _parsuj_daty(df["data_sprzedazy"])
    raport["daty_niesparsowane"] = int(df["data_sprzedazy"].isna().sum())
    raport["daty_przeksztalcone"] = int((~przed.str.startswith("2025-")).sum())
    return df

def czysc_liczby(df, raport):
    # CENA: w niektorych wierszach to "4,29" (tekst z przecinkiem) zamiast 4.29.
    # Krok 1: zamien przecinek na kropke. .str.replace dziala na calej kolumnie.
    # Krok 2: pd.to_numeric z errors="coerce" - zamienia tekst na liczbe,
    #         a czego sie nie da (np. puste pole) -> NaN, zamiast wywalic skrypt.
    cena_przed = df["cena_jednostkowa"].copy()
    df["cena_jednostkowa"] = df["cena_jednostkowa"].str.replace(",", ".", regex=False)
    df["cena_jednostkowa"] = pd.to_numeric(df["cena_jednostkowa"], errors="coerce")

    # ile cen bylo zapisanych z przecinkiem (czyli wymagalo naprawy)?
    raport["cena_przecinek"] = int(cena_przed.str.contains(",", na=False).sum())
    # ile cen jest pustych (NaN) po konwersji?
    raport["cena_pusta"] = int(df["cena_jednostkowa"].isna().sum())

    # ILOSC: tekst -> liczba.
    df["ilosc"] = pd.to_numeric(df["ilosc"], errors="coerce")

    # UJEMNE ILOSCI: -112 sztuk to blad (nie da sie sprzedac minus 112).
    # Zakladamy, ze to literowka znaku i bierzemy wartosc bezwzgledna.
    # (Inna mozliwa interpretacja: to ZWROTY towaru - wtedy nalezaloby je
    #  liczyc osobno, nie prostowac znaku. Ktora wersja jest poprawna,
    #  uzgodniloby sie z biznesem. Tu zakladam literowke.)
    ujemne = (df["ilosc"] < 0).sum()
    raport["ilosc_ujemna"] = int(ujemne)
    df["ilosc"] = df["ilosc"].abs()

    return df

# Oznaczanie potencjalnych duplikatow bez usuwania (do weryfikacji przez czlowieka)

def oznacz_duplikaty(df, raport):
    # Nie usuwamy duplikatow, bo bez znacznika czasu / ID transakcji nie da sie
    # odroznic technicznej powtorki od dwoch prawdziwych identycznych transakcji
    # tego samego dnia. Zamiast kasowac (i ryzykowac utrate realnej sprzedazy),
    # OZNACZAMY je do weryfikacji przez czlowieka.

    # porownujemy po oryginalnych kolumnach danych - bez 'plik_zrodlowy',
    # ktore sami dorzucilismy (ta sama transakcja moglaby trafic do 2 plikow).
    kolumny_danych = [k for k in df.columns if k != "plik_zrodlowy"]

    # keep="first" = pierwszy wiersz z powtorki traktujemy jako oryginal (zapis
    # faktu, ktory sie wydarzyl), a oznaczamy dopiero KOLEJNE wystapienia -
    # czyli realnych "kandydatow do usuniecia" dla analityka.
    df["potencjalny_duplikat"] = df.duplicated(subset=kolumny_danych, keep="first")

    raport["duplikaty_do_weryfikacji"] = int(df["potencjalny_duplikat"].sum())
    return df

# --- KLOCEK 4b: standaryzacja tekstu (regiony, produkty) ---

def _normalizuj(seria):
    # Wspolna normalizacja tekstu: usun spacje z brzegow, na male litery,
    # wielokrotne spacje wewnatrz -> pojedyncza. To skleja warianty rozniace
    # sie TYLKO formatowaniem, zanim w ogole siegniemy po mape.
    return (seria.str.strip()
                 .str.lower()
                 .str.replace(r"\s+", " ", regex=True))


def standaryzuj_tekst(df, raport, kolumna, mapa, nazwa_w_raporcie):
    znorm = _normalizuj(df[kolumna])

    # NIEROZPOZNANE: znormalizowane wartosci spoza mapy.
    maska_nieznane = ~znorm.isin(mapa.keys()) & znorm.notna()

    # Zamiast samej listy wartosci - namiar: dla kazdej nierozpoznanej wartosci
    # podajemy plik zrodlowy i numery wierszy, zeby analityk trafil do zrodla.
    nierozpoznane = []
    for wartosc in sorted(znorm[maska_nieznane].unique()):
        wiersze = df[maska_nieznane & (znorm == wartosc)]
        for plik, grupa in wiersze.groupby("plik_zrodlowy"):
            nierozpoznane.append({
                "wartosc": wartosc,
                "plik": plik,
                "wiersze": grupa.index.tolist(),  # indeksy w polaczonej tabeli
                "liczba": len(grupa),
            })
    raport[f"{nazwa_w_raporcie}_nierozpoznane"] = nierozpoznane
    return df

def czysc_sprzedawcow(df, raport):
    # 1. Spacje wokol nazwiska: "  Nowak " -> "Nowak". Inaczej ten sam
    #    sprzedawca liczylby sie jako dwoch roznych w podsumowaniu.
    df["sprzedawca"] = df["sprzedawca"].str.strip()

    # 2. Puste pola: nie zgadujemy, kto to byl (nie zmyslamy nazwiska).
    #    Wpisujemy "Nieznany" - transakcja jest prawdziwa (ma date, produkt,
    #    ilosc), brakuje tylko przypisania do osoby. Usuniecie wiersza
    #    zgubiloby realna sprzedaz. Pusty string i NaN traktujemy tak samo.
    puste = df["sprzedawca"].isna() | (df["sprzedawca"] == "")
    raport["sprzedawca_brak"] = int(puste.sum())
    df["sprzedawca"] = df["sprzedawca"].replace("", pd.NA).fillna("Nieznany")
    return df


def przelicz_wartosc(df, raport):
    # wartosc to wielkosc POCHODNA: powinna wynikac z ilosc * cena.
    # Czesc wierszy ma wartosc niezgodna - traktujemy ilosc i cene jako
    # zrodlo prawdy (dane pierwotne) i przeliczamy wartosc od nowa.
    # (W realnej firmie: uzgodnic z biznesem, ktore pole jest "prawda".)
    df["wartosc"] = pd.to_numeric(df["wartosc"], errors="coerce")
    poprawna = (df["ilosc"] * df["cena_jednostkowa"]).round(2)

    # ile wartosci sie nie zgadzalo (z tolerancja na bledy zaokraglen)?
    # porownujemy tylko tam, gdzie da sie policzyc (cena nie jest pusta).
    da_sie = df["cena_jednostkowa"].notna()
    niezgodne = (da_sie & ((df["wartosc"] - poprawna).abs() > 0.01)).sum()
    raport["wartosc_niezgodna"] = int(niezgodne)

    # przeliczamy wartosc; tam gdzie cena pusta -> wartosc zostaje NaN
    df["wartosc"] = poprawna

    # ile wartosci nie da sie policzyc, bo brakuje ceny?
    raport["wartosc_bez_ceny"] = int(df["wartosc"].isna().sum())
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
    print("Rozklad miesiecy (powinny byc tylko 1,2,3):",
          sorted(df["data_sprzedazy"].dt.month.dropna().unique().tolist()))
    print("Niesparsowane daty:", raport["daty_niesparsowane"])

    df = czysc_liczby(df, raport)
    print("\n--- KLOCEK 3: liczby ---")
    print(f"Cen naprawionych (przecinek -> kropka): {raport['cena_przecinek']}")
    print(f"Cen pustych (do uzupelnienia pozniej):  {raport['cena_pusta']}")
    print(f"Ujemnych ilosci naprawionych:           {raport['ilosc_ujemna']}")
    print(f"\nTyp ceny: {df['cena_jednostkowa'].dtype}, typ ilosci: {df['ilosc'].dtype}")

    df = oznacz_duplikaty(df, raport)
    print("\n--- KLOCEK 4a: duplikaty ---")
    print(f"Wierszy oznaczonych jako potencjalny duplikat: {raport['duplikaty_do_weryfikacji']}")
    print("(NIE usuniete - do weryfikacji przez czlowieka)")

    df = standaryzuj_tekst(df, raport, "region", MAPA_REGIONOW, "region")
    df = standaryzuj_tekst(df, raport, "produkt", MAPA_PRODUKTOW, "produkt")
    print("\n--- KLOCEK 4b: standaryzacja tekstu ---")
    print(f"Regiony po standaryzacji: {sorted(df['region'].dropna().unique())}")
    print(f"Produkty po standaryzacji: {sorted(df['produkt'].dropna().unique())}")

    print("\nNierozpoznane wartosci do poprawienia recznie:")
    nierozpoznane = raport["region_nierozpoznane"] + raport["produkt_nierozpoznane"]
    if not nierozpoznane:
        print("  brak - wszystko rozpoznane")
    for r in nierozpoznane:
        print(f"  Wartosc '{r['wartosc']}' ({r['liczba']}x) nie pasuje. "
              f"Otworz plik '{r['plik']}', znajdz '{r['wartosc']}' (Ctrl+F) i popraw.")
        
    df = czysc_sprzedawcow(df, raport)
    df = przelicz_wartosc(df, raport)
    print("\n--- KLOCEK 5a: sprzedawcy + wartosc ---")
    print(f"Pustych pol sprzedawcy (-> 'Nieznany'): {raport['sprzedawca_brak']}")
    print(f"Niezgodnych wartosci (przeliczone):     {raport['wartosc_niezgodna']}")
    print(f"Wartosci bez ceny (zostaja puste):      {raport['wartosc_bez_ceny']}")

