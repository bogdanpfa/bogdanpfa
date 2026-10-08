# Comandă servicii suplimentare - V1

Aplicație Flask locală pentru completarea și exportul PDF al formularului SRTFC Iași.

## Pornire locală

1. Deschideți PowerShell în `C:\DevTools\CSS`.
2. Creați mediul virtual: `py -m venv .venv`
3. Activați-l: `.\.venv\Scripts\Activate.ps1`
4. Instalați dependențele: `pip install -r requirements.txt`
5. Verificați `.env` - în special `PERSOANE_DB_PATH`.
6. Porniți aplicația: `python app.py`
7. Deschideți `http://127.0.0.1:5006`.

## Configurare

Beneficiarul, compania, prefixul numărului și calea bazei se configurează în `.env`. Exemplul sigur pentru distribuire este `.env.example`.

## Siguranța bazei de persoane

`persoane_repo.py` deschide baza SQLite numai cu `mode=ro`. Căutarea aplicației transmite obligatoriu filtrul `srtfc='IS'`; detaliile unei persoane sunt validate din nou înainte de afișare.

## Reguli de generare

PDF-ul se poate genera numai după activarea comutatorului pentru număr și completarea numărului de înregistrare. Este obligatoriu minimum un număr de telefon.
