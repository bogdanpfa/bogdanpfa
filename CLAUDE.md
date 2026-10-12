# Comandă servicii suplimentare (CSS) — v2

Aplicație internă Flask: completează formularul SRTFC Iași „Comandă de servicii suplimentare” și îl exportă în PDF. Serviciul OTD - IT, CFR Călători Iași.

## Rulare
- **Port: 5006**. Acum `app.py` pornește cu `host="127.0.0.1"` și `debug=True` (doar dezvoltare locală, `start_css.bat`).
- Server (172.26.65.126): `waitress` prin `C:\DevTools\_server\servere.ps1 Start CSS` (ignoră blocul `__main__`, deci fără debug).
- Pe server sunt necesare **LibreOffice** (`soffice --headless`, pentru PDF) și fontul **Cambria**.
- Dependențe: `requirements.txt` (Flask, lxml, Pillow, python-dotenv). Config în `.env` (vezi `.env.example`), `config.py` (`VERSION`).

## Structură
- `app.py`, `config.py`. `generators/docx_generator.py` — completează `sabloane/CSS_model.docx` (câmpuri `{{nume}}`) și îl convertește în PDF.
- `persoane_repo.py` — citește baza comună `C:\DevTools\_comun\persoane.db` **doar cu `mode=ro`**, cu filtrul obligatoriu `srtfc='IS'`.
- `templates/`, `static/`, `sabloane/` (șabloane `.docx`; originalul în `sabloane/originale/`), `exemplu/` (date inventate).

## Reguli
- **Nu scrie niciodată** în `persoane.db` (o administrează doar Agenda, port 5005). Citește `_comun\CITESTE-MA.txt`.
- PDF-ul se generează numai după activarea comutatorului de număr și completarea numărului de înregistrare; minim un număr de telefon (vezi README).
- Dacă modifici șablonul `.docx`, păstrează marcajele `{{...}}` și verifică PDF-ul rezultat vizual.
- `output/` conține PDF-uri cu date reale — nu intră pe GitHub. `CHANGELOG.md` + `VERSION` la fiecare modificare. Interfață în română.
