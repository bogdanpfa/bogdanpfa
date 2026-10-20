"""Autentificare, roluri și protecție CSRF.

Două tipuri de conturi:
  - 'ad'    : colegii intră cu contul de domeniu CALATORI; parola e verificată
              de Windows (LogonUser) — aplicația nu stochează parola
  - 'local' : parolă hash-uită în baza de date (contul de rezervă al super-adminului)

Doar utilizatorii adăugați de super-admin pot intra (listă albă).
"""
import ctypes
import functools
import secrets
from datetime import datetime, timedelta

from flask import abort, flash, g, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

import config
from .db import acum, get_db, jurnal

ROLURI = {
    'superadmin': 'Super-administrator',
    'admin': 'Administrator (scanare)',
    'vizualizare': 'Doar vizualizare',
}
NIVEL_ROL = {'vizualizare': 1, 'admin': 2, 'superadmin': 3}


# -- Verificare parolă de domeniu ----------------------------------------------

# Coduri Win32 întoarse de LogonUserW
_ERORI_LOGON = {
    1326: 'Utilizator sau parolă incorectă.',
    1909: 'Contul este blocat în domeniu. Contactați administratorul AD.',
    1330: 'Parola de domeniu a expirat. Schimbați-o din Windows, apoi reveniți.',
    1907: 'Parola trebuie schimbată la următoarea logare în Windows.',
    1331: 'Contul este dezactivat în domeniu.',
    1793: 'Contul a expirat în domeniu.',
    1311: 'Nu există niciun controller de domeniu disponibil.',
    1327: 'Restricție de cont (ore de logare, stații permise sau parolă goală).',
    1385: 'Contului nu i s-a acordat dreptul de logare prin rețea pe acest server.',
    1792: 'Serviciul Netlogon nu rulează pe server (serverul e membru în domeniu?).',
    1789: 'Relația de încredere dintre server și domeniu a eșuat (serverul trebuie reintrodus în domeniu).',
}


def _sid_grup(advapi32, nume):
    """SID-ul unui grup AD după nume („Domain Admins“ sau „CALATORI\\Grup“); None dacă nu există."""
    from ctypes import wintypes
    if '\\' not in nume:
        nume = f'{config.DOMAIN_NETBIOS}\\{nume}'
    sid = ctypes.create_string_buffer(256)
    cb = wintypes.DWORD(256)
    dom = ctypes.create_unicode_buffer(256)
    cch = wintypes.DWORD(256)
    tip = wintypes.DWORD()
    if not advapi32.LookupAccountNameW(None, wintypes.LPCWSTR(nume), sid, ctypes.byref(cb), dom,
                                       ctypes.byref(cch), ctypes.byref(tip)):
        return None
    return sid


def rezolva_grupuri(grupuri):
    """(găsite, negăsite) — folosit la salvarea setărilor, ca un nume greșit să nu blocheze pe toată lumea."""
    if not config.IS_WINDOWS:
        return list(grupuri), []
    advapi32 = ctypes.WinDLL('advapi32', use_last_error=True)
    gasite, negasite = [], []
    for g in grupuri:
        (gasite if _sid_grup(advapi32, g) is not None else negasite).append(g)
    return gasite, negasite


def verifica_parola_ad(username, parola, grupuri=None):
    """Întoarce (ok, mesaj_eroare, cod, grupuri_membru). Folosește LogonUserW (logon de rețea),
    deci parola nu circulă în clar spre controller-ul de domeniu. Dacă se dau grupuri, verifică
    apartenența (inclusiv prin grupuri imbricate) pe token-ul obținut."""
    if not config.IS_WINDOWS:
        return False, 'Autentificarea de domeniu funcționează doar pe serverul Windows.', None, []
    from ctypes import wintypes
    LOGON32_LOGON_NETWORK = 3
    LOGON32_PROVIDER_DEFAULT = 0
    advapi32 = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    token = wintypes.HANDLE()
    ok = advapi32.LogonUserW(wintypes.LPCWSTR(username), wintypes.LPCWSTR(config.DOMAIN_NETBIOS),
                             wintypes.LPCWSTR(parola), LOGON32_LOGON_NETWORK,
                             LOGON32_PROVIDER_DEFAULT, ctypes.byref(token))
    if ok:
        membru = []
        try:
            for g in grupuri or []:
                sid = _sid_grup(advapi32, g)
                este = wintypes.BOOL()
                if sid is not None and advapi32.CheckTokenMembership(token, sid, ctypes.byref(este)) and este.value:
                    membru.append(g)
        finally:
            kernel32.CloseHandle(token)
        return True, '', 0, membru
    cod = ctypes.get_last_error()
    return False, _ERORI_LOGON.get(cod, f'Autentificare de domeniu eșuată (cod {cod}).'), cod, []


