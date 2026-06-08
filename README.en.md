# FMCG – sales report automation

*[Wersja polska](README.md)* 

🔗 **Live demo:** https://fmcg-raport-automat-vgeevdu7bdryikyfrmdccx.streamlit.app/

A tool that takes raw, messy sales files (the kind that actually land on a
reporting analyst's desk), **detects and fixes data errors**, and then generates
a clean, formatted Excel report - no manual grind. Available as a web app
(upload files → download report) and from the command line.

Goal: show that a typical monthly reporting-analyst chore (hours of cleaning data
in Excel) can be reduced to a single click, **with a measurable data-quality
report** up front.

## Problem

Sales data rarely arrives clean. Here we have monthly CSV files, each exported in
a different format, with typical errors:

| Error category | Example |
|---|---|
| Mixed date formats | `2025-01-21`, `21.02.2025`, `15/03/2025` |
| Numbers as text with a comma | `"4,29"` instead of `4.29` |
| Negative quantities | `-112` units |
| Empty fields | missing salesperson, missing price |
| Typos / inconsistent region names | `Wielkopolska`, `wielkopolskie`, `Wlkp` |
| Typos / inconsistent product names | `Chipsy paprykowe 150g` vs `chipsy papryk. 150g` |
| Duplicate rows | the same row copied |
| Inconsistent value | `value ≠ quantity × price` |
| Extra whitespace | `"  Nowak "` |

The data is **synthetic and generated**: `generuj_dane.py` produces the demo set
with a controlled number of errors across 9 categories, and `generuj_dane_test.py`
produces a test set with edge cases for the fuzzy layer. Each script reports the
exact fix counts on **every run**, so the result is measurable and verifiable on
concrete data rather than merely claimed.

## How it works

1. **Loading and consolidation** - all uploaded CSV files are validated
   (column check) and merged into a single table.
2. **Cleaning** - dates (3 formats → one `datetime` type), numbers (price,
   quantity), region and product standardization, filling in salespeople,
   recalculating values.
3. **Fuzzy matching** - typos in region/product names (e.g. `mazowiekcie`) are
   auto-corrected based on similarity to a known list (rapidfuzz, threshold tuned
   on the data). Auto-corrections are reported **separately for audit** - it's a
   guess, so a human can verify or revert it. Values below the threshold (genuinely
   new names) go to manual review.
4. **Duplicate flagging** - potential duplicates are flagged for review, **not**
   removed (see: Assumptions and limitations).
5. **Quality report** - what was fixed and how much, broken down by category, plus
   a list of unrecognized values with their source file and a fix instruction.
6. **Excel export** - a formatted workbook with five sheets: clean data, sales
   summary, quality report, list to fix manually, and fuzzy auto-corrections to
   review.

## Running it

### Web app (locally)

```bash
python3 -m venv venv
source venv/bin/activate        # macOS / Linux
pip install -r requirements.txt
streamlit run app.py
```

The app opens in the browser: upload CSV files, see the quality report, download
the finished Excel report.

### From the command line (on data in the `dane_surowe/` folder)

```bash
python czyszczenie.py        # prints a summary of fixes
python eksport_excel.py      # generates raporty/raport_sprzedaz.xlsx
python generuj_dane.py       # (optional) a fresh demo data set
python generuj_dane_test.py  # (optional) a set with typos - fuzzy demo
```

## Structure
```bash
fmcg-raport-automat/
├── dane_surowe/          # demo (clean) data set - messy CSV files
├── dane_test/            # set with typos and unknown values (fuzzy demo)
├── generuj_dane.py       # demo set generator (with controlled errors)
├── generuj_dane_test.py  # test set generator (fuzzy edge cases)
├── czyszczenie.py        # cleaning engine (wyczysc_dane function)
├── eksport_excel.py      # Excel export (to disk and to memory/BytesIO)
├── app.py                # web interface (Streamlit)
├── requirements.txt
└── README.md
```
The cleaning logic (`czyszczenie.py`) is independent of the output format
(`eksport_excel.py`) and of the interface (`app.py`). Each module exposes
functions, so it can be called from the web app, a script, or a scheduler.

## Stack

Python (pandas, openpyxl, rapidfuzz), Streamlit. No database - deliberately
lightweight.

## Assumptions and limitations

The tool makes a few deliberate business assumptions. In a real deployment these
would be agreed with the team that knows the data source:

- **Date format:** a European day-first notation is assumed (`DD.MM.YYYY`,
  `DD/MM/YYYY`), because the data comes from a Polish company. A single ambiguous
  date (e.g. `03-04-2023`) cannot be resolved between the European and American
  formats. For data from mixed US/EU sources you would detect the format per file
  or enforce ISO (`YYYY-MM-DD`) on input.
- **Negative quantities** are treated as a sign typo (absolute value is taken).
  An alternative interpretation - returns - would require counting them separately.
- **An inconsistent transaction value** is recalculated as `quantity × price`,
  i.e. quantity and price are treated as the source of truth (primary data).
- **Duplicates are not removed**, only flagged for review - without a timestamp or
  transaction ID you cannot tell a technical duplicate from two genuinely identical
  transactions on the same day.
- **Empty salesperson fields** are filled with `Nieznany` ("Unknown") - we don't
  guess the name - and the transaction stays in the data, because the sale itself
  is real.

## Status / roadmap

- [x] Loading and consolidation of multiple files (with column validation)
- [x] Date normalization (3 formats → one `datetime` type)
- [x] Number cleaning (price, quantity)
- [x] Region and product standardization (with a report of unrecognized values)
- [x] Duplicate flagging for review
- [x] Filling in salespeople and recalculating values
- [x] Data-quality report
- [x] Export to a formatted Excel file
- [x] Fuzzy matching of typos against a known list (rapidfuzz) with an auto-correction report
- [x] Web interface (Streamlit) + cloud deployment