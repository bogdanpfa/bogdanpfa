"""Construiește sabloane/CSS_model.docx (cu câmpuri {{...}}) din modelul original.

Se rulează o singură dată (sau când se schimbă modelul original):

    python scripts/build_template.py

Șablonul rezultat se poate edita apoi liber în Word: contează doar ca textul
{{câmp}} să rămână în document. Vezi lista câmpurilor în README.md.
"""
import copy
import re
import sys
import zipfile
from pathlib import Path

from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from generators.docx_generator import NS, W, _latime, _q, _set_text, _text  # noqa: E402

BASE = Path(__file__).resolve().parents[1]
ORIGINAL = BASE / "sabloane" / "originale" / "CSS_model_original.docx"
REZULTAT = BASE / "sabloane" / "CSS_model.docx"

# (paragraf, grup de linie, nume câmp, puncte în plus față de linia din model)
CAMPURI = [
    (6, 0, "nume", 0), (6, 1, "initiala", 0), (7, 0, "prenume", 0), (8, 0, "companie", 150),
    (9, 0, "functie", 150), (10, 0, "locatia", 150), (13, 0, "sef_direct", 150),
    (15, 0, "cladire", 0), (15, 1, "etaj", 0), (15, 2, "camera", 0),
    (17, 0, "tel_cfr", 0), (17, 1, "tel_fix", 0), (18, 2, "fax_cfr", 0),
    (22, 0, "aspr_detalii", 80), (24, 0, "suport_detalii", 85),
    (25, 1, "alte_servicii_1", 90), (26, 0, "alte_servicii_2", 90),
]
# Neatinse (rămân linii goale): Departament (12), Mobil (18/0), Tel. IP (18/1), Unitate (11/1)

CASUTE = {
    4: ["op_nou", "op_transferat", "op_modificari", "op_stergere_utilizator"],
    11: ["loc_central", "loc_regional", "loc_unitate"],
    21: ["srv_adaugare", "srv_stergere"],
    22: ["srv_aspr"], 23: ["srv_rentrad", "srv_internet", "srv_email", "srv_legis"],
    24: ["srv_suport"], 25: ["srv_alte"],
}
# (paragraf, câmp): textul de după ultimul TAB devine un singur câmp
DUPA_TAB = [(31, "ben_nume"), (32, "ben_functie"), (34, "data_ben")]
P_ANTET, P_ALTE_DETALII, P_DATA = 1, 19, 34


def este_gol(run):
    if run.find("w:sym", NS) is not None or run.find("w:drawing", NS) is not None or run.find("w:tab", NS) is not None:
        return False
    t = _text(run)
    if "_" in t and re.fullmatch(r"[_ ]+", t):
        return True
    return bool(t) and t.strip() == "" and run.find("w:rPr/w:u", NS) is not None


def grupuri(paragraf):
    rezultat, curent = [], []
    for run in paragraf.findall("w:r", NS):
        if este_gol(run):
            curent.append(run)
            continue
        if any("_" in _text(r) for r in curent):
            rezultat.append(curent)
        curent = []
    if any("_" in _text(r) for r in curent):
        rezultat.append(curent)
    return rezultat


def lungime(runuri):
    return sum(_latime(_text(r), bold=r.find("w:rPr/w:b", NS) is not None) for r in runuri)


def rpr(subliniat=True, dim=24):
    el = etree.Element(_q("rPr"))
    f = etree.SubElement(el, _q("rFonts"))
    f.set(_q("ascii"), "Cambria")
    f.set(_q("hAnsi"), "Cambria")
    if subliniat:
        etree.SubElement(el, _q("u")).set(_q("val"), "single")
    for e in ("sz", "szCs"):
        etree.SubElement(el, _q(e)).set(_q("val"), str(dim))
    etree.SubElement(el, _q("lang")).set(_q("val"), "ro-RO")
    return el


def run_nou(text, subliniat=True, dim=24):
    r = etree.Element(_q("r"))
    r.append(rpr(subliniat, dim))
    _set_text(r, text)
    return r


def spatiu_inainte(run_nou_el):
    """Dacă eticheta dinainte nu se termină cu spațiu, adaugă unul (nesubliniat)."""
    anterior = run_nou_el.getprevious()
    while anterior is not None and anterior.tag != _q("r"):
        anterior = anterior.getprevious()
    if anterior is None:
        return
    t = _text(anterior)
    if anterior.find("w:tab", NS) is None and (anterior.find("w:sym", NS) is not None
                                              or (t and not t.endswith(" "))):
        run_nou_el.addprevious(run_nou(" ", subliniat=False))


def nr(x):
    return str(int(round(x)))


