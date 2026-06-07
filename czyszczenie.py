"""
Silnik czyszczenia danych sprzedazowych FMCG.

Wczytuje surowe pliki CSV (z folderu lub z uploadu), naprawia typowe bledy
(daty w roznych formatach, liczby jako tekst, ujemne ilosci, literowki nazw,
duplikaty, niezgodne wartosci) i zwraca czysty DataFrame wraz z raportem
jakosci. Logika jest niezalezna od formatu wyjscia i od interfejsu.
"""
import pandas as pd
import glob
import os
from rapidfuzz import process, fuzz

# Prog podobienstwa (0-100) dla dopasowania rozmytego literowek. Powyzej progu
# wartosc jest AUTO-poprawiana; ponizej - trafia do recznej weryfikacji.
# Dobrany na danych: literowki ~89-92, naprawde nowe nazwy ~41-74 (luka ~85).
PROG_FUZZY = 85

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
# Wczytanie i polaczenie wszystkich plikow z folderu

def _wczytaj_jeden(zrodlo, nazwa):
    """Wczytuje jeden CSV (sciezka LUB obiekt plikopodobny), waliduje kolumny,
    dodaje plik_zrodlowy. Wspolna logika dla wczytywania z folderu i z uploadu."""
    df = pd.read_csv(zrodlo, dtype=str)
    kolumny_pliku = set(df.columns)
    if kolumny_pliku != OCZEKIWANE_KOLUMNY:
        brakujace = OCZEKIWANE_KOLUMNY - kolumny_pliku
        nadmiarowe = kolumny_pliku - OCZEKIWANE_KOLUMNY
        raise ValueError(
            f"Plik {nazwa} ma zle kolumny.\n"
            f"  Brakuje:    {brakujace or 'brak'}\n"
            f"  Nadmiarowe: {nadmiarowe or 'brak'}\n"
            f"  Popraw naglowki w pliku, aby pasowaly do oczekiwanych kolumn."
        )
    df["plik_zrodlowy"] = nazwa
    return df


def wczytaj_dane(folder="dane_surowe"):
    """Wczytuje wszystkie CSV z folderu (uzycie lokalne / terminal)."""
    sciezki = sorted(glob.glob(os.path.join(folder, "*.csv")))
    ramki = [_wczytaj_jeden(s, os.path.basename(s)) for s in sciezki]
    return pd.concat(ramki, ignore_index=True)


def wczytaj_pliki(pliki):
    """Wczytuje liste wgranych plikow (obiekty ze Streamlit file_uploader).
    Kazdy ma atrybut .name (nazwa) i jest plikopodobny (pandas go odczyta)."""
    ramki = [_wczytaj_jeden(p, p.name) for p in pliki]
    return pd.concat(ramki, ignore_index=True)


# Czyszczenie dat (3 formaty -> jeden prawdziwy typ daty) ---

def _parsuj_daty(seria):
    # Parsuje daty z trzech formatow (ISO, DD.MM, DD/MM) do jednego typu datetime.
    # ISO (RRRR-MM-DD) parsujemy bez dayfirst - kolejnosc jest jednoznaczna.
    # Europejskie (DD.MM / DD/MM) z dayfirst, bo dzien jest pierwszy.
    # Zalozenie: format europejski dzien-pierwszy (dane z polskiej firmy).
    # Dwuznacznej daty jak "03-04-2023" nie da sie rozstrzygnac EU/US 
    # README, sekcja "Zalozenia i ograniczenia".
    # podzial ISO / europejskie jest konieczny, bo dayfirst psuje daty ISO
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
    # Zamienia przecinek na kropke. .str.replace na calej kolumnie.
    # pd.to_numeric z errors="coerce" - zamienia tekst na liczbe,
    # a czego sie nie da (np. puste pole) -> NaN, zamiast wywalic skrypt.
    cena_przed = df["cena_jednostkowa"].copy()
    df["cena_jednostkowa"] = df["cena_jednostkowa"].str.replace(",", ".", regex=False)
    df["cena_jednostkowa"] = pd.to_numeric(df["cena_jednostkowa"], errors="coerce")

    # ile cen bylo zapisanych z przecinkiem (czyli wymagalo naprawy)?
    raport["cena_przecinek"] = int(cena_przed.str.contains(",", na=False).sum())
    # ile cen jest pustych (NaN) po konwersji?
    raport["cena_pusta"] = int(df["cena_jednostkowa"].isna().sum())

    # ILOSC: tekst -> liczba.
    df["ilosc"] = pd.to_numeric(df["ilosc"], errors="coerce")

    # UJEMNE ILOSCI: Np. -112 sztuk to blad (nie da sie sprzedac minus 112).
    # Zakladamy, ze to literowka znaku i bierzemy wartosc bezwzgledna.
    # (Inna mozliwa interpretacja: to ZWROTY towaru - wtedy nalezaloby je
    #  liczyc osobno, nie prostowac znaku. Ktora wersja jest poprawna,
    #  uzgodniloby sie z biznesem. Tu zakladam literowke. Opisane w README.)
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

# Standaryzacja tekstu (regiony, produkty)

