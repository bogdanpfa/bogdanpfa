"""
Generare PDF pentru Ordin de Deplasare (Delegație) — A5 portrait, 2 pagini.
Pagina 1: Față   |   Pagina 2: Verso (decont cheltuieli)
"""
import os
import platform
from io import BytesIO
from reportlab.lib.pagesizes import A5
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import stringWidth

# ── Fonturi ───────────────────────────────────────────────────────────────────

_fonturi_init = False


def _init_fonturi():
    global _fonturi_init
    if _fonturi_init:
        return
    candidati = []
    if platform.system() == 'Windows':
        # Cambria — serif formal, similar cu documentele oficiale
        candidati += [
            (r'C:\Windows\Fonts\cambria.ttf',  r'C:\Windows\Fonts\cambriab.ttf'),
            (r'C:\Windows\Fonts\times.ttf',    r'C:\Windows\Fonts\timesbd.ttf'),
            (r'C:\Windows\Fonts\arial.ttf',    r'C:\Windows\Fonts\arialbd.ttf'),
        ]
    # Linux: Liberation Serif ≈ Times New Roman
    candidati += [
        ('/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf',
         '/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf'),
        ('/usr/share/fonts/truetype/freefont/FreeSerif.ttf',
         '/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf'),
        ('/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf',
         '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'),
        ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
         '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
    ]
    for normal, bold in candidati:
        if os.path.exists(normal) and os.path.exists(bold):
            pdfmetrics.registerFont(TTFont('ODF', normal))
            pdfmetrics.registerFont(TTFont('ODF-B', bold))
            _fonturi_init = True
            return
    _fonturi_init = True


def _f(bold=False):
    _init_fonturi()
    try:
        pdfmetrics.getFont('ODF')
        return 'ODF-B' if bold else 'ODF'
    except Exception:
        return 'Helvetica-Bold' if bold else 'Helvetica'


def wrap_text(text, max_mm, font_name, font_size):
    """Împarte textul în linii care încap în max_mm lățime."""
    if not text:
        return []
    max_pts = max_mm * mm
    words = text.split()
    lines, cur = [], ''
    for word in words:
        probe = (cur + ' ' + word).strip()
        if stringWidth(probe, font_name, font_size) <= max_pts:
            cur = probe
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines or [text]


# ── Constante layout ──────────────────────────────────────────────────────────

PH = 210   # mm înălțime A5
PW = 148   # mm lățime A5
ML = 5     # margine stânga
MR = 143   # margine dreapta
W  = MR - ML   # 138 mm lățime utilă


# ── Helper canvas ─────────────────────────────────────────────────────────────

class D:
    """Canvas wrapper cu y de sus în jos (mm)."""

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

    def fill_rect(self, x, y, w, h, gray=0.92):
        """Fundal gri deschis pentru header tabel."""
        self.c.setFillColorRGB(gray, gray, gray)
        self.c.setStrokeColorRGB(gray, gray, gray)
        self.c.rect(x * mm, self._y(y + h), w * mm, h * mm, stroke=0, fill=1)
        self.c.setFillColorRGB(0, 0, 0)
        self.c.setStrokeColorRGB(0, 0, 0)


# ── Pagina 1 (Față) ───────────────────────────────────────────────────────────