def main():
    with zipfile.ZipFile(ORIGINAL) as z:
        radacina = etree.fromstring(z.read("word/document.xml"))
        paragrafe = list(radacina.iter(_q("p")))
        p = lambda i: paragrafe[i]

        # Toate grupurile și căsuțele, înainte de orice modificare
        g = {i: grupuri(p(i)) for i in {c[0] for c in CAMPURI}}
        cas = {i: [r for r in p(i).findall("w:r", NS)
                   if r.find("w:sym", NS) is not None or _text(r) in ("X", "x")] for i in CASUTE}

        # 1. Textul roșu devine negru
        for culoare in list(radacina.iter(_q("color"))):
            if culoare.get(_q("val")) == "FF0000":
                culoare.getparent().remove(culoare)

        # 2. Căsuțe -> {{op_nou}} etc.
        for i, nume in CASUTE.items():
            for run, n in zip(cas[i], nume):
                nou = run_nou("{{%s}}" % n, subliniat=False)
                run.addnext(nou)
                run.getparent().remove(run)

        # 3. Linii -> {{câmp:min:max}}
        for i, k, nume, extra in CAMPURI:
            grup = g[i][k]
            minim = lungime(grup)
            text = "{{%s:%s:%s}}" % (nume, nr(minim), nr(minim + extra)) if extra else "{{%s:%s}}" % (nume, nr(minim))
            nou = run_nou(text)
            grup[0].addprevious(nou)
            for r in grup:
                r.getparent().remove(r)
            spatiu_inainte(nou)

        # 4. Beneficiar și dată: tot ce e după ultimul TAB devine un câmp
        for i, nume in DUPA_TAB:
            runuri = p(i).findall("w:r", NS)
            ultim_tab = max(j for j, r in enumerate(runuri) if r.find("w:tab", NS) is not None)
            de_scos = [r for r in runuri[ultim_tab + 1:] if _text(r) and r.find("w:drawing", NS) is None]
            # run-ul cu TAB poate conține și linii „___” (text după tab): le scoatem
            resturi = [r for r in [runuri[ultim_tab]] if _text(r)]
            minim = lungime(de_scos + resturi)
            for r in resturi:
                for t in r.findall("w:t", NS):
                    r.remove(t)
            nou = run_nou("{{%s:%s}}" % (nume, nr(minim)))
            runuri[ultim_tab].addnext(nou)
            for r in de_scos:
                r.getparent().remove(r)

        # 5. Antetul: Nr. {{nr_prefix}} / {{numar}} / {{data}}
        antet = p(P_ANTET)
        runuri = antet.findall("w:r", NS)
        rpr_antet = copy.deepcopy(runuri[0].find("w:rPr", NS))
        for r in runuri:
            antet.remove(r)
        for m in antet.findall("w:bookmarkStart", NS) + antet.findall("w:bookmarkEnd", NS):
            antet.remove(m)
        r = etree.SubElement(antet, _q("r"))
        r.append(rpr_antet)
        _set_text(r, "Nr. {{nr_prefix}} / {{numar:36}} / {{data}}")

        # 6. „Alte detalii necesare:” + text (nesubliniat, 11 pt)
        det = p(P_ALTE_DETALII)
        ultimul_text = [r for r in det.findall("w:r", NS) if r.find("w:tab", NS) is None][-1]
        ultimul_text.addnext(run_nou(" {{alte_detalii}}", subliniat=False, dim=22))

        # 7. „* Câmp obligatoriu”: nota de final din model devine paragraf în corp,
        #    imediat după „Data” (LibreOffice pune notele de final pe o pagină separată)
        for ref in list(radacina.iter(_q("endnoteReference"))):
            run = ref.getparent()
            run.remove(ref)
            for simbol in run.findall("w:sym", NS):
                _set_text(run, "*")
                run.remove(simbol)
        nota = etree.Element(_q("p"))
        ppr = etree.SubElement(nota, _q("pPr"))
        etree.SubElement(ppr, _q("pStyle")).set(_q("val"), "FootnoteText")
        bdr = etree.SubElement(ppr, _q("pBdr"))
        sus = etree.SubElement(bdr, _q("top"))
        for a, v in (("val", "single"), ("sz", "4"), ("space", "1"), ("color", "auto")):
            sus.set(_q(a), v)
        sp = etree.SubElement(ppr, _q("spacing"))
        for a, v in (("before", "360"), ("after", "0"), ("line", "240"), ("lineRule", "auto")):
            sp.set(_q(a), v)
        etree.SubElement(ppr, _q("ind")).set(_q("right"), "6191")  # linie scurtă, ca în Word
        r1 = etree.SubElement(nota, _q("r"))
        _set_text(r1, "* ")
        r2 = etree.SubElement(nota, _q("r"))
        etree.SubElement(etree.SubElement(r2, _q("rPr")), _q("i"))
        _set_text(r2, "Câmp obligatoriu")
        p(P_DATA).addnext(nota)

        # 8. Scriere
        with zipfile.ZipFile(REZULTAT, "w", zipfile.ZIP_DEFLATED) as out:
            for item in z.infolist():
                continut = z.read(item.filename)
                if item.filename == "word/document.xml":
                    continut = etree.tostring(radacina, xml_declaration=True, encoding="UTF-8", standalone=True)
                out.writestr(item, continut)
    print("Scris:", REZULTAT)


if __name__ == "__main__":
    main()
