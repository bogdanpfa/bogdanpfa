import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

VERSION = "2.1.0"

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-local-secret")
    PERSOANE_DB_PATH = os.getenv("PERSOANE_DB_PATH", r"C:\DevTools\_comun\persoane.db")
    SRTFC_CODE = "IS"
    BENEFICIAR_NUME = os.getenv("BENEFICIAR_NUME", "Bogdan PĂVĂLUC")
    BENEFICIAR_FUNCTIE = os.getenv("BENEFICIAR_FUNCTIE", "Economist I")
    COMPANIE = os.getenv("COMPANIE", "SNTFC CFR Călători SA")
    NR_PREFIX = os.getenv("NR_PREFIX", "IS 6/7")
