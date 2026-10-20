# Changelog și jurnal de depanar e — Audit Rețea SRTFC Iași

Aici ținem evidența a tot ce se schimbă la aplicație, în două părți:

1. **Versiuni**: ce s-a modificat în cod, pe versiuni (format [Keep a Changelog](https://keepachangelog.com/ro/1.1.0/)).
   Versiunea curentă se schimbă **doar** în `config.py` și apare în subsolul aplicației.
2. **Jurnal de depanare și intervenții**: probleme apărute, cauza lor și cum le-am rezolvat, plus intervențiile pe server
   care nu schimbă codul (setări, conturi, firewall, restaurări).

Aplicația există în **două copii**, ambele în `C:\DevTools\AuditRetea`:

| Copie | Rol | Baza de date |
|---|---|---|
| 💻 **Local** (PC-ul de lucru) | dezvoltare și teste | `instance\audit.db` locală, date de test |
| 🖥️ **Server** 172.26.65.126 | producție, port 5009 | `instance\audit.db` reală, nu se copiază niciodată peste |

Codul circulă **într-un singur sens**: Local → Server, cu `PUBLICA_PE_SERVER.bat` (GitHub păstrează istoricul).
Dacă se repară ceva direct pe server, intrarea din jurnal primește eticheta **⚠️ de adus în Local**
până când fișierul e copiat și pe PC. Altfel, la următoarea publicare reparația se pierde.
Fiecare publicare e notată automat și pe server, în `instance\logs\publicari.log`.

---

## Cum se scrie o intrare

**În partea 1, Versiuni** (la fiecare sesiune de lucru care schimbă codul):
1. Creșteți `VERSION` în `config.py`: `1.0.1` pentru reparații, `1.1.0` pentru funcții noi, `2.0.0` pentru schimbări mari.
2. Adăugați o secțiune nouă **deasupra** celorlalte, cu data și locul unde s-a lucrat.
3. Folosiți doar categoriile: Adăugat · Modificat · Reparat · Eliminat · Securitate.

```markdown
## [1.0.2] — 2026-11-05 · 💻 Local
### Reparat
- Ce s-a reparat, pe ënțelesul unui coleg (ex. „Exportul Excel nu mai pierde diacriticele din numele stațiilor“).
```

**În partea 2, Jurnal de depanare** (la orice problemă sau intervenție, chiar dacă nu s-a schimbat codul):

```markdown
### 2026-11-04 · 🖥️ Server · v1.0.1 · [REZOLVAT]
- **Simptom:** ce s-a văzut (mesaj de eroare, pagina, cine a observat).
- **Cauză:** de ce s-a întâmplat.
- **Rezolvare:** ce s-a făcut, pas cu pas, ca să poată fi repetat.
- **Prevenire:** ce schimbăm ca să nu se repete (sau „—“).
```

Stări posibile: **[REZOLVAT]** · **[În LUCRU]** · **[OCOLIT]** (merge, dar cauza a rămas) · **⚠️ de adus în Local**.

---

# Partea 1 — Versiuni

## [Nepublicat]
_(modificări făcute, dar încă neinstalate pe server)_

## [1.4.0] — 2026-10-20 · 💻 Local
### Modificat
- **Acces automat pentru orice cont AD valid**: orice utilizator de domeniu cu credențiale corecte intră direct,
  fără să fie adăugat manual de un administrator. La prima logare, contul e creat automat cu rolul „Administrator“.
- Dacă sunt configurate grupuri de acces în Setări, comportamentul rămâne același ca înainte (intră doar membrii grupului).

### Eliminat
- Formularul „Adaugă utilizator“ din pagina Utilizatori (înregistrarea manuală a conturilor AD nu mai e necesară).

## [1.3.0] — 2026-10-20 · 💻 Local
### Adăugat
- Buton **„Acasă“** în antet (inclusiv pe pagina de login): duce la portalul intern de pe același server
  (ex. `http://cl6srvappiasi/`); adresa se poate fixa cu variabila `AUDIT_PORTAL_URL`.

### Modificat
- Antetul are stilul aplicațiilor din portal (ca PDF Tools): iconiță + „Audit Rețea“ + „CFR Călători · Serviciul OTD & IT Iași“,
  butoane conturate în dreapta (Manual, Stare parc, Ieșire, Acasă); meniul e o bară separată sub antet.
- Pagina de login: card „Autentificare“ simplu, sub același antet.

## [1.2.1] — 2026-10-20 · 💻 Local
### Adăugat
- Integrare cu `C:\DevTools\MENIU.bat`: `1_DEPLOY_SERVER.bat` (deploy complet), `1_DEPLOY_RAPID.bat`
  (fără teste și confirmare; backup-ul bazei se face oricum) și `2_PUSH_GITHUB.bat` (commit + push cu control
  anti-date-sensibile; leagă de GitHub un folder instalat din ZIP).
- `PUBLICA_PE_SERVER.bat /rapid`; modul apare și în `instance\logs\publicari.log`.

## [1.2.0] — 2026-10-20 · 💻 Local
### Adăugat
- **Acces doar pentru administratorii AD** (Setări → Acces în aplicație): conturile de domeniu intră numai dacă sunt membre
  ale grupurilor alese (inclusiv prin grupuri imbricate); membrii intră direct și sunt creați automat în Utilizatori,
  cu rolul ales (Administrator / Doar vizualizare). Conturile locale rămân permise, ca rezervă.
- Grupurile sunt verificate în AD la salvare: un nume greșit nu poate refuza pe toată lumea.
- `manage.py verifica-ad` arată și apartenența la grupurile de acces.

### Securitate
- Încercările greșite pentru conturi încă necunoscute aplicației sunt limitate (2 / 15 minute), ca pagina de login
  să nu poată fi folosită pentru blocarea conturilor în domeniu.

## [1.1.2] — 2026-10-20 · 💻 Local
### Adăugat
- `python manage.py verifica-ad <utilizator>`: diagnostic pentru logarea cu cont de domeniu (server membru în domeniu,
  cont în lista aplicației, blocare, răspunsul exact al Windows).
- Mesaje clare pentru mai multe coduri de eroare Windows la logare (1327, 1385, 1789, 1792).

## [1.1.1] — 2026-10-19 · 💻 Local
### Adăugat
- Buton „▶ Scanea ză“ pe fiecare subnet salvat: deschide formularul de scanare cu intervalul deja ales.
- În pagina Subneturi apare data ultimei scanări a fiecărui interval, cu link către rezultate.
- La scanarea unui interval introdus manual: bifa „Salvează intervalul ca subnet“.

## [1.1.0] — 2026-10-19 · 💻 Local
### Adăugat
- **Stare parc**: totaluri pe sistem de operare, tip sistem, stocare, RAM, compatibilitate Windows 11 și 12 indicatori
  (Windows 10, Windows 7/8/XP, fără antivirus, antivirus neactualizat, disc defect, HDD, disc mic, C: plin, RAM mic,
  TPM lipsă, PC vechi, nu trece pe Windows 11), pe toată rețeaua și pe subneturi.
- **Filtre cu bife** comune (subneturi, sisteme de operare, tip sistem, stocare, indicatori cu „oricare/toate“, RAM min/max,
  căutare, coloane afișate) și **vederi salvate** per utilizator.
- **Necesar piese și consumabile**: module RAM (tip, format, capacitate, viteză), SSD (SATA/NVMe, capacitate), toner sub prag,
  PC-uri de înlocuit, module RAM recuperate; reguli configurabile; export Excel pe foi.
- **Ramura Imprimante**: model, serie, contor pagini, nivel consumabile, erori, filtru pe marcă; export Excel.
- Motor: tip sistem, data BIOS, TPM, antivirus și starea lui, RAM structurat (tip, viteză, format, module, sloturi, maxim),
  disc (model, capacitate, interfață), C: total; imprimante și echipamente de rețea prin SNMP v2c.
- Setări: SNMP (activ, community) și regulile implicite pentru necesar.

### Modificat
- Migrare automată a bazei de date (coloane noi adăugate, fără pierderi); scanările vechi apar cu „date incomplete“.

### Eliminat
- Numele utilizatorului de pe rapoartele tipărite și din Excel (rămâne doar „Raport generat de Audit Rețea SRTFC Iași“ și data).

## [1.0.4] — 2026-10-19 · 💻 Local
### Adăugat
- Documentele generate poartă numele documentului și mențiunea „Raport generat de Audit Rețea SRTFC Iași“, cu data și utilizatorul:
  - la tipărire: raport de scanare, inventar echipamente, comparare, istoric, jurnal, manual;
  - în Excel: rândurile de titlu deasupra tabelului, plus antet și subsol la tipărirea din Excel (cu „Pagina X din Y“).
- Buton „Tipărește“ pe paginile Echipamente și Comparare.

### Reparat
- La tipărire, tabelul de scanare ieșea din pagină: acum se tipărește pe A4 orizontal, cu font compact.
  Coloanele MAC și Ultima pornire se ascund pe hârtie, dar rămân în aplicație și în Excel.
- Textul mențiunii se schimbă dintr-un singur loc: `config.py` (`TEXT_GENERAT`).

### Neschimbat intenționat
- Exportul CSV rămâne fără rânduri suplimentare, ca să poată fi reimportat și deschis exact ca fișierele din v6.

## [1.0.3] — 2026-10-19 · 💻 Local
### Adăugat
- Mențiunea „Aplicație dezvoltată de Bogdan PĂVĂLUC“ în subsolul tuturor paginilor (inclusiv login) și în manual.
  Numele și serviciul se modifică dintr-un singur loc: `config.py` (`AUTOR`, `SERVICIU`).

## [1.0.2] — 2026-10-19 · 💻 Local
### Adăugat
- `PUBLICA_PE_SERVER.bat`: publicare de pe PC-ul local, într-un pas: teste, oprire aplicație, backup la baza de pe server,
  copiere cu robocopy (fără `instance\`), pornire, verificare că rulează versiunea nouă, notare în `publicari.log`.
- La pornire, `serve.py` instalează singur dependențele dacă `requirements.txt` s-a schimbat.

### Eliminat
- `scripts\actualizeaza.ps1` (actualizare prin git pe server), înlocuit de `PUBLICA_PE_SERVER.bat`. Serverul nu mai are nevoie de Git.

## [1.0.1] — 2026-10-19 · 💻 Local
### Adăugat
- Jurnal de depanare și intervenții în acest fișier, cu șablon de completare și evidența locului (Local / Server).
- `scripts\actualizeaza.ps1`: actualizarea serverului din GitHub (eliminat în 1.0.2).

### Modificat
- Folderul implicit al aplicației este acum `C:\DevTools\AuditRetea`, atât local, cât și pe server.

## [1.0.0] — 2026-10-19 · 💻 Local
### Adăugat
- Aplicație web Flask + SQLite care rulează motorul `Audit_Retea_v6.ps1` fără interfață grafică (`engine/audit_engine.ps1`).
- Scanare la cerere cu progres live, oprire grațioasă și coadă (o singură scanare activă).
- Scanări programate săptămânal/lunar; contul de scanare e salvat cifrat cu DPAPI (domeniul mașinii).
- Utilizatori cu roluri (super-admin, administrator, vizualizare); autentificare de domeniu prin LogonUser sau cont local.
- Protecții de cont: verificare unică a parolei înainte de scanare, oprire la respingere de către domeniu,
  blocare în aplicație după 2 încercări AD greșite / 5 locale, CSRF pe toate formularele.
- Alerte: disc defect / avertizări SMART, spațiu redus pe C:, HDD, Windows 10 / 7 / 8, RAM sub 8 GB.
- Export Excel și CSV compatibil v6; import CSV v6; comparare între scanări; echipamente cunoscute și „fantomă“.
- Jurnal de acțiuni, retenție configurabilă, manual printabil, backup zilnic programat (ultimele 30 de copii).

### Modificat față de v6 (motor)
- Parola se primește pe STDIN, nu prin linia de comandă; ieșirea e JSON pe linie, UTF-8.
- Starea ONLINE se acordă la deschiderea sesiunii CIM (în v6, o stație fără `Win32_OperatingSystem` rămânea OFFLINE).
- Clasificare nouă a erorilor: Acces Refuzat / Timeout WMI / Non-Windows; detectare imprimante prin portul 9100 și DNS.
- Câmpuri completate acum: RAM Detalii, Producător, MAC, licență Windows (opțional); serie din BIOS când lipsește din carcasă.
- Discul de sistem (index 0) e cel analizat; cascada SSD/HDD rulează și când MSFT_PhysicalDisk răspunde „nespecificat“.

### Eliminat
- Prototipul anterior din AI Studio (React/Node), care genera date de inventar simulate. Rămâne accesibil pe branch-ul `arhiva-ai-studio`.

---

# Partea 2 — Jurnal de depanare și intervenții

_(cele mai noi sus)_

### 2026-10-20 · 🖥️ Server · v1.1.1 · [REZOLVAT]
- **Simptom:** la prima instalare, logarea cu contul local de rezervă merge, dar contul de administrator de domeniu e refuzat.
- **Cauză probabilă:** în aplicație intră doar conturile adăugate în pagina Utilizatori (listă albă). Superadmin-ul a fost
  creat pentru `bogdan.pavaluc`, iar contul de administrator AD are alt nume. Alte cauze posibile: serverul nu e membru
  în domeniu sau contul e blocat temporar în aplicație după 2 încercări.
- **Rezolvare:** adăugarea contului de administrator în Utilizatori (tip „Cont de domeniu“); diagnostic cu
  `manage.py verifica-ad <cont>` (adăugat în v1.1.2).
- **Rezultat:** după adăugarea contului de administrator, logarea cu contul AD funcționează.
- **Prevenire:** manualul explică diferența dintre contul de intrare în aplicație și contul folosit la scanare;
  din v1.2.0, administratorii AD pot intra automat, pe baza grupului.

### 2026-10-19 · 💻 Local · v1.0.0 · [REZOLVAT]
- **Simptom:** la teste, scanarea cu parolă corectă era tratată ca parolă greșită, iar cea cu parolă greșită trecea.
- **Cauză:** aplicația trimitea parola către motor cu un caracter invizibil (BOM UTF-8) în față, deci parola ajungea modificată.
- **Rezolvare:** parola se trimite acum ca octeți UTF-8 fără BOM. Motorul citește intrarea și scrie ieșirea explicit în UTF-8,
  fără să depindă de codepage-ul consolei (852 pe Windows în română).
- **Prevenire:** testul automat `test_parola_gresita_opreste` verifică acest caz la fiecare rulare.

### 2026-10-19 · 💻 Local · v1.0.0 · [REZOLVAT]
- **Simptom:** paginile cu formulare dădeau eroare („csrf_token is undefined“).
- **Cauză:** macro-urile Jinja importate nu primeau contextul paginii.
- **Rezolvare:** `{% from '_macro.html' import … with context %}` în toate paginile.
- **Prevenire:** testul `test_pagini_se_incarca` deschide toate paginile la fiecare rulare.
