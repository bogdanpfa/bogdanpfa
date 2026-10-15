"""
Generare PDF pentru Ordin de Deplasare (Delegație) — A5 portrait, 2 pagini.
Pagina 1: Față (datele ordinului)
Pagina 2: Verso (decontul cheltuielilor)
"""
import os
import platform
from io import BytesIO
from reportlab.lib.pagesizes import A5
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── Fonturi Unicode (suport diacritice) ──────────────────────────────────────

_fonturi_init = False


def _init_fonturi():
    global _fonturi_init
    if _fonturi_init:
        return
    candidati = []
    if platform.system() == 'Windows':
        candidati += [
            (r'C:\Windows\Fonts\arial.ttf', r'C:\Windows\Fonts\arialbd.ttf'),
        ]
    candidati += [
        ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
         '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
        ('/usr/share/fonts/dejavu/DejaVuSans.ttf',
         '/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf'),
    ]
    for normal, bold in candidati:
        if os.path.exists(normal) and os.path.exists(bold):
            pdfmetrics.registerFont(TTFont('ODF', normal))
            pdfmetrics.registerFont(TTFont('ODF-B', bold))
            _fonturi_init = True
            return
    _fonturi_init = True  # fallback Helvetica


def _f(bold=False):
    _init_fonturi()
    try:
        pdfmetrics.getFont('ODF')
        return 'ODF-B' if bold else 'ODF'
    except Exception:
        return 'Helvetica-Bold' if bold else 'Helvetica'


# ── Constante layout A5 portrait (148×210 mm) ────────────────────────────────

PH = 210   # înălțime pagină mm
PW = 148   # lățime pagină mm
ML = 5     # margine stânga
MR = 143   # margine dreapta
W = MR - ML  # 138 mm lățime utilă


# ── Helper de desenare ───────────────────────────────────────────────────────

class D:
    """Wrapper ReportLab canvas cu coordonate y de sus în jos (mm)."""

    def __init__(self, c: Canvas):
        self.c = c

    def _y(self, v):
        return (PH - v) * mm

    def hline(self, x1, x2, y, lw=0.5):
        self.c.setLineWidth(lw)
        self.c.line(x1 * mm, self._y(y), x2 * mm, self._y(y))

    def vline(self, x, y1, y2, lw=0.5):
        self.c.setLineWidth(lw)
        self.c.line(x * mm, self._y(y1), x * mm, self._y(y2))

    def box(self, x, y, w, h, lw=0.7):
        self.c.setLineWidth(lw)
        self.c.rect(x * mm, self._y(y + h), w * mm, h * mm)

    def t(self, x, y, s, sz=8, bold=False, align='l'):
        if s is None:
            s = ''
        self.c.setFont(_f(bold), sz)
        xp, yp = x * mm, self._y(y)
        s = str(s)
        if align == 'c':
            self.c.drawCentredString(xp, yp, s)
        elif align == 'r':
            self.c.drawRightString(xp, yp, s)
        else:
            self.c.drawString(xp, yp, s)

    def rand(self, x, y, latime, eticheta, valoare, esz=6.5, vsz=8.5, et_latime=None):
        """
        Rând cu etichetă + linie punctată + valoare.
        et_latime: lățimea etichetei în mm (auto dacă None)
        """
        if eticheta:
            self.t(x, y, eticheta, sz=esz)
        lx = x + (et_latime if et_latime is not None else len(eticheta) * esz * 0.42 + 1.5)
        self.hline(lx, x + latime, y + 1.2, lw=0.3)
        if valoare:
            self.t(lx + 0.5, y, str(valoare), sz=vsz)

    def rand_cont(self, x, y, latime, valoare, vsz=8.5):
        """Rând fără etichetă (continuare)."""
        self.hline(x, x + latime, y + 1.2, lw=0.3)
        if valoare:
            self.t(x + 0.5, y, str(valoare), sz=vsz)


# ── Pagina 1 (Față) ──────────────────────────────────────────────────────────

