import csv, random, os
random.seed(42)

regiony_clean = ["Wielkopolska", "Mazowieckie", "Malopolska", "Dolnoslaskie", "Pomorskie"]
regiony_dirty = {
    "Wielkopolska": ["Wielkopolska", "wielkopolskie", "Wlkp", "Wielkopolskie "],
    "Mazowieckie": ["Mazowieckie", "mazowieckie", "Mazowsze", " Mazowieckie"],
    "Malopolska": ["Malopolska", "malopolskie", "Malopolskie", "MALOPOLSKA"],
    "Dolnoslaskie": ["Dolnoslaskie", "dolnoslaskie", "Dolny Slask", "Dolnoslaskie "],
    "Pomorskie": ["Pomorskie", "pomorskie", "Pomorze", "POMORSKIE"],
}
# --- FMCG: napoje i przekaski ---
produkty = {
    "Woda gazowana 1.5L": 2.49,
    "Piwo jasne 0.5L": 4.29,
    "Chipsy paprykowe 150g": 6.99,
    "Sok pomaranczowy 1L": 5.49,
    "Baton czekoladowy 50g": 2.99,
}
produkty_dirty = {
    "Woda gazowana 1.5L": ["Woda gazowana 1.5L", "woda gazowana 1.5l", "Woda  gazowana 1.5L", "Woda gaz. 1.5L"],
    "Piwo jasne 0.5L": ["Piwo jasne 0.5L", "piwo jasne 0.5l", "Piwo  jasne 0.5L"],
    "Chipsy paprykowe 150g": ["Chipsy paprykowe 150g", "chipsy paprykowe 150g", "Chipsy paprykowe  150g", "Chipsy papryk. 150g"],
    "Sok pomaranczowy 1L": ["Sok pomaranczowy 1L", "sok pomaranczowy 1l", "Sok pomaranczowy 1 L"],
    "Baton czekoladowy 50g": ["Baton czekoladowy 50g", "baton czekoladowy 50g", "Baton czekol. 50g"],
}
sprzedawcy = ["Nowak", "Kowalski", "Wisniewski", "Wojcik", "Lewandowska"]

def date_fmt(y, m, d, style):
    if style == 0: return f"{y}-{m:02d}-{d:02d}"
    if style == 1: return f"{d:02d}.{m:02d}.{y}"
    if style == 2: return f"{d:02d}/{m:02d}/{y}"

error_log = {"duplikaty":0,"ujemna_ilosc":0,"cena_tekst_przecinek":0,
             "pusty_sprzedawca":0,"pusta_cena":0,"literowka_region":0,
             "literowka_produkt":0,"wartosc_niezgodna":0,"spacje":0}

def make_row(y, m, style):
    prod_clean = random.choice(list(produkty.keys()))
    cena = produkty[prod_clean]
    ilosc = random.randint(6, 120)            # FMCG -> wieksze ilosci (palety/kartony)
    d = random.randint(1, 28)
    data = date_fmt(y, m, d, style)
    region = random.choice(regiony_clean)
    produkt = prod_clean
    sprzedawca = random.choice(sprzedawcy)
    cena_str = f"{cena:.2f}"
    wartosc = round(cena * ilosc, 2)

    if random.random() < 0.18:
        region = random.choice(regiony_dirty[region]); error_log["literowka_region"] += 1
    if random.random() < 0.15:
        produkt = random.choice(produkty_dirty[prod_clean])
        if produkt != prod_clean: error_log["literowka_produkt"] += 1
    if random.random() < 0.08:
        ilosc = -ilosc; error_log["ujemna_ilosc"] += 1
    if random.random() < 0.12:
        cena_str = f"{cena:.2f}".replace(".", ","); error_log["cena_tekst_przecinek"] += 1
    if random.random() < 0.06:
        sprzedawca = ""; error_log["pusty_sprzedawca"] += 1
    if random.random() < 0.05:
        cena_str = ""; error_log["pusta_cena"] += 1
    if random.random() < 0.07:
        wartosc = round(wartosc * random.uniform(1.05, 1.4), 2); error_log["wartosc_niezgodna"] += 1
    if random.random() < 0.06:
        sprzedawca = f"  {sprzedawca} "; error_log["spacje"] += 1
    return [data, region, sprzedawca, produkt, ilosc, cena_str, wartosc]

header = ["data_sprzedazy","region","sprzedawca","produkt","ilosc","cena_jednostkowa","wartosc"]
files = [("2025_01", 2025, 1, 0), ("2025_02", 2025, 2, 1), ("2025_03", 2025, 3, 2)]

os.makedirs("dane_surowe", exist_ok=True)
# usun stare jubilerskie pliki jesli zostaly
for f in os.listdir("dane_surowe"):
    os.remove(os.path.join("dane_surowe", f))

total = 0
for name, y, m, style in files:
    rows = [make_row(y, m, style) for _ in range(120)]
    for _ in range(random.randint(4, 7)):
        rows.append(random.choice(rows)[:]); error_log["duplikaty"] += 1
    random.shuffle(rows)
    with open(f"dane_surowe/sprzedaz_{name}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)
    total += len(rows)

print(f"Utworzono 3 pliki CSV (FMCG), lacznie {total} wierszy\n")
print("KLUCZ ODPOWIEDZI (ile bledow wpletlem):")
for k, v in error_log.items():
    print(f"  {k:24s}: {v}")
print(f"\n  SUMA bledow do naprawienia: {sum(error_log.values())}")
