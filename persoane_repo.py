# Copie locală a repository-ului comun. Baza este deschisă exclusiv în mode=ro.
import os
import re
import sqlite3
import unicodedata
from pathlib import Path

DB_PATH = os.environ.get("PERSOANE_DB_PATH", r"C:\DevTools\_comun\persoane.db")
CAMPURI_TOATE = ("marca", "srtfc", "nume", "initiala_tata", "prenume", "nume_afisare",
                 "functie", "loc_munca", "este_tesa", "email", "telefon_ad", "mobil_ad",
                 "ad_cont", "status")

def _conectare():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Baza comună de persoane nu există: {DB_PATH}")
    conn = sqlite3.connect(Path(DB_PATH).resolve().as_uri() + "?mode=ro", uri=True, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def _cheie(text):
    text = unicodedata.normalize("NFKD", str(text or ""))
    text = "".join(c for c in text if not unicodedata.combining(c)).upper()
    return re.sub(r"[^A-Z0-9]", "", text)

def _campuri(conn):
    existente = {c[1] for c in conn.execute("PRAGMA table_info(persoane)")}
    return [c for c in CAMPURI_TOATE if c in existente]

def _dict(row):
    if not row:
        return None
    d = dict(row)
    return {k: d.get(k) for k in CAMPURI_TOATE}

def get_persoana(marca):
    with _conectare() as conn:
        row = conn.execute(f"SELECT {', '.join(_campuri(conn))} FROM persoane WHERE marca = ?", (marca,)).fetchone()
    return _dict(row)

def list_persoane(doar_active=True, srtfc=None):
    params, sql = [], "WHERE 1=1"
    if doar_active:
        sql += " AND status = 'activ'"
    if srtfc:
        sql += " AND srtfc = ?"
        # Codul stabil al aplicațiilor este IS; în baza existentă valoarea este Iași.
        params.append("Iași" if str(srtfc).upper() == "IS" else srtfc)
    sql += " ORDER BY nume_afisare"
    with _conectare() as conn:
        rows = conn.execute(f"SELECT {', '.join(_campuri(conn))} FROM persoane " + sql, params)
        return [_dict(r) for r in rows]

def cauta_persoana(text, doar_active=True, limita=50, srtfc=None):
    """Caută după nume sau funcție, opțional limitat strict la o regională."""
    cuvinte = [_cheie(w) for w in str(text or "").split() if _cheie(w)]
    if not cuvinte:
        return []
    rezultat = []
    for p in list_persoane(doar_active=doar_active, srtfc=srtfc):
        tinta = _cheie(p["nume_afisare"]) + "|" + _cheie(p["functie"])
        if all(c in tinta for c in cuvinte):
            rezultat.append(p)
            if len(rezultat) >= limita:
                break
    return rezultat
