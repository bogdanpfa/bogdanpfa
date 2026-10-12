"""Completează șablonul sabloane/CSS_model.docx și îl convertește în PDF.

Șablonul are câmpuri marcate în text:

    {{nume}}          valoarea câmpului „nume”
    {{nume:98}}       idem, linia subliniată e completată până la 98 pt
    {{nume:98:250}}   idem; valoarea poate crește până la 250 pt (apoi se micșorează fontul)
    {{op_nou}}        căsuță de bifat: devine „X” (bifat) sau „☐”

Aspectul (font, mărime, subliniere, culoare) se ia de pe câmpul din șablon, deci
formularul se poate rearanja liber în Word, atât timp cât câmpurile rămân în text.
Lista câmpurilor: vezi README.md.
"""
import copy
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from lxml import etree
from PIL import ImageFont

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"

BASE_DIR = Path(__file__).resolve().parents[1]
SABLON = BASE_DIR / "sabloane" / "CSS_model.docx"

# Caladea are aceleași dimensiuni ale literelor ca Cambria, deci măsurătoarea
# lățimii textului e valabilă și pe Windows (cu Cambria) și pe Linux (cu Caladea).
_FONT_DIRS = [Path(r"C:\Windows\Fonts"), Path("/usr/share/fonts/truetype/crosextra")]
_FONT_FILES = {False: ("cambria.ttc", "Caladea-Regular.ttf"), True: ("cambriab.ttf", "Caladea-Bold.ttf")}
_cache_fonturi = {}

CAMP = re.compile(r"\{\{\s*([A-Za-z0-9_]+)\s*(?::\s*(\d+(?:\.\d+)?))?\s*(?::\s*(\d+(?:\.\d+)?))?\s*\}\}")

# Căsuțe de bifat: nume câmp -> (grup, valoare)
OPERATIUNI = {"op_nou": "Nou", "op_transferat": "Transferat", "op_modificari": "Modificări",
              "op_stergere_utilizator": "Ștergere utilizator"}
TIPURI_LOCATIE = {"loc_central": "Central", "loc_regional": "Regional", "loc_unitate": "Unitate"}
SERVICII = {"srv_adaugare": "Adăugare", "srv_stergere": "Ștergere", "srv_aspr": "ASP-R",
            "srv_rentrad": "RENTRAD", "srv_internet": "Internet", "srv_email": "E-Mail",
            "srv_legis": "Legis", "srv_suport": "Suport tehnic", "srv_alte": "Alte servicii"}


def _q(tag):
    return f"{{{W}}}{tag}"


def _font(bold):
    if bold not in _cache_fonturi:
        gasit = None
        for folder in _FONT_DIRS:
            for nume in _FONT_FILES[bold]:
                if (folder / nume).exists():
                    gasit = ImageFont.truetype(str(folder / nume), 1000)
                    break
            if gasit:
                break
        _cache_fonturi[bold] = gasit
    return _cache_fonturi[bold]


def _latime(text, bold=False, size_pt=12.0):
    """Lățimea textului în puncte tipografice."""
    font = _font(bold)
    if font is None:
        return len(text) * size_pt * 0.5
    return font.getlength(text) * size_pt / 1000


# --------------------------------------------------------------------------
# Run-uri și câmpuri
# --------------------------------------------------------------------------
def _runuri(paragraf):
    return [r for r in paragraf.findall("w:r", NS)]


def _text(run):
    return "".join(t.text or "" for t in run.findall("w:t", NS))


def _set_text(run, valoare):
    for t in run.findall("w:t", NS):
        run.remove(t)
    t = etree.SubElement(run, _q("t"))
    t.text = valoare
    t.set(XML_SPACE, "preserve")


def _imparte(run, pozitie):
    """Împarte run-ul în două la `pozitie`; al doilea păstrează formatul."""
    text = _text(run)
    al_doilea = copy.deepcopy(run)
    _set_text(run, text[:pozitie])
    _set_text(al_doilea, text[pozitie:])
    run.addnext(al_doilea)
    return al_doilea


