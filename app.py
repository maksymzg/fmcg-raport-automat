import streamlit as st
import pandas as pd
from czyszczenie import wyczysc_dane
from eksport_excel import eksportuj_do_bajtow

# --- Konfiguracja strony ---
st.set_page_config(page_title="Czyszczenie raportu sprzedazy", page_icon="🧹", layout="wide")
st.title("🧹 Automatyzacja raportu sprzedazy FMCG")
st.write(
    "Wgraj surowe pliki CSV ze sprzedaza. Narzedzie wykryje i naprawi typowe bledy "
    "(daty, liczby, literowki, duplikaty), pokaze raport jakosci i wygeneruje gotowy raport Excel."
)

# --- Wgrywanie plikow ---
pliki = st.file_uploader(
    "Wgraj pliki CSV (mozesz kilka naraz)",
    type="csv",
    accept_multiple_files=True,
)

# Jesli nic nie wgrano - zatrzymujemy sie tutaj (reszta sie nie wykona).
if not pliki:
    st.info("Czekam na pliki CSV.")
    st.stop()

# --- Czyszczenie (z obsluga bledu walidacji kolumn) ---
try:
    df, raport = wyczysc_dane(pliki)
except ValueError as e:
    st.error(f"Problem z plikiem:\n\n{e}")
    st.stop()

st.success(f"Gotowe! Przetworzono {len(df)} wierszy z {len(pliki)} plikow.")

# --- Raport jakosci: kafelki z liczbami ---
st.subheader("Raport jakosci danych")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Ceny naprawione", raport["cena_przecinek"])
k2.metric("Ujemne ilosci", raport["ilosc_ujemna"])
k3.metric("Sprzedawcy uzupelnieni", raport["sprzedawca_brak"])
k4.metric("Wartosci przeliczone", raport["wartosc_niezgodna"])

k5, k6, k7, k8 = st.columns(4)
k5.metric("Daty znormalizowane", raport["daty_przeksztalcone"])
k6.metric("Daty niesparsowane", raport["daty_niesparsowane"])
k7.metric("Ceny puste", raport["cena_pusta"])
k8.metric("Duplikaty do weryfikacji", raport["duplikaty_do_weryfikacji"])

# --- Nierozpoznane wartosci do recznej poprawy ---
nierozp = raport["region_nierozpoznane"] + raport["produkt_nierozpoznane"]
if nierozp:
    st.warning(f"Znaleziono {len(nierozp)} nierozpoznanych wartosci do recznej poprawy:")
    for r in nierozp:
        st.write(f"- **{r['wartosc']}** ({r['liczba']}x) w pliku `{r['plik']}` "
                 f"- otworz plik, znajdz wartosc (Ctrl+F) i popraw.")
else:
    st.info("Wszystkie wartosci rozpoznane - nic do recznej poprawy.")
# --- Auto-poprawki fuzzy (do sprawdzenia) ---
fuzzy = raport["region_fuzzy"] + raport["produkt_fuzzy"]
if fuzzy:
    st.subheader("Auto-poprawione literowki (do sprawdzenia)")
    st.caption("Narzedzie samo poprawilo te wartosci na podstawie podobienstwa. "
               "To zgadywanie - zweryfikuj, czy dopasowanie jest trafne.")
    st.dataframe(
        pd.DataFrame([{
            "Bylo": f["wartosc"],
            "Poprawiono na": f["poprawiono_na"],
            "Podobienstwo": f["wynik"],
        } for f in fuzzy]),
        use_container_width=True,
    )
# --- Podglad wyczyszczonych danych ---
st.subheader("Podglad wyczyszczonych danych")
st.dataframe(df.head(50), use_container_width=True)

# --- Pobranie raportu Excel ---
st.subheader("Pobierz raport")
bajty = eksportuj_do_bajtow(df, raport)
st.download_button(
    label="📥 Pobierz raport Excel",
    data=bajty,
    file_name="raport_sprzedaz.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)