# -- Utilizatori -----------------------------------------------------------------

def normalizeaza_username(username):
    """'CALATORI\\ion.pop' sau 'ion.pop@calatori.local' -> 'ion.pop'"""
    u = (username or '').strip()
    if '\\' in u:
        u = u.split('\\', 1)[1]
    if '@' in u:
        u = u.split('@', 1)[0]
    return u.lower()


def creeaza_utilizator(conn, username, nume, rol, tip_auth, parola=None):
    if rol not in ROLURI or tip_auth not in ('local', 'ad'):
        raise ValueError('Rol sau tip de autentificare invalid.')
    if tip_auth == 'local' and not parola:
        raise ValueError('Contul local necesită o parolă.')
    if parola is not None:
        valideaza_parola_noua(parola)
    conn.execute(
        'INSERT INTO utilizatori (username, nume, rol, tip_auth, parola_hash, creat_la) VALUES (?, ?, ?, ?, ?, ?)',
        (normalizeaza_username(username), nume.strip(), rol, tip_auth,
         generate_password_hash(parola) if parola else None, acum()))
    conn.commit()


def valideaza_parola_noua(parola):
    if len(parola) < 10:
        raise ValueError('Parola trebuie să aibă minim 10 caractere.')


def seteaza_parola_locala(conn, user_id, parola):
    valideaza_parola_noua(parola)
    conn.execute('UPDATE utilizatori SET parola_hash = ?, incercari_esuate = 0, blocat_pana = NULL WHERE id = ?',
                 (generate_password_hash(parola), user_id))
    conn.commit()


# Încercări eșuate pentru conturi încă necunoscute aplicației (mod „grup AD“): în memorie,
# ca nimeni să nu poată folosi pagina de login pentru a bloca un cont în domeniu.
_incercari_noi = {}


def _blocat_nou(username):
    acum_ts = datetime.now()
    lista = [t for t in _incercari_noi.get(username, []) if acum_ts - t < timedelta(minutes=config.BLOCARE_MINUTE)]
    _incercari_noi[username] = lista
    return len(lista) >= config.MAX_INCERCARI_AD


def setari_acces():
    from .db import get_setare
    grupuri = [g.strip() for g in (get_setare('grupuri_ad_acces') or '').split(',') if g.strip()]
    return get_setare('acces_doar_grup') == '1' and bool(grupuri), grupuri, get_setare('rol_grup') or 'admin'