def _p1(d: D, data):
    def g(k):
        v = data.get(k, '') or ''
        return v.strip() if isinstance(v, str) else str(v)

    # ── 1. HEADER (y: 3–20) ──
    d.box(ML, 3, W, 17, lw=0.8)
    d.vline(90, 3, 20)
    d.hline(90, MR, 11, lw=0.4)

    # Stânga: Unitatea
    d.t(ML + 1, 8, 'Unitatea', sz=6.5)
    d.hline(ML + 1, 88, 16, lw=0.3)
    d.t(ML + 1, 14.5, g('unitatea'), sz=8.5)

    # Dreapta: Depus decontul
    d.t(91, 7.5, 'Depus decontul (nr. și data)', sz=6.5)
    d.hline(91, MR - 1, 16, lw=0.3)
    d.t(91, 14.5, g('depus_decont'), sz=8)

    # ── 2. TITLU (y: 20–40) ──
    d.box(ML, 20, W, 20, lw=0.8)
    d.t(PW / 2, 31, 'ORDIN DE DEPLASARE (DELEGAȚIE)', sz=10, bold=True, align='c')
    d.t(PW / 2, 38, 'Nr. ' + g('nr_ordin'), sz=9, align='c')

    # ── 3. DATE DELEGAT (y: 40–126) ──
    d.box(ML, 40, W, 86, lw=0.8)

    # Dl./D-na
    titlu = g('titlu') or 'Dl.'
    d.t(ML + 1, 48.5, titlu, sz=6.5)
    d.hline(ML + 1 + len(titlu) * 2.5, MR - 1, 49.5, lw=0.3)
    d.t(ML + 1 + len(titlu) * 2.5 + 1, 48, g('nume_prenume'), sz=8.5)

    # Funcția
    d.t(ML + 1, 57.5, 'având funcția de', sz=6.5)
    d.hline(ML + 36, MR - 1, 58.5, lw=0.3)
    d.t(ML + 37, 57, g('functia'), sz=8.5)

    # Scopul — 3 linii
    d.t(ML + 1, 66.5, 'este delegat/delegată pentru', sz=6.5)
    d.hline(ML + 56, MR - 1, 67.5, lw=0.3)
    scop1 = g('scop_1')
    if scop1:
        d.t(ML + 57, 66, scop1, sz=8.5)
    d.hline(ML + 1, MR - 1, 76.5, lw=0.3)
    scop2 = g('scop_2')
    if scop2:
        d.t(ML + 1.5, 75.5, scop2, sz=8.5)
    d.hline(ML + 1, MR - 1, 85.5, lw=0.3)
    scop3 = g('scop_3')
    if scop3:
        d.t(ML + 1.5, 84.5, scop3, sz=8.5)

    # Destinația — 2 linii
    d.t(ML + 1, 93.5, 'la', sz=6.5)
    d.hline(ML + 6, MR - 1, 94.5, lw=0.3)
    dest1 = g('dest_1')
    if dest1:
        d.t(ML + 7, 93, dest1, sz=8.5)
    d.hline(ML + 1, MR - 1, 103.5, lw=0.3)
    dest2 = g('dest_2')
    if dest2:
        d.t(ML + 1.5, 102.5, dest2, sz=8.5)

    # Durata deplasării
    d.t(ML + 1, 111.5, 'Durata deplasării de la', sz=6.5)
    d.hline(ML + 46, ML + 78, 112.5, lw=0.3)
    d.t(ML + 79, 111.5, 'la', sz=6.5)
    d.hline(ML + 83, MR - 1, 112.5, lw=0.3)
    if g('durata_de_la'):
        d.t(ML + 47, 111, g('durata_de_la'), sz=8.5)
    if g('durata_pana_la'):
        d.t(ML + 84, 111, g('durata_pana_la'), sz=8.5)

    # Legitimație
    d.t(ML + 1, 120.5, 'Se legitimează cu', sz=6.5)
    d.hline(ML + 35, MR - 1, 121.5, lw=0.3)
    if g('legitimatie'):
        d.t(ML + 36, 120, g('legitimatie'), sz=8.5)

    # ── 4. ȘTAMPILĂ (y: 126–148) ──
    d.box(ML, 126, W, 22, lw=0.8)
    d.t(PW / 2, 136, 'Ștampila unității și semnătura', sz=8, bold=True, align='c')

    # ── 5. DATA (y: 148–157) ──
    d.t(ML + 1, 154.5, 'Data', sz=6.5)
    d.hline(ML + 10, MR - 1, 155.5, lw=0.3)
    if g('data_emitere'):
        d.t(ML + 11, 154, g('data_emitere'), sz=8.5)

    # ── 6. CASETE VIZE 2×2 (y: 157–204) ──
    mid = (ML + MR) / 2  # ~74mm
    cel_h = 23
    for row in range(2):
        y0 = 157 + row * cel_h
        for col in range(2):
            x0 = ML if col == 0 else mid
            cw = mid - ML
            d.box(x0, y0, cw, cel_h, lw=0.6)
            d.t(x0 + 1, y0 + 5.5, 'Sosit*)', sz=6.5)
            d.hline(x0 + 14, x0 + cw - 1, y0 + 6.5, lw=0.25)
            d.t(x0 + 1, y0 + 11, 'Plecat*)', sz=6.5)
            d.hline(x0 + 14, x0 + cw - 1, y0 + 12, lw=0.25)
            d.t(x0 + 1, y0 + 16.5, 'Cu (fără) cazare', sz=6.5)
            d.hline(x0 + 30, x0 + cw - 1, y0 + 17.5, lw=0.25)
            d.t(x0 + cw / 2, y0 + 20, 'Ștampila unității și', sz=6, align='c')
            d.t(x0 + cw / 2, y0 + 22.5, 'Semnătura', sz=6, align='c')

    # ── 7. NOTĂ DE SUBSOL ──
    d.t(ML, 207, '*) Se va completa ziua, luna, anul și ora', sz=5.5)


