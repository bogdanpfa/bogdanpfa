# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/ro/1.1.0/).

## [2.1.0] - 2026-10-09
### Modificat
- Șablonul `sabloane/CSS_model.docx` are acum câmpuri marcate `{{nume}}`; generatorul le înlocuiește direct, fără să depindă de structura internă a documentului. Șablonul se poate rearanja liber în Word (vezi README). Modelul original e păstrat în `sabloane/originale/`.
- Tot textul din formular e negru (înainte, etichetele erau roșii).
- Fără dublă subliniere: o valoare completată e subliniată o singură dată; câmpurile goale rămân linii „____”.
- „Departament / Direcție / divizie” nu se mai completează. „Locația” = penultimul segment din `loc_munca`.
- Tel. IP scos din formular; Tel. fix adăugat (manual). Mobil și Tel. IP rămân necompletate în PDF.
- „Adăugare” și „Ștergere” se exclud reciproc, în pagină și pe server.
- Erorile de generare (LibreOffice lipsă, câmp necunoscut în șablon, timeout) apar ca mesaj în pagină.

## [2.0.0] - 2026-10-08
### Modificat
- Generatorul PDF folosește acum șablonul `sabloane/CSS_model.docx`, completat și convertit cu LibreOffice, în loc de text suprapus peste un PDF. Rezultatul păstrează aspectul modelului (antet, subsol, note, semnătură).
- Căsuțele se pot bifa/debifa liber; preselecția din model (Adăugare, RENTRAD, Internet, E-Mail) devine valoare implicită în formular.
- „Locația” și „Departament” se completează din calea `loc_munca` a persoanei (penultimul, respectiv ultimul segment), editabile.
- Câmpurile Mobil și Tel. fix au fost scoase; rămân necompletate în PDF. Telefonul obligatoriu: Tel. CFR, Tel. IP sau Fax CFR.
- „* Câmp obligatoriu” (notă de final în model) este afișat ca paragraf în corp, pentru ca documentul să rămână pe o pagină.

### Eliminat
- `generators/pdf_generator.py` și dependențele `reportlab`, `pypdf`.

## [1.0.0]
- Versiunea inițială (PDF prin suprapunere).