def autentifica(username, parola):
    """Întoarce (user_row, None) la succes sau (None, mesaj)."""
    conn = get_db()
    username = normalizeaza_username(username)
    mesaj_generic = 'Utilizator sau parolă incorectă, ori contul nu are acces la aplicație.'
    doar_grup, grupuri, rol_grup = setari_acces()
    mesaj_grup = 'Accesul e permis doar administratorilor (membri ai grupului AD: ' + ', '.join(grupuri) + ').'
    user = conn.execute('SELECT * FROM utilizatori WHERE username = ?', (username,)).fetchone()

    # Cont necunoscut: orice utilizator AD cu credențiale corecte primește acces automat la prima logare.
    # Dacă sunt configurate grupuri în setări, trebuie să fie și membru.
    if user is None and username:
        if _blocat_nou(username):
            return None, f'Prea multe încercări greșite. Reîncercți peste {config.BLOCARE_MINUTE} minute.'
        ok, eroare, cod, membru = verifica_parola_ad(username, parola, grupuri if grupuri else None)
        if not ok:
            _incercari_noi.setdefault(username, []).append(datetime.now())
            jurnal('login_esuat', f'{username} (ad, cont nou) cod {cod}', utilizator=username)
            return None, eroare
        if grupuri and not membru:
            jurnal('login_refuzat', f'{username}: nu e membru în {", ".join(grupuri)}', utilizator=username)
            return None, mesaj_grup
        rol_auto = rol_grup if grupuri else 'admin'
        creeaza_utilizator(conn, username, username, rol_auto, 'ad')
        jurnal('utilizator_auto', f'{username} rol {rol_auto} (AD)', utilizator=username)
        user = conn.execute('SELECT * FROM utilizatori WHERE username = ?', (username,)).fetchone()
        conn.execute('UPDATE utilizatori SET ultima_logare = ? WHERE id = ?', (acum(), user['id']))
        conn.commit()
        return user, None

    if user is None or not user['activ']:
        jurnal('login_esuat', f'utilizator necunoscut/inactiv: {username}', utilizator=username)
        return None, mesaj_generic

    if user['blocat_pana'] and user['blocat_pana'] > acum():
        return None, f'Prea multe încercări greșite. Contul e blocat în aplicație până la {user["blocat_pana"][11:16]}.'

    membru = None
    if user['tip_auth'] == 'ad':
        ok, eroare, cod, membru = verifica_parola_ad(username, parola, grupuri if doar_grup else None)
    else:
        ok = bool(user['parola_hash']) and check_password_hash(user['parola_hash'], parola)
        eroare, cod = mesaj_generic, None

    if not ok:
        incercari = user['incercari_esuate'] + 1
        limita = config.MAX_INCERCARI_AD if user['tip_auth'] == 'ad' else config.MAX_INCERCARI_LOCAL
        blocat = None
        if incercari >= limita:
            blocat = (datetime.now() + timedelta(minutes=config.BLOCARE_MINUTE)).replace(microsecond=0).isoformat(sep=' ')
            incercari = 0
        conn.execute('UPDATE utilizatori SET incercari_esuate = ?, blocat_pana = ? WHERE id = ?',
                     (incercari, blocat, user['id']))
        conn.commit()
        jurnal('login_esuat', f'{username} ({user["tip_auth"]}){" cod " + str(cod) if cod else ""}', utilizator=username)
        if blocat:
            return None, (f'Prea multe încercări greșite. Accesul e blocat {config.BLOCARE_MINUTE} minute '
                          '(protecție pentru contul de domeniu).')
        return None, eroare

    # Parola e corectă, dar în modul „grup AD“ contul de domeniu trebuie să fie și administrator.
    # Conturile locale (ex. rezerva super-adminului) rămân permise.
    if user['tip_auth'] == 'ad' and doar_grup and not membru:
        conn.execute('UPDATE utilizatori SET incercari_esuate = 0 WHERE id = ?', (user['id'],))
        conn.commit()
        jurnal('login_refuzat', f'{username}: nu e membru în {", ".join(grupuri)}', utilizator=username)
        return None, mesaj_grup

    conn.execute('UPDATE utilizatori SET incercari_esuate = 0, blocat_pana = NULL, ultima_logare = ? WHERE id = ?',
                 (acum(), user['id']))
    conn.commit()
    return user, None


def incarca_utilizator_curent():
    g.user = None
    uid = session.get('user_id')
    if uid:
        user = get_db().execute('SELECT * FROM utilizatori WHERE id = ? AND activ = 1', (uid,)).fetchone()
        if user is None:
            session.clear()
        else:
            g.user = user


def are_rol(minim):
    return g.get('user') is not None and NIVEL_ROL[g.user['rol']] >= NIVEL_ROL[minim]


def necesita_rol(minim='vizualizare'):
    """Decorator: rutele cer autentificare și un rol minim."""
    def decorator(view):
        @functools.wraps(view)
        def wrapped(*args, **kwargs):
            if g.get('user') is None:
                return redirect(url_for('main.login', next=request.full_path))
            if not are_rol(minim):
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


# -- CSRF (fără dependențe externe) ---------------------------------------------

def csrf_token():
    if '_csrf' not in session:
        session['_csrf'] = secrets.token_urlsafe(32)
    return session['_csrf']


def verifica_csrf():
    if request.method in ('GET', 'HEAD', 'OPTIONS'):
        return
    trimis = request.form.get('_csrf') or request.headers.get('X-CSRF-Token', '')
    if not trimis or not secrets.compare_digest(trimis, session.get('_csrf', '')):
        flash('Sesiunea a expirat sau formularul e invalid. Reîncercți.', 'eroare')
        abort(400)
