# ============================================================
# persoane_repo.py — CITIRE din baza comună de Persoane
# Versiune: 1.1.0 (2026-10-06) — + telefon_ad, mobil_ad, ad_cont
#
# Se COPIAZĂ identic în fiecare aplicație care are nevoie de
# persoane (TonerBox, Stoc etc.). Originalul: C:\DevTools\_comun\
#
# DOAR CITIRE — baza se deschide read-only, orice încercare de
# scriere dă eroare. Modificările se fac numai din Agenda (5005).
#
# În .env-ul aplicației:
#   PERSOANE_DB_PATH=C:\DevTools\_comun\persoane.db
#
# Exemplu:
#   import persoane_repo as pr
#   pr.get_persoana("IS-000048")      -> dict sau None
#   pr.list_persoane()                -> doar active
#   pr.cauta_persoana("popa dan")     -> potriviri fără diacritice
# ============================================================

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
    """Conexiune DOAR CITIRE (mode=ro). Eroare clară dacă baza lipsește."""
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Baza comună de persoane nu există: {DB_PATH}")
    conn = sqlite3.connect(Path(DB_PATH).resolve().as_uri() + "?mode=ro", uri=True, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def _cheie(text):
    """„Popa Dan” / „POPĂ DAN” -> „POPADAN” (fără diacritice, fără spații)."""
    text = unicodedata.normalize("NFKD", str(text or ""))
    text = "".join(c for c in text if not unicodedata.combining(c)).upper()
    return re.sub(r"[^A-Z0-9]", "", text)


def _campuri(conn):
    """Doar câmpurile care există în bază (merge și cu o bază mai veche, fără coloanele AD)."""
    existente = {c[1] for c in conn.execute("PRAGMA table_info(persoane)")}
    return [c for c in CAMPURI_TOATE if c in existente]


def _dict(row):
    if not row:
        return None
    d = dict(row)
    return {k: d.get(k) for k in CAMPURI_TOATE}


def get_persoana(marca):
    """O persoană după marcă (orice status), sau None."""
    with _conectare() as conn:
        row = conn.execute(f"SELECT {', '.join(_campuri(conn))} FROM persoane WHERE marca = ?",
                           (marca,)).fetchone()
    return _dict(row)


def list_persoane(doar_active=True, srtfc=None):
    """Lista persoanelor, ordonată după nume. Implicit doar cele active."""
    params = []
    sql = "WHERE 1=1"
    if doar_active:
        sql += " AND status = 'activ'"
    if srtfc:
        sql += " AND srtfc = ?"
        params.append(srtfc)
    sql += " ORDER BY nume_afisare"
    with _conectare() as conn:
        sql = f"SELECT {', '.join(_campuri(conn))} FROM persoane " + sql
        return [_dict(r) for r in conn.execute(sql, params)]


def cauta_persoana(text, doar_active=True, limita=50):
    """
    Caută după nume sau funcție; fiecare cuvânt trebuie să se regăsească
    („dan popa” = „popa dan”). Fără diacritice.
    """
    cuvinte = [_cheie(w) for w in str(text or "").split() if _cheie(w)]
    if not cuvinte:
        return []
    rezultat = []
    for p in list_persoane(doar_active=doar_active):
        tinta = _cheie(p["nume_afisare"]) + "|" + _cheie(p["functie"])
        if all(c in tinta for c in cuvinte):
            rezultat.append(p)
            if len(rezultat) >= limita:
                break
    return rezultat
