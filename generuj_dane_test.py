"""
Generator zestawu TESTOWEGO (dane_test/) z przypadkami brzegowymi.

W odroznieniu od generuj_dane.py zawiera literowke, ktora warstwa fuzzy
auto-poprawi, oraz nieznane wartosci (nowy region, nowy produkt), ktore
narzedzie zostawi do recznej weryfikacji. Sluzy do demonstracji fuzzy.
"""
import csv
import random
import os

random.seed(2024)  # inny seed niz generuj_dane.py 

REGIONY = ["Wielkopolska", "Mazowieckie", "Malopolska", "Dolnoslaskie", "Pomorskie"]
REGIONY_DIRTY = {
    "Wielkopolska": ["Wielkopolska", "wielkopolskie", "Wlkp"],
    "Mazowieckie": ["Mazowieckie", "mazowieckie", "Mazowsze"],
    "Malopolska": ["Malopolska", "malopolskie", "MALOPOLSKA"],
    "Dolnoslaskie": ["Dolnoslaskie", "dolnoslaskie", "Dolny Slask"],
    "Pomorskie": ["Pomorskie", "pomorskie", "Pomorze"],
}
PRODUKTY = {
    "Woda gazowana 1.5L": 2.49, "Piwo jasne 0.5L": 4.29, "Chipsy paprykowe 150g": 6.99,
    "Sok pomaranczowy 1L": 5.49, "Baton czekoladowy 50g": 2.99,
}
SPRZEDAWCY = ["Nowak", "Kowalski", "Wisniewski", "Wojcik", "Lewandowska"]
NAGLOWEK = ["data_sprzedazy", "region", "sprzedawca", "produkt",
            "ilosc", "cena_jednostkowa", "wartosc"]


def format_daty(y, m, d, styl):
    return [f"{y}-{m:02d}-{d:02d}", f"{d:02d}.{m:02d}.{y}", f"{d:02d}/{m:02d}/{y}"][styl]


def zrob_wiersz(y, m, styl):
    produkt = random.choice(list(PRODUKTY))
    cena = PRODUKTY[produkt]
    ilosc = random.randint(6, 120)
    data = format_daty(y, m, random.randint(1, 28), styl)
    region = random.choice(REGIONY)
    sprzedawca = random.choice(SPRZEDAWCY)
    cena_str = f"{cena:.2f}"
    wartosc = round(cena * ilosc, 2)
    # te same typowe bledy co w danych demo, zeby zestaw byl realistyczny
    if random.random() < 0.18:
        region = random.choice(REGIONY_DIRTY[region])
    if random.random() < 0.12:
        cena_str = cena_str.replace(".", ",")
    if random.random() < 0.08:
        ilosc = -ilosc
    if random.random() < 0.06:
        sprzedawca = ""
    return [data, region, sprzedawca, produkt, ilosc, cena_str, wartosc]


# SEDNO tego zestawu - przypadki brzegowe dla warstwy fuzzy:
PRZYPADKI_BRZEGOWE = [
    # literowka regionu -> fuzzy AUTO-poprawi na "Mazowieckie" (podobienstwo > prog)
    ["2025-07-15", "Mazowiekcie", "Nowak", "Piwo jasne 0.5L", 8, "4.29", 34.32],
    # region SPOZA listy -> fuzzy ZOSTAWI do recznej weryfikacji (ponizej progu)
    ["2025-07-16", "Slaskie", "Nowak", "Piwo jasne 0.5L", 8, "4.29", 34.32],
    # NOWY produkt spoza listy -> do recznej weryfikacji
    ["2025-07-17", "Pomorskie", "Nowak", "Napoj energetyczny 250ml", 8, "5.99", 47.92],
]

PLIKI = [("2025_04", 2025, 4, 0, 90), ("2025_05", 2025, 5, 1, 150),
         ("2025_06", 2025, 6, 2, 75), ("2025_07", 2025, 7, 0, 110)]

os.makedirs("dane_test", exist_ok=True)
for plik in os.listdir("dane_test"):
    os.remove(os.path.join("dane_test", plik))

for nazwa, y, m, styl, n in PLIKI:
    wiersze = [zrob_wiersz(y, m, styl) for _ in range(n)]
    for _ in range(random.randint(3, 6)):          # kilka duplikatow do oflagowania
        wiersze.append(random.choice(wiersze)[:])
    with open(f"dane_test/sprzedaz_{nazwa}.csv", "w", newline="", encoding="utf-8") as fh:
        pisarz = csv.writer(fh)
        pisarz.writerow(NAGLOWEK)
        pisarz.writerows(wiersze)

# przypadki brzegowe dopisujemy na koncu ostatniego pliku
with open("dane_test/sprzedaz_2025_07.csv", "a", newline="", encoding="utf-8") as fh:
    csv.writer(fh).writerows(PRZYPADKI_BRZEGOWE)

print("Wygenerowano dane_test/ (4 pliki). Przypadki brzegowe dla fuzzy:")
print("  Mazowiekcie              -> literowka, fuzzy auto-poprawi na Mazowieckie")
print("  Slaskie                  -> region spoza listy, do recznej weryfikacji")
print("  Napoj energetyczny 250ml -> nowy produkt, do recznej weryfikacji")