def _normalizuj(seria):
    # Wspolna normalizacja tekstu: usun spacje z brzegow, na male litery,
    # wielokrotne spacje wewnatrz -> pojedyncza. To skleja warianty rozniace
    # sie tylko formatowaniem.
    return (seria.str.strip()
                 .str.lower()
                 .str.replace(r"\s+", " ", regex=True))


def standaryzuj_tekst(df, raport, kolumna, mapa, nazwa_w_raporcie):
    znorm = _normalizuj(df[kolumna])

    # 1. DOPASOWANIE DOKLADNE: znormalizowana wartosc obecna w mapie.
    docelowa = znorm.map(mapa)

    # 2. FUZZY: dla wartosci NIE w mapie szukamy najblizszego klucza. Jesli
    #    podobienstwo >= PROG_FUZZY (literowka) - auto-poprawiamy. Ponizej progu
    #    (naprawde inna nazwa) - zostawiamy do recznej weryfikacji w kroku 3.
    #    Auto-poprawki raportujemy osobno, bo to ZGADYWANIE - czlowiek ma moc je
    #    skontrolowac.
    klucze = list(mapa.keys())
    fuzzy_poprawki, mapa_fuzzy = [], {}
    niedopasowane = sorted(znorm[docelowa.isna() & znorm.notna()].unique())
    for wartosc in niedopasowane:
        klucz, wynik, _ = process.extractOne(wartosc, klucze, scorer=fuzz.ratio)
        if wynik >= PROG_FUZZY:
            mapa_fuzzy[wartosc] = mapa[klucz]
            fuzzy_poprawki.append({"wartosc": wartosc, "poprawiono_na": mapa[klucz],
                                   "wynik": round(wynik, 1)})
    if mapa_fuzzy:
        docelowa = docelowa.fillna(znorm.map(mapa_fuzzy))
    raport[f"{nazwa_w_raporcie}_fuzzy"] = fuzzy_poprawki

    # 3. NIEROZPOZNANE: wciaz niedopasowane (ani mapa, ani fuzzy) - do reki.
    maska_nierozp = docelowa.isna() & znorm.notna()
    nierozpoznane = []
    for wartosc in sorted(znorm[maska_nierozp].unique()):
        wiersze = df[maska_nierozp & (znorm == wartosc)]
        for plik, grupa in wiersze.groupby("plik_zrodlowy"):
            nierozpoznane.append({
                "wartosc": wartosc,
                "plik": plik,
                "wiersze": grupa.index.tolist(),
                "liczba": len(grupa),
            })
    raport[f"{nazwa_w_raporcie}_nierozpoznane"] = nierozpoznane

    # 4. Finalna kolumna: docelowa (mapa + fuzzy), a co zostalo -> ORYGINAL.
    df[kolumna] = docelowa.fillna(df[kolumna])
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
    # Gdy zapisana wartosc nie zgadza sie z iloczynem ilosc * cena, ufamy
    # ilosci i cenie (dane pierwotne) i przeliczamy wartosc od nowa -
    # traktujemy ja jako blednie policzona, nie ilosc/cene.
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

def wyczysc_dane(zrodlo="dane_surowe"):
    """Uruchamia caly pipeline czyszczenia i zwraca (df, raport).

    zrodlo moze byc:
      - sciezka do folderu (str) -> wczytuje wszystkie CSV z folderu (lokalnie),
      - lista wgranych plikow    -> wczytuje je (Streamlit file_uploader).
    """
    if isinstance(zrodlo, str):
        df = wczytaj_dane(zrodlo)        # str = sciezka do folderu
    else:
        df = wczytaj_pliki(zrodlo)       # inaczej = lista wgranych plikow
    raport = {}
    df = czysc_daty(df, raport)
    df = czysc_liczby(df, raport)                                          
    df = oznacz_duplikaty(df, raport)                                      
    df = standaryzuj_tekst(df, raport, "region", MAPA_REGIONOW, "region")  
    df = standaryzuj_tekst(df, raport, "produkt", MAPA_PRODUKTOW, "produkt")
    df = czysc_sprzedawcow(df, raport)                                     
    df = przelicz_wartosc(df, raport)                                      
    return df, raport                                                     


if __name__ == "__main__":
    # Ten blok sluzy tylko do testowego uruchomienia z terminala.
    # Docelowo pipeline wola Streamlit przez funkcje wyczysc_dane().
    df, raport = wyczysc_dane()
    print(f"Wyczyszczono {len(df)} wierszy")
    print(f"Daty: przeksztalcono {raport['daty_przeksztalcone']}, niesparsowano {raport['daty_niesparsowane']}")
    print(f"Ceny z przecinkiem: {raport['cena_przecinek']}, puste: {raport['cena_pusta']}")
    print(f"Ujemne ilosci: {raport['ilosc_ujemna']}, duplikaty: {raport['duplikaty_do_weryfikacji']}")
    print(f"Sprzedawcy uzupelnieni: {raport['sprzedawca_brak']}, wartosci przeliczone: {raport['wartosc_niezgodna']}")
    nierozp = raport["region_nierozpoznane"] + raport["produkt_nierozpoznane"]
    print(f"Do recznej poprawy: {len(nierozp)} wartosci")
    fuzzy = raport["region_fuzzy"] + raport["produkt_fuzzy"]
    print(f"Auto-poprawki fuzzy: {len(fuzzy)} wartosci")