def _izoleaza_campuri(paragraf):
    """Pune fiecare {{câmp}} într-un run propriu (Word poate sparge textul în mai multe run-uri).

    Returnează lista de (run, potrivire) pentru câmpurile din paragraf.
    """
    while True:
        runuri = _runuri(paragraf)
        texte = [_text(r) for r in runuri]
        complet = "".join(texte)
        # prima potrivire care nu e încă izolată într-un run propriu
        potrivire = None
        for m in CAMP.finditer(complet):
            if not _este_izolat(runuri, texte, m):
                potrivire = m
                break
        if potrivire is None:
            break
        s, e = potrivire.span()
        # tăiem run-urile la marginile potrivirii
        pozitie = 0
        for run, text in zip(runuri, texte):
            inceput, sfarsit = pozitie, pozitie + len(text)
            pozitie = sfarsit
            if inceput < s < sfarsit:
                _imparte(run, s - inceput)
                break
        runuri = _runuri(paragraf)
        texte = [_text(r) for r in runuri]
        pozitie = 0
        for run, text in zip(runuri, texte):
            inceput, sfarsit = pozitie, pozitie + len(text)
            pozitie = sfarsit
            if inceput < e < sfarsit:
                _imparte(run, e - inceput)
                break
        # unim run-urile acoperite de potrivire în primul dintre ele
        runuri = _runuri(paragraf)
        texte = [_text(r) for r in runuri]
        pozitie, acoperite = 0, []
        for run, text in zip(runuri, texte):
            inceput, sfarsit = pozitie, pozitie + len(text)
            pozitie = sfarsit
            if text and inceput >= s and sfarsit <= e:
                acoperite.append(run)
        for run in acoperite[1:]:
            run.getparent().remove(run)
        _set_text(acoperite[0], potrivire.group(0))
    gasite = []
    for run in _runuri(paragraf):
        m = CAMP.fullmatch(_text(run).strip()) if _text(run) else None
        if m:
            gasite.append((run, m))
    return gasite


def _este_izolat(runuri, texte, potrivire):
    s, e = potrivire.span()
    pozitie = 0
    for run, text in zip(runuri, texte):
        inceput, sfarsit = pozitie, pozitie + len(text)
        pozitie = sfarsit
        if inceput == s and sfarsit == e:
            return True
    return False


def _dim_run(run):
    sz = run.find("w:rPr/w:sz", NS)
    return int(sz.get(_q("val"))) / 2 if sz is not None else 12.0


def _are(run, eticheta):
    el = run.find(f"w:rPr/w:{eticheta}", NS)
    return el is not None and el.get(_q("val"), "true") not in ("0", "false", "none")


def _seteaza_dim(run, dim):
    rpr = run.find("w:rPr", NS)
    if rpr is None:
        rpr = etree.Element(_q("rPr"))
        run.insert(0, rpr)
    for eticheta in ("sz", "szCs"):
        el = rpr.find(f"w:{eticheta}", NS)
        if el is None:
            el = etree.SubElement(rpr, _q(eticheta))
        el.set(_q("val"), str(int(round(dim * 2))))