def _p1(d: D, data):
    def g(k):
        v = data.get(k, '') or ''
        return v.strip() if isinstance(v, str) else str(v)

    # ── 1. HEADER (y: 3–27) ──────────────────────────────────────────────────
    HDR_Y, HDR_H = 3, 24
    d.box(ML, HDR_Y, W, HDR_H, lw=1.0)
    d.vline(90, HDR_Y, HDR_Y + HDR_H, lw=0.6)
    d.hline(90, MR, HDR_Y + 9, lw=0.4)

    # Stânga: Unitatea + subdiviziune
    d.t(ML + 1, HDR_Y + 5, 'Unitatea', sz=6, bold=False)
    unitate = g('unitatea')
    subdiv  = g('subdiviziunea')

    font_n = _f(False)
    # Unitate (bold, 8.5pt)
    d.t(ML + 1, HDR_Y + 11, unitate, sz=8.5, bold=True)
    # Subdiviziune (normal, 6.5pt, max 2 rânduri)
    if subdiv:
        linii = wrap_text(subdiv, 83, font_n, 6.5)
        for i, linie in enumerate(linii[:2]):
            d.t(ML + 1, HDR_Y + 16 + i * 5.5, linie, sz=6.5)

    # Dreapta: Depus decontul
    d.t(91, HDR_Y + 5, 'Depus decontul (nr. și data)', sz=6)
    d.hline(91, MR - 1, HDR_Y + 18, lw=0.3)
    d.t(91, HDR_Y + 16, g('depus_decont'), sz=8)

    # ── 2. TITLU (y: 27–46) ──────────────────────────────────────────────────
    TTL_Y = HDR_Y + HDR_H
    d.box(ML, TTL_Y, W, 19, lw=1.0)
    d.t(PW / 2, TTL_Y + 10, 'ORDIN DE DEPLASARE (DELEGAȚIE)', sz=10, bold=True, align='c')
    d.t(PW / 2, TTL_Y + 17, 'Nr. ' + g('nr_ordin'), sz=9, align='c')

    # ── 3. DATE DELEGAT (y: 46–126) ──────────────────────────────────────────
    CNT_Y = TTL_Y + 19
    d.box(ML, CNT_Y, W, 80, lw=1.0)

    def rand(y_rel, eticheta, valoare, et_mm):
        """Rând cu etichetă fixă + linie + valoare."""
        y = CNT_Y + y_rel
        d.t(ML + 1, y, eticheta, sz=6.5)
        d.hline(ML + et_mm, MR - 1, y + 1.3, lw=0.3)
        if valoare:
            d.t(ML + et_mm + 0.5, y, str(valoare), sz=8.5)

    def rand_cont(y_rel, valoare):
        y = CNT_Y + y_rel
        d.hline(ML + 1, MR - 1, y + 1.3, lw=0.3)
        if valoare:
            d.t(ML + 1.5, y, str(valoare), sz=8.5)

    titlu = g('titlu') or 'Dl.'
    rand(8,  titlu,                  g('nume_prenume'),  len(titlu) * 2.8 + 2)
    rand(17, 'având funcția de',     g('functia'),       37)
    rand(26, 'este delegat/delegată pentru', g('scop_1'), 57)
    rand_cont(35, g('scop_2'))
    rand_cont(44, g('scop_3'))
    rand(53, 'la',                   g('dest_1'),        6)
    rand_cont(62, g('dest_2'))

    # Durata
    y_dur = CNT_Y + 71
    d.t(ML + 1, y_dur, 'Durata deplasării de la', sz=6.5)
    d.hline(ML + 47, ML + 79, y_dur + 1.3, lw=0.3)
    d.t(ML + 80, y_dur, 'la', sz=6.5)
    d.hline(ML + 84, MR - 1, y_dur + 1.3, lw=0.3)
    if g('durata_de_la'):
        d.t(ML + 48, y_dur, g('durata_de_la'), sz=8.5)
    if g('durata_pana_la'):
        d.t(ML + 85, y_dur, g('durata_pana_la'), sz=8.5)

    rand(79, 'Se legitimează cu', g('legitimatie'), 35)

    # ── 4. ȘTAMPILĂ (y: 126–146) ─────────────────────────────────────────────
    SMP_Y = CNT_Y + 80
    d.box(ML, SMP_Y, W, 20, lw=1.0)
    d.t(PW / 2, SMP_Y + 9, 'Ștampila unității și semnătura', sz=8, bold=True, align='c')

    # ── 5. DATA (y: 146–155) ─────────────────────────────────────────────────
    DAT_Y = SMP_Y + 20
    d.t(ML + 1, DAT_Y + 7, 'Data', sz=6.5)
    d.hline(ML + 11, MR - 1, DAT_Y + 8, lw=0.3)
    if g('data_emitere'):
        d.t(ML + 12, DAT_Y + 7, g('data_emitere'), sz=8.5)

    # ── 6. CASETE VIZE 2×2 (y: 155–201) ─────────────────────────────────────
    VIZ_Y = DAT_Y + 9
    mid = (ML + MR) / 2
    cel_w = mid - ML
    cel_h = 23

    for row in range(2):
        for col in range(2):
            x0 = ML if col == 0 else mid
            y0 = VIZ_Y + row * cel_h
            d.box(x0, y0, cel_w, cel_h, lw=0.7)
            d.t(x0 + 1, y0 + 5.5, 'Sosit*)',         sz=6.5)
            d.hline(x0 + 14, x0 + cel_w - 1, y0 + 6.5, lw=0.25)
            d.t(x0 + 1, y0 + 11,  'Plecat*)',        sz=6.5)
            d.hline(x0 + 14, x0 + cel_w - 1, y0 + 12, lw=0.25)
            d.t(x0 + 1, y0 + 16.5, 'Cu (fără) cazare', sz=6.5)
            d.hline(x0 + 30, x0 + cel_w - 1, y0 + 17.5, lw=0.25)
            d.t(x0 + cel_w / 2, y0 + 20,   'Ștampila unității și', sz=5.5, align='c')
            d.t(x0 + cel_w / 2, y0 + 22.5, 'Semnătura',            sz=5.5, align='c')

    # ── 7. NOTĂ ───────────────────────────────────────────────────────────────
    d.t(ML, 207, '*) Se va completa ziua, luna, anul și ora', sz=5.5)


