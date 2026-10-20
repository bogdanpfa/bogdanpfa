"""Configurare centrală — Audit Rețea SRTFC Iași.

Versiunea se citește DOAR de aici (afișată în footer și în manual).
Valorile pot fi suprascrise prin variabile de mediu, fără modificarea codului.
"""
import os
import sys

VERSION = '1.4.0'
APP_NAME = 'Audit Rețea SRTFC Iași'
# Autorul — afișat în subsolul tuturor paginilor și în manual
AUTOR = 'Bogdan PĂVĂLUC'
SERVICIU = 'Serviciul OTD & IT SRTFC Iași'
# Mențiunea de pe documentele generate (pagini tipărite, Excel)
TEXT_GENERAT = 'Raport generat de Audit Rețea SRTFC Iași'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# instance/ conține baza de date, cheia de sesiune și backup-urile — nu intră în git
INSTANCE_DIR = os.environ.get('AUDIT_INSTANCE', os.path.join(BASE_DIR, 'instance'))

PORT = int(os.environ.get('AUDIT_PORT', '5009'))
# Butonul „Acasă": portalul intern. Gol = același server, portul 80 (pagina iisstart.htm)
PORTAL_URL = os.environ.get('AUDIT_PORTAL_URL', '')
HOST = os.environ.get('AUDIT_HOST', '0.0.0.0')

# Domeniul Active Directory
DOMAIN_NETBIOS = os.environ.get('AUDIT_DOMAIN', 'CALATORI')
DOMAIN_DNS = os.environ.get('AUDIT_DOMAIN_DNS', 'calatori.local')

# Motorul PowerShell (derivat din Audit_Retea_v6.ps1)
ENGINE_SCRIPT = os.path.join(BASE_DIR, 'engine', 'audit_engine.ps1')
POWERSHELL_EXE = os.environ.get('AUDIT_POWERSHELL', 'powershell.exe')
IS_WINDOWS = sys.platform == 'win32'

# Limite de autentificare în aplicație.
# Conturile AD: maxim 2 încercări greșite, apoi blocare în aplicație —
# astfel aplicația nu poate atinge niciodată pragul de 3 din domeniu.
MAX_INCERCARI_LOCAL = 5
MAX_INCERCARI_AD = 2
BLOCARE_MINUTE = 15

# Valori implicite pentru setări (modificabile din pagina Setări)
SETARI_IMPLICITE = {
    'timeout_sec': '15',        # ca în v6 — protejează rețeaua și contul
    'delay_ms': '250',          # pauză între IP-uri
    'licente': '0',             # interogare licență Windows (lentă)
    'retentie_luni': '12',      # istoricul scanărilor (GDPR — utilizatorul logat e dată personală)
    'prag_spatiu_c_gb': '10',
    'zile_fantoma': '60',
    # SNMP (imprimante și echipamente de rețea)
    'snmp': '1',
    'snmp_community': 'public',
    # Reguli implicite pentru „stare parc" și „necesar piese" (modificabile din pagină)
    'ram_tinta_gb': '8',
    'ssd_gb': '256',
    'prag_disc_mic_gb': '128',
    'prag_toner': '15',
    'vechime_ani': '8',
    # Acces: doar membrii grupurilor AD (conturile locale rămân permise, ca rezervă)
    'acces_doar_grup': '0',
    'grupuri_ad_acces': 'Domain Admins',
    'rol_grup': 'admin',
}