def _completeaza_text(run, valoare, minim, maxim):
    """Pune valoarea în run.

    Valoare completată: text subliniat (micșorat dacă nu încape, apoi trunchiat).
    Câmp gol: linie „____” de lățimea `minim`, ca în modelul necompletat.
    """
    valoare = re.sub(r"\s+", " ", str(valoare or "")).strip()
    dim = _dim_run(run)
    bold = _are(run, "b")
    if not valoare:
        if minim:
            _set_text(run, "_" * max(int(minim // _latime("_", bold, dim)), 1))
            subliniere = run.find("w:rPr/w:u", NS)
            if subliniere is not None:
                subliniere.getparent().remove(subliniere)  # liniile „_” nu se mai subliniază (fără dublă linie)
        else:
            _set_text(run, "")
        return
    if maxim:
        while _latime(valoare, bold, dim) > maxim and dim > 8:
            dim -= 0.5
        while _latime(valoare, bold, dim) > maxim and len(valoare) > 1:
            valoare = valoare[:-1]
        _seteaza_dim(run, dim)
    _set_text(run, valoare)


def _completeaza_casuta(run, bifat):
    """Bifat = „X” aldin; nebifat = căsuța goală ☐."""
    rpr = run.find("w:rPr", NS)
    if rpr is None:
        rpr = etree.Element(_q("rPr"))
        run.insert(0, rpr)
    if bifat:
        if rpr.find("w:b", NS) is None:
            rpr.insert(0, etree.Element(_q("b")))
        _set_text(run, "X")
    else:
        fonturi = rpr.find("w:rFonts", NS)
        if fonturi is None:
            fonturi = etree.SubElement(rpr, _q("rFonts"))
            rpr.insert(0, fonturi)
        for atribut in ("ascii", "hAnsi", "eastAsia", "cs"):
            fonturi.set(_q(atribut), "Segoe UI Symbol")
        _set_text(run, "\u2610")


# --------------------------------------------------------------------------
# Valorile câmpurilor
# --------------------------------------------------------------------------
def _valori(d):
    """Textul fiecărui câmp, din datele trimise de formular."""
    an, luna, zi = (d.get("data") or "0000-00-00").split("-")
    data = f"{zi}.{luna}.{an}"
    return {
        "nr_prefix": re.sub(r"\s*/\s*", "/ ", str(d.get("nr_prefix", "IS 6/7"))).strip(),
        "numar": str(d.get("numar_inregistrare", "")).strip(), "data": data, "data_ben": data,
        "nume": d.get("nume"), "initiala": d.get("initiala_tata"), "prenume": d.get("prenume"),
        "companie": d.get("companie"), "functie": d.get("functie"), "locatia": d.get("loc_munca"),
        "sef_direct": d.get("sef_direct"), "cladire": d.get("cladire"), "etaj": d.get("etaj"),
        "camera": d.get("camera"), "tel_cfr": d.get("telefon_cfr"), "tel_fix": d.get("telefon_fix"),
        "fax_cfr": d.get("fax_cfr"), "alte_detalii": d.get("alte_detalii"),
        "aspr_detalii": d.get("aspr_detalii"), "suport_detalii": d.get("suport_detalii"),
        "ben_nume": d.get("beneficiar_nume"), "ben_functie": d.get("beneficiar_functie"),
    }


def _bifate(d):
    servicii = set(d.get("servicii") or [])
    bifate = {nume for nume, val in OPERATIUNI.items() if val == d.get("operatiune")}
    bifate |= {nume for nume, val in TIPURI_LOCATIE.items() if val == d.get("tip_locatie")}
    bifate |= {nume for nume, val in SERVICII.items() if val in servicii}
    return bifate


def _imparte_alte_servicii(text, latime_rand1, dim=12.0):
    """„Alte servicii”: textul curge pe cele două rânduri din formular."""
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    taiat = len(text)
    while taiat > 1 and _latime(text[:taiat], size_pt=dim) > latime_rand1:
        taiat -= 1
    if taiat < len(text) and " " in text[:taiat]:
        taiat = text[:taiat].rfind(" ")
    return text[:taiat].strip(), text[taiat:].strip()


def _completeaza(radacina, d):
    valori, bifate = _valori(d), _bifate(d)
    cunoscute = set(valori) | set(OPERATIUNI) | set(TIPURI_LOCATIE) | set(SERVICII) | {"alte_servicii_1", "alte_servicii_2"}
    campuri = []
    for paragraf in radacina.iter(_q("p")):
        campuri.extend(_izoleaza_campuri(paragraf))

    necunoscute = sorted({m.group(1) for _, m in campuri if m.group(1) not in cunoscute})
    if necunoscute:
        raise ValueError("Câmpuri necunoscute în șablon: " + ", ".join("{{%s}}" % n for n in necunoscute))

    # „Alte servicii”: lățimea primului rând decide unde se rupe textul
    rand1 = next(((r, m) for r, m in campuri if m.group(1) == "alte_servicii_1"), None)
    if rand1:
        maxim = float(rand1[1].group(3) or rand1[1].group(2) or 300)
        valori["alte_servicii_1"], valori["alte_servicii_2"] = _imparte_alte_servicii(
            d.get("alte_servicii"), maxim, _dim_run(rand1[0]))
    else:
        valori["alte_servicii_1"] = d.get("alte_servicii")
        valori["alte_servicii_2"] = ""

    for run, m in campuri:
        nume = m.group(1)
        if nume in OPERATIUNI or nume in TIPURI_LOCATIE or nume in SERVICII:
            _completeaza_casuta(run, nume in bifate)
            continue
        minim = float(m.group(2)) if m.group(2) else None
        maxim = float(m.group(3)) if m.group(3) else minim
        _completeaza_text(run, valori.get(nume), minim, maxim)


def genereaza_docx(d, destinatie):
    with zipfile.ZipFile(SABLON) as z:
        arbore = etree.fromstring(z.read("word/document.xml"))
        _completeaza(arbore, d)
        with zipfile.ZipFile(destinatie, "w", zipfile.ZIP_DEFLATED) as out:
            for item in z.infolist():
                continut = z.read(item.filename)
                if item.filename == "word/document.xml":
                    continut = etree.tostring(arbore, xml_declaration=True, encoding="UTF-8", standalone=True)
                out.writestr(item, continut)


def _cauta_soffice():
    for nume in ("soffice", "libreoffice"):
        gasit = shutil.which(nume)
        if gasit:
            return gasit
    for cale in (r"C:\Program Files\LibreOffice\program\soffice.exe",
                 r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"):
        if Path(cale).exists():
            return cale
    raise FileNotFoundError("LibreOffice nu este instalat (soffice nu a fost găsit).")


def genereaza_pdf(d, destinatie):
    """Completează șablonul și îl convertește în PDF la `destinatie`."""
    destinatie = Path(destinatie)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        docx = tmp / "formular.docx"
        genereaza_docx(d, docx)
        # Profil LibreOffice separat, ca să nu se blocheze cu o instanță deschisă de utilizator
        profil = (tmp / "profil").resolve().as_uri()
        subprocess.run(
            [_cauta_soffice(), f"-env:UserInstallation={profil}", "--headless", "--convert-to", "pdf",
             "--outdir", str(tmp), str(docx)],
            check=True, capture_output=True, timeout=120,
        )
        shutil.move(str(tmp / "formular.pdf"), destinatie)