# ── Pagina 2 (Verso — Decont) ────────────────────────────────────────────────

def _p2(d: D, data):
    def g(k):
        v = data.get(k, '') or ''
        return v.strip() if isinstance(v, str) else str(v)

    def gf(k):
        """Valoare numerică pentru sume."""
        try:
            return float((data.get(k) or '0').replace(',', '.'))
        except Exception:
            return 0.0

    # ── 1. HEADER VERSO (y: 3–32) ──
    d.box(ML, 3, W, 29, lw=0.8)
    mid = 78
    d.vline(mid, 3, 32)

    # Stânga
    d.t(ML + 1, 9, 'Ziua și ora plecării', sz=6.5)
    d.hline(ML + 38, mid - 1, 10, lw=0.3)
    d.t(ML + 39, 8.5, g('ziua_ora_plecarii'), sz=8)

    d.t(ML + 1, 15, 'Ziua și ora sosirii', sz=6.5)
    d.hline(ML + 37, mid - 1, 16, lw=0.3)
    d.t(ML + 38, 14.5, g('ziua_ora_sosirii'), sz=8)

    d.t(ML + 1, 21, 'Data depunerii decontului', sz=6.5)
    d.hline(ML + 49, mid - 1, 22, lw=0.3)
    d.t(ML + 50, 20.5, g('data_depunere_decont'), sz=8)

    d.t(ML + 1, 27, 'Penalizări calculate', sz=6.5)
    d.hline(ML + 38, mid - 1, 28, lw=0.3)
    d.t(ML + 39, 26.5, g('penalizari'), sz=8)

    # Dreapta — Avans
    d.t((mid + MR) / 2, 7.5, 'Avans spre decontare', sz=7, bold=True, align='c')
    d.t(mid + 2, 13, '- Primit la plecare', sz=6.5)
    d.hline(mid + 37, MR - 8, 14, lw=0.3)
    d.t(MR - 7, 13, 'lei', sz=6.5)
    if gf('avans_plecare'):
        d.t(mid + 38, 12.5, f'{gf("avans_plecare"):.2f}', sz=8, align='r')
        # right-align before "lei"

    d.t(mid + 2, 19, '- Primit în timpul deplasării', sz=6.5)
    d.hline(mid + 54, MR - 8, 20, lw=0.3)
    d.t(MR - 7, 19, 'lei', sz=6.5)
    if gf('avans_deplasare'):
        d.t(MR - 9, 18.5, f'{gf("avans_deplasare"):.2f}', sz=8, align='r')

    avans_total = gf('avans_plecare') + gf('avans_deplasare')
    d.t(mid + 2, 25, 'TOTAL', sz=7, bold=True)
    d.hline(mid + 14, MR - 8, 26, lw=0.3)
    d.t(MR - 7, 25, 'lei', sz=6.5)
    if avans_total:
        d.t(MR - 9, 24.5, f'{avans_total:.2f}', sz=8, bold=True, align='r')

    # ── 2. TITLU TABEL CHELTUIELI (y: 32–38) ──
    d.box(ML, 32, W, 6, lw=0.8)
    d.t(PW / 2, 36.5,
        'CHELTUIELI EFECTUATE CONFORM DOCUMENTELOR ANEXATE',
        sz=6.5, bold=True, align='c')

    # ── 3. HEADER TABEL (y: 38–44) ──
    col1_w = 70   # Felul actului + emitentul
    col2_w = 38   # Nr. și data
    col3_w = 30   # Suma
    c1x = ML
    c2x = ML + col1_w
    c3x = ML + col1_w + col2_w

    d.box(ML, 38, W, 6, lw=0.8)
    d.vline(c2x, 38, 44)
    d.vline(c3x, 38, 44)
    d.t(c1x + col1_w / 2, 42.5, 'Felul actului și emitentul', sz=6.5, align='c')
    d.t(c2x + col2_w / 2, 42.5, 'Nr. și data actului', sz=6.5, align='c')
    d.t(c3x + col3_w / 2, 42.5, 'Suma', sz=6.5, align='c')

    # ── 4. RÂNDURI CHELTUIELI (y: 44–...) ──
    rand_h = 7
    nr_randuri = 12
    y_tabel_start = 44
    total_ch = 0.0

    for i in range(nr_randuri):
        yr = y_tabel_start + i * rand_h
        d.hline(ML, MR, yr + rand_h, lw=0.3)
        d.vline(c2x, yr, yr + rand_h, lw=0.3)
        d.vline(c3x, yr, yr + rand_h, lw=0.3)
        d.vline(ML, yr, yr + rand_h, lw=0.3)
        d.vline(MR, yr, yr + rand_h, lw=0.3)

        fel = g(f'ch_fel_{i}')
        emitent = g(f'ch_emitent_{i}')
        nr_act = g(f'ch_nr_{i}')
        data_act = g(f'ch_data_{i}')
        suma = gf(f'ch_suma_{i}')

        if fel:
            d.t(c1x + 0.5, yr + 4.5, fel, sz=6.5)
        if emitent:
            d.t(c1x + 0.5, yr + 4.5 + (3 if fel else 0), emitent, sz=6)
        nr_data = ' / '.join(filter(None, [nr_act, data_act]))
        if nr_data:
            d.t(c2x + 0.5, yr + 4.5, nr_data, sz=6.5)
        if suma:
            d.t(c3x + col3_w - 0.5, yr + 4.5, f'{suma:.2f}', sz=7, align='r')
            total_ch += suma

    # ── 5. TOTAL CHELTUIELI ──
    y_total = y_tabel_start + nr_randuri * rand_h
    d.box(ML, y_total, W, 7, lw=0.8)
    d.vline(c2x, y_total, y_total + 7)
    d.vline(c3x, y_total, y_total + 7)
    d.t(PW / 2, y_total + 5, 'TOTAL CHELTUIELI', sz=7.5, bold=True, align='c')
    if total_ch:
        d.t(c3x + col3_w - 0.5, y_total + 5, f'{total_ch:.2f}', sz=8, bold=True, align='r')

    # ── 6. DIFERENȚE (y: ...) ──
    y_dif = y_total + 7
    d.box(ML, y_dif, W, 14, lw=0.8)
    d.vline(mid, y_dif, y_dif + 14)

    d.t(ML + 1, y_dif + 5, 'Diferența de restituit s-a depus cu', sz=6)
    d.t(ML + 1, y_dif + 9, 'dispoziție de încasare către casierie', sz=6)
    d.t(ML + 1, y_dif + 13, 'Nr.', sz=6)
    d.hline(ML + 9, ML + 30, y_dif + 13.5, lw=0.3)
    d.t(ML + 31, y_dif + 13, 'din', sz=6)
    d.hline(ML + 37, mid - 1, y_dif + 13.5, lw=0.3)

    tip = g('diferenta_tip') or 'primit'
    val_dif = gf('diferenta_val')
    d.t(mid + 2, y_dif + 6, f'Diferența de', sz=6.5)
    d.t(mid + 2, y_dif + 10, tip, sz=7, bold=True)
    d.hline(mid + 2, MR - 8, y_dif + 13.5, lw=0.3)
    d.t(MR - 7, y_dif + 13, 'lei', sz=6.5)
    if val_dif:
        d.t(MR - 9, y_dif + 12.5, f'{val_dif:.2f}', sz=8, align='r')

    # ── 7. SEMNĂTURI (y: ...) ──
    y_semn = y_dif + 14
    semn_labels = [
        'Aprobat\nconductorul\nunității',
        'Control financiar\npreventiv',
        'Verificat\ndecont',
        'Șef\ncompartiment',
        'Titular\navans',
    ]
    semn_h = 17
    cel_w = W / len(semn_labels)

    d.box(ML, y_semn, W, semn_h, lw=0.8)
    for i, label in enumerate(semn_labels):
        xc = ML + i * cel_w
        if i > 0:
            d.vline(xc, y_semn, y_semn + semn_h)
        cx = xc + cel_w / 2
        for j, linie in enumerate(label.split('\n')):
            d.t(cx, y_semn + 4 + j * 4, linie, sz=5.5, align='c')


# ── Entry point ──────────────────────────────────────────────────────────────

def generate_pdf(data) -> bytes:
    """Generează PDF A5 cu 2 pagini și returnează bytes."""
    buf = BytesIO()
    c = Canvas(buf, pagesize=A5)

    d = D(c)
    _p1(d, data)
    c.showPage()

    d2 = D(c)
    _p2(d2, data)
    c.showPage()

    c.save()
    buf.seek(0)
    return buf.read()