# ── Pagina 2 (Verso — Decont) ─────────────────────────────────────────────────

def _p2(d: D, data):
    def g(k):
        v = data.get(k, '') or ''
        return v.strip() if isinstance(v, str) else str(v)

    def gf(k):
        try:
            return float((data.get(k) or '0').replace(',', '.'))
        except Exception:
            return 0.0

    # ── 1. HEADER VERSO (y: 3–31) ────────────────────────────────────────────
    d.box(ML, 3, W, 28, lw=1.0)
    MID = 76
    d.vline(MID, 3, 31, lw=0.6)

    # Stânga
    def sv(eticheta, valoare, y, et_mm):
        d.t(ML + 1, y, eticheta, sz=6.5)
        d.hline(ML + et_mm, MID - 1, y + 1.2, lw=0.3)
        if valoare:
            d.t(ML + et_mm + 0.5, y, str(valoare), sz=8)

    sv('Ziua și ora plecării',        g('ziua_ora_plecarii'),   8.5,  38)
    sv('Ziua și ora sosirii',         g('ziua_ora_sosirii'),    15.5, 37)
    sv('Data depunerii decontului',   g('data_depunere_decont'),22.5, 50)
    sv('Penalizări calculate',        g('penalizari'),          29.5, 38)

    # Dreapta — Avans
    d.fill_rect(MID, 3, W - (MID - ML), 6.5, gray=0.90)
    d.t((MID + MR) / 2, 7.5, 'Avans spre decontare', sz=7, bold=True, align='c')

    def av(eticheta, valoare, y):
        d.t(MID + 2, y, eticheta, sz=6.5)
        d.hline(MID + 2, MR - 9, y + 1.2, lw=0.3)
        d.t(MR - 8, y, 'lei', sz=6.5)
        if valoare:
            d.t(MR - 9, y, f'{valoare:.2f}', sz=8, align='r')

    av('- Primit la plecare',         gf('avans_plecare'),   13)
    av('- Primit în timpul deplasării', gf('avans_deplasare'), 20)
    total_av = gf('avans_plecare') + gf('avans_deplasare')
    # linie înainte de total
    d.hline(MID + 2, MR - 1, 25.5, lw=0.5)
    d.t(MID + 2, 27, 'TOTAL', sz=7, bold=True)
    d.hline(MID + 2, MR - 9, 28, lw=0.3)
    d.t(MR - 8, 27, 'lei', sz=6.5)
    if total_av:
        d.t(MR - 9, 27, f'{total_av:.2f}', sz=8, bold=True, align='r')

    # ── 2. TITLU TABEL (y: 31–38) ────────────────────────────────────────────
    d.fill_rect(ML, 31, W, 7, gray=0.88)
    d.box(ML, 31, W, 7, lw=1.0)
    d.t(PW / 2, 36.5,
        'CHELTUIELI EFECTUATE CONFORM DOCUMENTELOR ANEXATE',
        sz=6.5, bold=True, align='c')

    # ── 3. HEADER TABEL (y: 38–45) ───────────────────────────────────────────
    C1W, C2W, C3W = 68, 40, 30   # lățimi coloane mm
    C1X = ML
    C2X = ML + C1W
    C3X = ML + C1W + C2W

    d.fill_rect(ML, 38, W, 7, gray=0.93)
    d.box(ML, 38, W, 7, lw=1.0)
    d.vline(C2X, 38, 45, lw=0.6)
    d.vline(C3X, 38, 45, lw=0.6)
    d.t(C1X + C1W / 2, 43, 'Felul actului și emitentul', sz=6.5, bold=True, align='c')
    d.t(C2X + C2W / 2, 43, 'Nr. și data actului',        sz=6.5, bold=True, align='c')
    d.t(C3X + C3W / 2, 43, 'Suma',                       sz=6.5, bold=True, align='c')

    # ── 4. RÂNDURI (y: 45–...) ────────────────────────────────────────────────
    RH = 7          # înălțime rând mm
    NR = 12         # număr rânduri
    Y0 = 45
    total_ch = 0.0

    for i in range(NR):
        yr = Y0 + i * RH
        # alternăm fundalul ușor
        if i % 2 == 0:
            d.fill_rect(ML, yr, W, RH, gray=0.97)

        d.hline(ML, MR, yr + RH, lw=0.25)
        d.vline(ML, yr, yr + RH, lw=0.5)
        d.vline(C2X, yr, yr + RH, lw=0.4)
        d.vline(C3X, yr, yr + RH, lw=0.4)
        d.vline(MR, yr, yr + RH, lw=0.5)

        fel    = g(f'ch_fel_{i}')
        nr_act = g(f'ch_nr_{i}')
        suma   = gf(f'ch_suma_{i}')

        if fel:
            # Trunchiem dacă e prea lung
            while fel and stringWidth(fel, _f(False), 6.5) > (C1W - 2) * mm:
                fel = fel[:-1]
            d.t(C1X + 0.5, yr + 4.5, fel, sz=6.5)

        if nr_act:
            d.t(C2X + 0.5, yr + 4.5, nr_act, sz=6.5)

        if suma:
            d.t(C3X + C3W - 0.5, yr + 4.5, f'{suma:.2f}', sz=7, align='r')
            total_ch += suma

    # ── 5. TOTAL (y: ...) ─────────────────────────────────────────────────────
    Y_TOT = Y0 + NR * RH
    d.fill_rect(ML, Y_TOT, W, 7, gray=0.88)
    d.box(ML, Y_TOT, W, 7, lw=1.0)
    d.vline(C2X, Y_TOT, Y_TOT + 7, lw=0.5)
    d.vline(C3X, Y_TOT, Y_TOT + 7, lw=0.5)
    d.t((ML + C3X) / 2, Y_TOT + 5, 'TOTAL CHELTUIELI', sz=8, bold=True, align='c')
    if total_ch:
        d.t(C3X + C3W - 0.5, Y_TOT + 5, f'{total_ch:.2f}', sz=8, bold=True, align='r')

    # ── 6. DIFERENȚE ──────────────────────────────────────────────────────────
    Y_DIF = Y_TOT + 7
    d.box(ML, Y_DIF, W, 13, lw=1.0)
    d.vline(MID, Y_DIF, Y_DIF + 13, lw=0.5)

    d.t(ML + 1, Y_DIF + 4.5,  'Diferența de restituit s-a depus cu', sz=6)
    d.t(ML + 1, Y_DIF + 8.5,  'dispoziție de încasare către casierie', sz=6)
    d.t(ML + 1, Y_DIF + 12.5, 'Nr.', sz=6)
    d.hline(ML + 9, ML + 28, Y_DIF + 13, lw=0.3)
    d.t(ML + 29, Y_DIF + 12.5, 'din', sz=6)
    d.hline(ML + 35, MID - 1, Y_DIF + 13, lw=0.3)

    tip = g('diferenta_tip') or 'primit'
    val_dif = gf('diferenta_val')
    d.t(MID + 2, Y_DIF + 5,  'Diferența de', sz=6.5)
    d.t(MID + 2, Y_DIF + 10, tip,            sz=7, bold=True)
    d.hline(MID + 2, MR - 9, Y_DIF + 13, lw=0.3)
    d.t(MR - 8, Y_DIF + 12.5, 'lei', sz=6.5)
    if val_dif:
        d.t(MR - 9, Y_DIF + 12, f'{val_dif:.2f}', sz=8, align='r')

    # ── 7. SEMNĂTURI ──────────────────────────────────────────────────────────
    Y_SGN = Y_DIF + 13
    SGN_H = 16
    semn = [
        'Aprobat\nconductorul\nunității',
        'Control financiar\npreventiv',
        'Verificat\ndecont',
        'Șef\ncompartiment',
        'Titular\navans',
    ]
    cel_w = W / len(semn)

    d.box(ML, Y_SGN, W, SGN_H, lw=1.0)
    for i, label in enumerate(semn):
        xc = ML + i * cel_w
        if i > 0:
            d.vline(xc, Y_SGN, Y_SGN + SGN_H, lw=0.5)
        cx = xc + cel_w / 2
        for j, linie in enumerate(label.split('\n')):
            d.t(cx, Y_SGN + 4 + j * 3.8, linie, sz=5.5, align='c')


# ── Entry point ───────────────────────────────────────────────────────────────

def generate_pdf(data) -> bytes:
    """Generează PDF A5, 2 pagini (față + verso)."""
    buf = BytesIO()
    c = Canvas(buf, pagesize=A5)

    _p1(D(c), data)
    c.showPage()
    _p2(D(c), data)
    c.showPage()

    c.save()
    buf.seek(0)
    return buf.read()
