# Comandă servicii suplimentare - V2

Aplicație Flask locală pentru completarea și exportul PDF al formularului SRTFC Iași.

## Pornire locală

1. Deschideți PowerShell în `C:\DevTools\CSS`.
2. Creați mediul virtual: `py -m venv .venv`
3. Activați-l: `.\.venv\Scripts\Activate.ps1`
4. Instalați dependențele: `pip install -r requirements.txt`
5. Instalați LibreOffice (necesar pentru PDF) și verificați că fontul Cambria există pe mașină.
6. Verificați `.env` - în special `PERSOANE_DB_PATH`.
7. Porniți aplicația: `python app.py`
8. Deschideți `http://127.0.0.1:5006`.

## Configurare

Beneficiarul, compania, prefixul numărului și calea bazei se configurează în `.env`. Exemplul sigur pentru distribuire este `.env.example`.

## Siguranța bazei de persoane

`persoane_repo.py` deschide baza SQLite numai cu `mode=ro`. Căutarea aplicației transmite obligatoriu filtrul `srtfc='IS'`; detaliile unei persoane sunt validate din nou înainte de afișare.

## Reguli de generare

PDF-ul se poate genera numai după activarea comutatorului pentru număr și completarea numărului de înregistrare. Este obligatoriu minimum un număr de telefon.

## Generarea PDF

`generators/docx_generator.py` completează `sabloane/CSS_model.docx` și îl convertește în PDF cu LibreOffice (`soffice --headless`).

### Modificarea aspectului în Word

Deschideți `sabloane/CSS_model.docx` în Word și modificați liber fonturi, spațiere, subliniere, tabele. Singura regulă: câmpurile `{{...}}` trebuie să rămână în text, scrise exact. Formatul câmpului (font, mărime, subliniere, culoare) se aplică valorii completate.

- `{{nume:98}}` — dacă valoarea lipsește, se pune o linie `____` de 98 pt; dacă există, se afișează subliniată.
- `{{companie:134:284}}` — a doua cifră e lățimea maximă: peste ea fontul se micșorează (minim 8 pt), apoi textul se taie.
- Căsuțele `{{op_nou}}`, `{{srv_internet}}` etc. devin `X` (bifat) sau `☐`.
- După modificare, salvați ca `.docx` (nu .doc) în același loc. Dacă greșiți un nume de câmp, aplicația afișează „Câmpuri necunoscute în șablon: {{...}}”.

### Câmpurile disponibile

| Tip | Câmpuri |
|---|---|
| Text | `nr_prefix`, `numar`, `data`, `nume`, `initiala`, `prenume`, `companie`, `functie`, `locatia`, `sef_direct`, `cladire`, `etaj`, `camera`, `tel_cfr`, `tel_fix`, `fax_cfr`, `alte_detalii`, `aspr_detalii`, `suport_detalii`, `alte_servicii_1`, `alte_servicii_2`, `ben_nume`, `ben_functie`, `data_ben` |
| Operațiune | `op_nou`, `op_transferat`, `op_modificari`, `op_stergere_utilizator` |
| Tip locație | `loc_central`, `loc_regional`, `loc_unitate` |
| Servicii | `srv_adaugare`, `srv_stergere`, `srv_aspr`, `srv_rentrad`, `srv_internet`, `srv_email`, `srv_legis`, `srv_suport`, `srv_alte` |

`alte_servicii_1` și `alte_servicii_2` sunt cele două rânduri pe care curge câmpul „Alte servicii”.
Liniile fără câmp (Departament, Mobil, Tel. IP, Unitate) rămân goale, ca în model.

`python scripts/build_template.py` reface șablonul din modelul original (se folosește doar dacă se pornește din nou de la original; suprascrie modificările făcute în Word).
