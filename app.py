import os
from datetime import date
from pathlib import Path
from flask import Flask, jsonify, render_template, request, send_file
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")
from config import Config, OUTPUT_DIR

os.environ.setdefault("PERSOANE_DB_PATH", Config.PERSOANE_DB_PATH)
import persoane_repo as persoane
from generators.pdf_generator import create_pdf

app = Flask(__name__)
app.config.from_object(Config)

@app.get("/")
def index():
    return render_template("formular.html", settings={
        "beneficiar_nume": Config.BENEFICIAR_NUME, "beneficiar_functie": Config.BENEFICIAR_FUNCTIE,
        "companie": Config.COMPANIE, "nr_prefix": Config.NR_PREFIX, "today": date.today().isoformat()})

@app.get("/api/persoane")
def search_people():
    text = request.args.get("q", "").strip()
    if len(text) < 2: return jsonify([])
    try:
        return jsonify(persoane.cauta_persoana(text, srtfc=Config.SRTFC_CODE, limita=20))
    except FileNotFoundError as exc:
        return jsonify({"error": str(exc)}), 503

@app.get("/api/persoane/<marca>")
def get_person(marca):
    try:
        person = persoane.get_persoana(marca)
    except FileNotFoundError as exc:
        return jsonify({"error": str(exc)}), 503
    if not person or person.get("srtfc") not in (Config.SRTFC_CODE, "Iași"):
        return jsonify({"error":"Persoana nu este disponibilă pentru SRTFC Iași."}), 404
    return jsonify(person)

@app.post("/api/pdf")
def pdf():
    data = request.get_json(silent=True) or {}
    if not data.get("numar_manual") or not str(data.get("numar_inregistrare", "")).strip():
        return jsonify({"error":"Activați numărul manual și completați numărul de înregistrare."}), 400
    if not (data.get("telefon_cfr") or data.get("telefon_fix") or data.get("mobil") or data.get("telefon_ip") or data.get("fax_cfr")):
        return jsonify({"error":"Completați cel puțin un număr de telefon."}), 400
    data.update({"beneficiar_nume": Config.BENEFICIAR_NUME, "beneficiar_functie": Config.BENEFICIAR_FUNCTIE,
                 "companie": data.get("companie") or Config.COMPANIE, "nr_prefix": Config.NR_PREFIX})
    safe_name = "".join(c for c in f"Comanda_{data.get('numar_inregistrare')}_{data.get('nume','').strip()}" if c.isalnum() or c in "_-")
    target = OUTPUT_DIR / f"{safe_name or 'comanda_servicii'}.pdf"
    create_pdf(data, target)
    return send_file(target, as_attachment=True, download_name=target.name, mimetype="application/pdf")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5006, debug=True)
