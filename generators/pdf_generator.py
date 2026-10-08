"""Completează modelul aprobat CSS prin suprapunerea datelor peste PDF-ul lui original."""
from io import BytesIO
from pathlib import Path
from reportlab.lib.colors import HexColor, white
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter

FONT_DIR = Path(r"C:\Windows\Fonts")
pdfmetrics.registerFont(TTFont("CambriaForm", str(FONT_DIR / "cambria.ttc"), subfontIndex=0))
BASE_DIR = Path(__file__).resolve().parents[1]
TEMPLATE = BASE_DIR / "templates" / "css_model.pdf"
FIELD_COLOR = HexColor("#c00000")

def _text(c, value, x, y, size=10, color=FIELD_COLOR, max_chars=58):
    value = str(value or "").strip().replace("\n", " ")[:max_chars]
    if value:
        c.setFillColor(color); c.setFont("CambriaForm", size); c.drawString(x, y, value)

def _mark(c, active, x, y):
    c.setFillColor(white); c.rect(x-1, y-2, 11, 11, stroke=0, fill=1)
    if active:
        c.setFillColor(HexColor("#000000")); c.setFont("CambriaForm", 11); c.drawString(x, y, "X")

def create_pdf(data, destination: Path):
    if not TEMPLATE.exists(): raise FileNotFoundError(f"Lipsește modelul PDF: {TEMPLATE}")
    overlay = BytesIO(); c = canvas.Canvas(overlay, pagesize=(595.276,841.89))
    _text(c,data.get("numar_inregistrare"),318,763,10,HexColor("#000000"),20); _text(c,data.get("data"),347,763,10,HexColor("#000000"),12)
    for key,x,y,size,limit in [("nume",150,680,10,25),("initiala_tata",294,680,10,4),("prenume",217,665,10,30),("companie",197,650,10,42),("functie",187,635,10,42),("loc_munca",127,620,10,55),("departament",343,589,10,27),("sef_direct",186,572,10,48),("cladire",144,544,10,16),("etaj",257,544,10,16),("camera",395,544,10,16),("telefon_cfr",143,516,10,15),("telefon_fix",273,516,10,18),("mobil",145,501,10,18),("telefon_ip",280,501,10,20),("fax_cfr",421,501,10,16),("alte_detalii",154,480,9,78)]: _text(c,data.get(key),x,y,size,max_chars=limit)
    for value,x in [("Central",154),("Regional",218),("Unitate",309)]: _mark(c,data.get("tip_locatie")==value,x,604)
    op=data.get("operatiune")
    for value,x in [("Nou",109),("Transferat",180),("Modificări",261),("Ștergere utilizator",388)]: _mark(c,op==value,x,712)
    services=set(data.get("servicii") or [])
    for value,x,y in [("Adăugare",130,444),("Ștergere",214,444),("ASP-R",228,423),("RENTRAD",189,408),("Internet",289,408),("E-Mail",371,408),("Legis",463,408),("Suport tehnic",143,393),("Alte servicii",143,378)]: _mark(c,value in services,x,y)
    _text(c,data.get("aspr_detalii"),236,423,10,max_chars=42); _text(c,data.get("suport_detalii"),160,393,10,max_chars=60); _text(c,data.get("alte_servicii"),160,378,10,max_chars=60)
    c.setFillColor(white); c.rect(140,250,160,56,stroke=0,fill=1)
    _text(c,data.get("beneficiar_nume"),155,273,11,HexColor("#000000"),27); _text(c,data.get("beneficiar_functie"),155,253,11,HexColor("#000000"),27); _text(c,data.get("data"),155,211,10,HexColor("#000000"),22); c.save()
    base=PdfReader(str(TEMPLATE)); base.pages[0].merge_page(PdfReader(overlay).pages[0]); writer=PdfWriter(); writer.add_page(base.pages[0])
    with open(destination,"wb") as stream: writer.write(stream)
