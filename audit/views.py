"""Paginile aplicației."""
import re
from datetime import datetime

from flask import (Blueprint, Response, abort, flash, g, jsonify, redirect, render_template, request,
                   session, url_for)

import config
from . import analiza, auth, csvio, secret_store
from .db import CAMPURI_DISPOZITIV, acum, get_db, get_setare, get_setare_int, jurnal, set_setare
from .scanner import manager

bp = Blueprint('main', __name__)

RE_PREFIX = re.compile(r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})$')
ZILE = [('1', 'Luni'), ('2', 'Marți'), ('3', 'Miercuri'), ('4', 'Joi'), ('5', 'Vineri'), ('6', 'Sâmbătă'), ('7', 'Duminică')]
STARI = {'in_asteptare': 'În așteptare', 'ruleaza': 'Rulează', 'finalizat': 'Finalizată',
         'oprit': 'Oprită', 'eroare': 'Eroare'}


@bp.app_template_filter('stare')
def _filtru_stare(v):
    return STARI.get(v, v)


@bp.app_template_filter('data')
def _filtru_data(v):
    """'2026-10-19 14:05:00' -> '19.10.2026 14:05'"""
    if not v:
        return ''
    try:
        return datetime.fromisoformat(v).strftime('%d.%m.%Y %H:%M')
    except ValueError:
        return v


def valideaza_interval(prefix, start, end):
    """Întoarce (prefix, start, end) curate sau aruncă ValueError cu mesaj în română."""
    prefix = (prefix or '').strip()
    m = RE_PREFIX.match(prefix)
    if not m or any(int(x) > 255 for x in m.groups()):
        raise ValueError('Prefix IP invalid. Format: 172.26.65')
    try:
        start, end = int(start), int(end)
    except (TypeError, ValueError):
        raise ValueError('Intervalul IP trebuie să fie numeric.')
    if not (1 <= start <= end <= 254):
        raise ValueError('Interval invalid: între 1 și 254, iar „de la“ ≤ „până la“.')
    return prefix, start, end


def _scanare_sau_404(sid):
    s = get_db().execute('SELECT * FROM scanari WHERE id = ?', (sid,)).fetchone()
    if s is None:
        abort(404)
    return s


# -- Autentificare ------------------------------------------------------------------

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if g.user:
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        user, eroare = auth.autentifica(request.form.get('username', ''), request.form.get('password', ''))
        if user:
            session.clear()
            session.permanent = True
            session['user_id'] = user['id']
            session['username'] = user['username']
            jurnal('login', f'{user["username"]} ({user["tip_auth"]})', utilizator=user['username'])
            urmator = request.args.get('next', '')
            # doar căi interne (fără redirect spre alte site-uri)
            if not urmator.startswith('/') or urmator.startswith('//'):
                urmator = url_for('main.index')
            return redirect(urmator)
        flash(eroare, 'eroare')
    return render_template('login.html', domeniu=config.DOMAIN_NETBIOS)


@bp.route('/logout', methods=['POST'])
def logout():
    if g.user:
        jurnal('logout', g.user['username'])
    session.clear()
    return redirect(url_for('main.login'))


@bp.route('/cont', methods=['GET', 'POST'])
@auth.necesita_rol('vizualizare')
def cont():
    if request.method == 'POST':
        if g.user['tip_auth'] != 'local':
            abort(400)
        db = get_db()
        from werkzeug.security import check_password_hash
        if not check_password_hash(g.user['parola_hash'] or '', request.form.get('parola_veche', '')):
            flash('Parola actuală nu este corectă.', 'eroare')
        elif request.form.get('parola_noua') != request.form.get('parola_confirmare'):
            flash('Parolele noi nu coincid.', 'eroare')
        else:
            try:
                auth.seteaza_parola_locala(db, g.user['id'], request.form.get('parola_noua', ''))
                jurnal('parola_schimbata', g.user['username'])
                flash('Parola a fost schimbată.', 'succes')
                return redirect(url_for('main.cont'))
            except ValueError as exc:
                flash(str(exc), 'eroare')
    return render_template('cont.html')


# -- Panou principal ------------------------------------------------------------------

@bp.route('/')
@auth.necesita_rol('vizualizare')
def index():
    db = get_db()
    active = db.execute("SELECT * FROM scanari WHERE stare IN ('ruleaza', 'in_asteptare') ORDER BY id").fetchall()
    recente = db.execute('SELECT * FROM scanari ORDER BY id DESC LIMIT 8').fetchall()
    # ultima scanare reușită pentru fiecare subnet (prefix + interval)
    ultimele = db.execute(
        "SELECT s.* FROM scanari s JOIN (SELECT prefix, ip_start, ip_end, MAX(id) AS mid FROM scanari "
        "WHERE stare IN ('finalizat', 'oprit') GROUP BY prefix, ip_start, ip_end) u ON u.mid = s.id "
        "ORDER BY s.prefix, s.ip_start").fetchall()
    ids = [s['id'] for s in ultimele]
    dispozitive = []
    if ids:
        dispozitive = db.execute(f'SELECT * FROM dispozitive WHERE scanare_id IN ({",".join("?" * len(ids))})',
                                 ids).fetchall()
    prag = get_setare_int('prag_spatiu_c_gb')
    sumar = analiza.sumar_alerte(dispozitive, prag)
    total = {k: sum(s[k] for s in ultimele) for k in ('online', 'offline', 'refuzat', 'ssd', 'hdd', 'imprimante')}
    programari = db.execute('SELECT p.*, s.nume FROM programari p JOIN subneturi s ON s.id = p.subnet_id '
                            'WHERE p.activ = 1 ORDER BY p.ora').fetchall()
    return render_template('index.html', active=active, recente=recente, ultimele=ultimele, sumar=sumar,
                           total=total, programari=programari, ZILE=dict(ZILE))


# -- Scanări ---------------------------------------------------------------------------

@bp.route('/scanare/noua', methods=['GET', 'POST'])
@auth.necesita_rol('admin')
def scanare_noua():
    db = get_db()
    subneturi = db.execute('SELECT * FROM subneturi ORDER BY nume').fetchall()
    cont_programat = get_setare('cont_programat_user')
    are_cont_salvat = bool(cont_programat and get_setare('cont_programat_parola'))
    if request.method == 'POST':
        f = request.form
        try:
            subnet_id = int(f['subnet_id']) if f.get('subnet_id') else None
            if subnet_id:
                sub = db.execute('SELECT * FROM subneturi WHERE id = ?', (subnet_id,)).fetchone()
                if sub is None:
                    raise ValueError('Subnetul ales nu mai există.')
                prefix, start, end = sub['prefix'], sub['ip_start'], sub['ip_end']
                eticheta = sub['nume']
            else:
                prefix, start, end = valideaza_interval(f.get('prefix'), f.get('ip_start'), f.get('ip_end'))
                eticheta = (f.get('eticheta') or '').strip() or prefix
                # opțional: intervalul introdus manual se salvează ca subnet, pentru data viitoare
                if f.get('salveaza_subnet'):
                    if not (f.get('eticheta') or '').strip():
                        raise ValueError('Pentru a salva intervalul, completați „Denumire“.')
                    existent = db.execute('SELECT id FROM subneturi WHERE prefix = ? AND ip_start = ? AND ip_end = ?',
                                          (prefix, start, end)).fetchone()
                    if existent:
                        subnet_id = existent['id']
                    else:
                        subnet_id = db.execute('INSERT INTO subneturi (nume, prefix, ip_start, ip_end) VALUES (?, ?, ?, ?)',
                                               (eticheta, prefix, start, end)).lastrowid
                        db.commit()
                        jurnal('subnet_adaugat', f'{eticheta} {prefix}.{start}-{end} (din scanare nouă)')
            if f.get('cont') == 'salvat':
                if not are_cont_salvat:
                    raise ValueError('Nu există un cont de scanare salvat.')
                utilizator_scanare = cont_programat
                parola = secret_store.descifreaza(get_setare('cont_programat_parola'))
            else:
                utilizator_scanare = auth.normalizeaza_username(f.get('cont_user'))
                parola = f.get('cont_parola', '')
                if not utilizator_scanare or not parola:
                    raise ValueError('Introduceți utilizatorul și parola de administrator AD.')
            if db.execute("SELECT 1 FROM scanari WHERE prefix = ? AND ip_start = ? AND ip_end = ? "
                          "AND stare IN ('in_asteptare', 'ruleaza')", (prefix, start, end)).fetchone():
                raise ValueError(f'Există deja o scanare activă sau în coadă pentru {prefix}.{start}-{end}.')
        except (ValueError, secret_store.SecretIndisponibil) as exc:
            flash(str(exc), 'eroare')
            return render_template('scanare_noua.html', subneturi=subneturi, are_cont_salvat=are_cont_salvat,
                                   cont_programat=cont_programat, form=f)
        sid = manager.adauga(db, prefix=prefix, ip_start=start, ip_end=end, eticheta=eticheta,
                             utilizator_scanare=utilizator_scanare, parola=parola,
                             initiat_de=g.user['username'], subnet_id=subnet_id)
        jurnal('scanare_ceruta', f'#{sid} {prefix}.{start}-{end} ({eticheta})')
        flash('Scanarea a fost pusă în coadă.' if manager.ocupat() else 'Scanarea a pornit.', 'succes')
        return redirect(url_for('main.scanare', sid=sid))
    implicit_user = g.user['username'] if g.user['tip_auth'] == 'ad' else ''
    # „Scanea ză“ din pagina Subneturi deschide formularul cu subnetul deja ales
    preselectat = request.args.get('subnet_id', '')
    return render_template('scanare_noua.html', subneturi=subneturi, are_cont_salvat=are_cont_salvat,
                           cont_programat=cont_programat, form={'cont_user': implicit_user, 'subnet_id': preselectat})


@bp.route('/scanari')
@auth.necesita_rol('vizualizare')
def scanari():
    lista = get_db().execute('SELECT * FROM scanari ORDER BY id DESC LIMIT 500').fetchall()
    return render_template('scanari.html', scanari=lista)


@bp.route('/scanare/<int:sid>')
@auth.necesita_rol('vizualizare')
def scanare(sid):
    s = _scanare_sau_404(sid)
    dispozitive = get_db().execute('SELECT * FROM dispozitive WHERE scanare_id = ? ORDER BY id', (sid,)).fetchall()
    prag = get_setare_int('prag_spatiu_c_gb')
    alerte = {d['id']: analiza.alerte_dispozitiv(d, prag) for d in dispozitive}
    anterioara = get_db().execute(
        "SELECT id, creat_la FROM scanari WHERE prefix = ? AND id < ? AND stare IN ('finalizat', 'oprit') "
        "ORDER BY id DESC LIMIT 1", (s['prefix'], sid)).fetchone()
    return render_template('scanare.html', s=s, dispozitive=dispozitive, alerte=alerte, anterioara=anterioara,
                           sumar=analiza.sumar_alerte(dispozitive, prag))


@bp.route('/api/scanare/<int:sid>/stare')
@auth.necesita_rol('vizualizare')
def api_stare(sid):
    s = _scanare_sau_404(sid)
    live = manager.stare_live(sid) or {}
    return jsonify({k: s[k] for k in ('stare', 'mesaj', 'total', 'procesate', 'online', 'offline', 'refuzat',
                                      'ssd', 'hdd', 'imprimante')} | {
        'stare_text': STARI.get(s['stare']), 'ip_curent': live.get('ip_curent', ''),
        'loguri': live.get('loguri', []),
        'procent': round(100 * s['procesate'] / s['total']) if s['total'] else 0})


@bp.route('/scanare/<int:sid>/opreste', methods=['POST'])
@auth.necesita_rol('admin')
def scanare_opreste(sid):
    s = _scanare_sau_404(sid)
    if manager.opreste(sid):
        jurnal('scanare_oprire_ceruta', f'#{sid}')
        flash('Oprirea a fost cerută — scanarea se încheie după IP-ul curent.', 'succes')
    else:
        flash(f'Scanarea nu mai rulează (stare: {STARI.get(s["stare"])}).', 'eroare')
    return redirect(url_for('main.scanare', sid=sid))


@bp.route('/scanare/<int:sid>/sterge', methods=['POST'])
@auth.necesita_rol('superadmin')
def scanare_sterge(sid):
    s = _scanare_sau_404(sid)
    if s['stare'] in ('ruleaza', 'in_asteptare'):
        flash('Opriți scanarea înainte de ștergere.', 'eroare')
        return redirect(url_for('main.scanare', sid=sid))
    db = get_db()
    db.execute('DELETE FROM scanari WHERE id = ?', (sid,))
    db.commit()
    jurnal('scanare_stearsa', f'#{sid} {s["eticheta"]} din {s["creat_la"]}')
    flash('Scanarea a fost ștearsă.', 'succes')
    return redirect(url_for('main.scanari'))


@bp.route('/scanare/<int:sid>/export.<fmt>')
@auth.necesita_rol('vizualizare')
def scanare_export(sid, fmt):
    s = _scanare_sau_404(sid)
    randuri = get_db().execute('SELECT * FROM dispozitive WHERE scanare_id = ? ORDER BY id', (sid,)).fetchall()
    nume = f'audit_{s["prefix"].replace(".", "_")}_{s["creat_la"][:10]}'
    jurnal('export', f'#{sid} {fmt}')
    if fmt == 'csv':
        return Response(csvio.export_csv(randuri), mimetype='text/csv',
                        headers={'Content-Disposition': f'attachment; filename="{nume}.csv"'})
    if fmt == 'xlsx':
        detalii = (f'Interval {s["prefix"]}.{s["ip_start"]}–{s["ip_end"]} · scanare din {_filtru_data(s["creat_la"])} · '
                   f'{s["online"]} online, {s["offline"]} offline, {s["refuzat"]} refuzat · sursa: {s["sursa"]}')
        return Response(csvio.export_xlsx(randuri, s['eticheta'], f'Raport de audit rețea — {s["eticheta"]}', detalii),
                        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        headers={'Content-Disposition': f'attachment; filename="{nume}.xlsx"'})
    abort(404)


@bp.route('/comparare')
@auth.necesita_rol('vizualizare')
def comparare():
    db = get_db()
    lista = db.execute("SELECT * FROM scanari WHERE stare IN ('finalizat', 'oprit') ORDER BY id DESC LIMIT 300").fetchall()
    a, b = request.args.get('a', type=int), request.args.get('b', type=int)
    rezultat = sa = sb = None
    if a and b:
        sa, sb = _scanare_sau_404(a), _scanare_sau_404(b)
        if sa['id'] > sb['id']:
            sa, sb = sb, sa      # „vechi“ -> „nou“
        da = db.execute('SELECT * FROM dispozitive WHERE scanare_id = ?', (sa['id'],)).fetchall()
        dbb = db.execute('SELECT * FROM dispozitive WHERE scanare_id = ?', (sb['id'],)).fetchall()
        rezultat = analiza.compara(da, dbb)
    return render_template('comparare.html', scanari=lista, rezultat=rezultat, sa=sa, sb=sb, a=a, b=b)


@bp.route('/echipamente')
@auth.necesita_rol('vizualizare')
def echipamente():
    lista = analiza.echipamente_cunoscute(get_db(), get_setare_int('zile_fantoma'))
    if request.args.get('export') == 'xlsx':
        jurnal('export', 'echipamente xlsx')
        return Response(csvio.export_xlsx([e['d'] for e in lista], 'Echipamente', 'Inventar echipamente cunoscute',
                                          f'{len(lista)} echipamente — ultima stare cunoscută din toate scanările finalizate'),
                        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        headers={'Content-Disposition': f'attachment; filename="echipamente_{acum()[:10]}.xlsx"'})
    return render_template('echipamente.html', echipamente=lista, zile_fantoma=get_setare_int('zile_fantoma'))


@bp.route('/import', methods=['GET', 'POST'])
@auth.necesita_rol('admin')
def import_csv():
    if request.method == 'POST':
        fisier = request.files.get('fisier')
        if not fisier or not fisier.filename:
            flash('Alegeți un fișier CSV.', 'eroare')
            return redirect(url_for('main.import_csv'))
        try:
            prefix, start, end, dispozitive = csvio.citeste_csv_v6(fisier.read())
        except csvio.ImportInvalid as exc:
            flash(str(exc), 'eroare')
            return redirect(url_for('main.import_csv'))
        data_scanare = (request.form.get('data_scanare') or '').strip()
        try:
            creat_la = datetime.strptime(data_scanare, '%Y-%m-%d').strftime('%Y-%m-%d 12:00:00') if data_scanare else acum()
        except ValueError:
            creat_la = acum()
        eticheta = (request.form.get('eticheta') or '').strip() or f'Import {fisier.filename}'
        numar = {k: 0 for k in ('online', 'offline', 'refuzat', 'ssd', 'hdd', 'imprimante')}
        for d in dispozitive:
            st = d['status']
            numar['online'] += st == 'ONLINE'
            numar['offline'] += st == 'OFFLINE'
            numar['refuzat'] += st in ('Acces Refuzat', 'Timeout WMI')
            numar['ssd'] += d['tip_stocare'] == 'SSD'
            numar['hdd'] += d['tip_stocare'] == 'HDD'
            numar['imprimante'] += d['tip_dispozitiv'] == 'Imprimanta'
        db = get_db()
        cur = db.execute(
            'INSERT INTO scanari (eticheta, prefix, ip_start, ip_end, sursa, stare, mesaj, initiat_de, creat_la, '
            'pornit_la, terminat_la, total, procesate, online, offline, refuzat, ssd, hdd, imprimante) '
            "VALUES (?, ?, ?, ?, 'import', 'finalizat', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (eticheta, prefix, start, end, f'Importat din {fisier.filename}', g.user['username'], creat_la,
             creat_la, creat_la, len(dispozitive), len(dispozitive), numar['online'], numar['offline'],
             numar['refuzat'], numar['ssd'], numar['hdd'], numar['imprimante']))
        sid = cur.lastrowid
        db.executemany(f'INSERT INTO dispozitive (scanare_id, {", ".join(CAMPURI_DISPOZITIV)}) '
                       f'VALUES (?, {", ".join("?" * len(CAMPURI_DISPOZITIV))})',
                       [[sid] + [d[c] for c in CAMPURI_DISPOZITIV] for d in dispozitive])
        db.commit()
        jurnal('import_csv', f'#{sid} {fisier.filename}: {len(dispozitive)} rânduri')
        flash(f'Import reușit: {len(dispozitive)} adrese.', 'succes')
        return redirect(url_for('main.scanare', sid=sid))
    return render_template('import.html')


# -- Subneturi și programări ------------------------------------------------------------

@bp.route('/subneturi', methods=['GET', 'POST'])
@auth.necesita_rol('admin')
def subneturi():
    db = get_db()
    if request.method == 'POST':
        f = request.form
        try:
            prefix, start, end = valideaza_interval(f.get('prefix'), f.get('ip_start'), f.get('ip_end'))
            nume = (f.get('nume') or '').strip()
            if not nume:
                raise ValueError('Denumirea este obligatorie.')
        except ValueError as exc:
            flash(str(exc), 'eroare')
        else:
            sid = f.get('id', type=int)
            if sid:
                db.execute('UPDATE subneturi SET nume = ?, prefix = ?, ip_start = ?, ip_end = ?, descriere = ? '
                           'WHERE id = ?', (nume, prefix, start, end, f.get('descriere', '').strip(), sid))
                jurnal('subnet_modificat', f'#{sid} {nume} {prefix}.{start}-{end}')
            else:
                db.execute('INSERT INTO subneturi (nume, prefix, ip_start, ip_end, descriere) VALUES (?, ?, ?, ?, ?)',
                           (nume, prefix, start, end, f.get('descriere', '').strip()))
                jurnal('subnet_adaugat', f'{nume} {prefix}.{start}-{end}')
            db.commit()
            flash('Subnet salvat.', 'succes')
            return redirect(url_for('main.subneturi'))
    # fiecare subnet, cu ultima lui scanare (dacă există)
    lista = db.execute(
        "SELECT n.*, (SELECT MAX(s.id) FROM scanari s WHERE s.prefix = n.prefix AND s.ip_start = n.ip_start "
        "AND s.ip_end = n.ip_end AND s.stare IN ('finalizat', 'oprit')) AS ultima_id, "
        "(SELECT s.creat_la FROM scanari s WHERE s.prefix = n.prefix AND s.ip_start = n.ip_start AND s.ip_end = n.ip_end "
        "AND s.stare IN ('finalizat', 'oprit') ORDER BY s.id DESC LIMIT 1) AS ultima_data "
        "FROM subneturi n ORDER BY n.prefix, n.ip_start").fetchall()
    editare = None
    if request.args.get('edit', type=int):
        editare = db.execute('SELECT * FROM subneturi WHERE id = ?', (request.args.get('edit', type=int),)).fetchone()
    return render_template('subneturi.html', subneturi=lista, editare=editare)


@bp.route('/subneturi/<int:sid>/sterge', methods=['POST'])
@auth.necesita_rol('admin')
def subnet_sterge(sid):
    db = get_db()
    s = db.execute('SELECT * FROM subneturi WHERE id = ?', (sid,)).fetchone()
    if s:
        db.execute('DELETE FROM subneturi WHERE id = ?', (sid,))
        db.commit()
        jurnal('subnet_sters', f'{s["nume"]} {s["prefix"]}')
        flash('Subnet șters (scanările existente se păstrează).', 'succes')
    return redirect(url_for('main.subneturi'))


@bp.route('/programari', methods=['GET', 'POST'])
@auth.necesita_rol('admin')
def programari():
    db = get_db()
    if request.method == 'POST':
        f = request.form
        try:
            subnet_id = f.get('subnet_id', type=int)
            if not subnet_id or not db.execute('SELECT 1 FROM subneturi WHERE id = ?', (subnet_id,)).fetchone():
                raise ValueError('Alegeți un subnet.')
            ora = (f.get('ora') or '').strip()
            if not re.match(r'^([01]\d|2[0-3]):[0-5]\d$', ora):
                raise ValueError('Ora trebuie să fie în format HH:MM.')
            frecventa = f.get('frecventa')
            zile, zi_luna = '', None
            if frecventa == 'saptamanal':
                zile = ','.join(z for z in f.getlist('zile') if z in dict(ZILE))
                if not zile:
                    raise ValueError('Alegeți cel puțin o zi a săptămânii.')
            elif frecventa == 'lunar':
                zi_luna = f.get('zi_luna', type=int)
                if not zi_luna or not 1 <= zi_luna <= 28:
                    raise ValueError('Ziua lunii trebuie să fie între 1 și 28.')
            else:
                raise ValueError('Frecvență invalidă.')
        except ValueError as exc:
            flash(str(exc), 'eroare')
        else:
            db.execute('INSERT INTO programari (subnet_id, frecventa, zile, zi_luna, ora, creat_de) VALUES (?, ?, ?, ?, ?, ?)',
                       (subnet_id, frecventa, zile, zi_luna, ora, g.user['username']))
            db.commit()
            jurnal('programare_adaugata', f'subnet #{subnet_id} {frecventa} {zile or zi_luna} {ora}')
            flash('Programare salvată.', 'succes')
            return redirect(url_for('main.programari'))
    lista = db.execute('SELECT p.*, s.nume, s.prefix, s.ip_start, s.ip_end FROM programari p '
                       'JOIN subneturi s ON s.id = p.subnet_id ORDER BY p.ora').fetchall()
    subs = db.execute('SELECT * FROM subneturi ORDER BY nume').fetchall()
    are_cont = bool(get_setare('cont_programat_user') and get_setare('cont_programat_parola'))
    return render_template('programari.html', programari=lista, subneturi=subs, ZILE=ZILE, are_cont=are_cont)


@bp.route('/programari/<int:pid>/<actiune>', methods=['POST'])
@auth.necesita_rol('admin')
def programare_actiune(pid, actiune):
    db = get_db()
    if actiune == 'comuta':
        db.execute('UPDATE programari SET activ = 1 - activ WHERE id = ?', (pid,))
    elif actiune == 'sterge':
        db.execute('DELETE FROM programari WHERE id = ?', (pid,))
    else:
        abort(404)
    db.commit()
    jurnal('programare_' + actiune, f'#{pid}')
    return redirect(url_for('main.programari'))


# -- Administrare (super-admin) -------------------------------------------------------------

@bp.route('/utilizatori')
@auth.necesita_rol('superadmin')
def utilizatori():
    db = get_db()
    lista = db.execute('SELECT * FROM utilizatori ORDER BY rol DESC, username').fetchall()
    doar_grup, grupuri, rol_grup = auth.setari_acces()
    return render_template('utilizatori.html', utilizatori=lista, domeniu=config.DOMAIN_NETBIOS,
                           doar_grup=doar_grup, grupuri=grupuri, rol_grup=rol_grup)


@bp.route('/utilizatori/<int:uid>/<actiune>', methods=['POST'])
@auth.necesita_rol('superadmin')
def utilizator_actiune(uid, actiune):
    db = get_db()
    u = db.execute('SELECT * FROM utilizatori WHERE id = ?', (uid,)).fetchone()
    if u is None:
        abort(404)
    if u['id'] == g.user['id'] and actiune in ('comuta', 'rol'):
        flash('Nu vă puteți dezactiva sau schimba propriul rol.', 'eroare')
        return redirect(url_for('main.utilizatori'))
    if actiune == 'comuta':
        db.execute('UPDATE utilizatori SET activ = 1 - activ WHERE id = ?', (uid,))
    elif actiune == 'rol':
        rol = request.form.get('rol')
        if rol not in auth.ROLURI:
            abort(400)
        db.execute('UPDATE utilizatori SET rol = ? WHERE id = ?', (rol, uid))
    elif actiune == 'deblocheaza':
        db.execute('UPDATE utilizatori SET incercari_esuate = 0, blocat_pana = NULL WHERE id = ?', (uid,))
    elif actiune == 'parola':
        if u['tip_auth'] != 'local':
            abort(400)
        try:
            auth.seteaza_parola_locala(db, uid, request.form.get('parola', ''))
        except ValueError as exc:
            flash(str(exc), 'eroare')
            return redirect(url_for('main.utilizatori'))
    else:
        abort(404)
    db.commit()
    jurnal('utilizator_' + actiune, f'{u["username"]} {request.form.get("rol", "")}'.strip())
    flash('Modificare salvată.', 'succes')
    return redirect(url_for('main.utilizatori'))


@bp.route('/setari', methods=['GET', 'POST'])
@auth.necesita_rol('superadmin')
def setari():
    db = get_db()
    if request.method == 'POST':
        f = request.form
        sectiune = f.get('sectiune')
        if sectiune == 'scanare':
            limite = {'timeout_sec': (5, 60), 'delay_ms': (0, 5000), 'retentie_luni': (0, 120),
                      'prag_spatiu_c_gb': (1, 500), 'zile_fantoma': (7, 365), 'ram_tinta_gb': (2, 64),
                      'ssd_gb': (128, 4000), 'prag_disc_mic_gb': (16, 4000), 'prag_toner': (1, 100), 'vechime_ani': (1, 30)}
            for cheie, (mn, mx) in limite.items():
                v = f.get(cheie, type=int)
                if v is None or not mn <= v <= mx:
                    flash(f'Valoare invalidă pentru {cheie} ({mn}–{mx}).', 'eroare')
                    return redirect(url_for('main.setari'))
                set_setare(cheie, v)
            set_setare('licente', '1' if f.get('licente') else '0')
            set_setare('snmp', '1' if f.get('snmp') else '0')
            comunitate = (f.get('snmp_community') or 'public').strip()
            if not re.match(r'^[\x21-\x7e]{1,32}$', comunitate):
                flash('Community SNMP invalid (1–32 caractere, fără spații).', 'eroare')
                return redirect(url_for('main.setari'))
            set_setare('snmp_community', comunitate)
            jurnal('setari_modificate', 'parametri scanare')
            flash('Setări salvate.', 'succes')
        elif sectiune == 'cont':
            user = auth.normalizeaza_username(f.get('cont_user'))
            parola = f.get('cont_parola', '')
            if not user or not parola:
                flash('Introduceți utilizatorul și parola contului de scanare.', 'eroare')
            else:
                try:
                    set_setare('cont_programat_parola', secret_store.cifreaza(parola))
                    set_setare('cont_programat_user', user)
                    jurnal('cont_programat_salvat', user)
                    flash(f'Contul {config.DOMAIN_NETBIOS}\\{user} a fost salvat cifrat (DPAPI).', 'succes')
                except secret_store.SecretIndisponibil as exc:
                    flash(str(exc), 'eroare')
        elif sectiune == 'acces':
            grupuri = [x.strip() for x in (f.get('grupuri_ad_acces') or '').split(',') if x.strip()]
            activ = bool(f.get('acces_doar_grup'))
            rol = f.get('rol_grup')
            if rol not in ('admin', 'vizualizare'):
                abort(400)
            if activ and not grupuri:
                flash('Introduceți cel puțin un grup AD.', 'eroare')
                return redirect(url_for('main.setari'))
            # un nume de grup greșit ar refuza toate conturile de domeniu — verificăm înainte de salvare
            _gasite, negasite = auth.rezolva_grupuri(grupuri)
            if negasite:
                flash('Grupul nu există în domeniu: ' + ', '.join(negasite) + '. Setarea nu a fost salvată.', 'eroare')
                return redirect(url_for('main.setari'))
            set_setare('grupuri_ad_acces', ', '.join(grupuri))
            set_setare('rol_grup', rol)
            set_setare('acces_doar_grup', '1' if activ else '0')
            jurnal('acces_modificat', f'doar grup: {"da" if activ else "nu"}; grupuri: {", ".join(grupuri)}; rol nou: {rol}')
            flash('Regula de acces a fost salvată.' + (' Conturile de domeniu care nu sunt în grup vor fi refuzate la logare.'
                                                      if activ else ''), 'succes')
        elif sectiune == 'cont_sterge':
            db.execute("DELETE FROM setari WHERE cheie IN ('cont_programat_user', 'cont_programat_parola')")
            db.commit()
            jurnal('cont_programat_sters', '')
            flash('Contul de scanare salvat a fost șters.', 'succes')
        return redirect(url_for('main.setari'))
    valori = {k: get_setare(k) for k in config.SETARI_IMPLICITE}
    are_local = db.execute("SELECT 1 FROM utilizatori WHERE tip_auth = 'local' AND rol = 'superadmin' AND activ = 1").fetchone()
    return render_template('setari.html', valori=valori, cont_user=get_setare('cont_programat_user'),
                           are_parola=bool(get_setare('cont_programat_parola')), domeniu=config.DOMAIN_NETBIOS,
                           e_windows=config.IS_WINDOWS, are_local=bool(are_local))


@bp.route('/jurnal')
@auth.necesita_rol('admin')
def jurnal_view():
    q = (request.args.get('q') or '').strip()
    db = get_db()
    if q:
        like = f'%{q}%'
        lista = db.execute('SELECT * FROM jurnal WHERE utilizator LIKE ? OR actiune LIKE ? OR detalii LIKE ? '
                           'ORDER BY id DESC LIMIT 1000', (like, like, like)).fetchall()
    else:
        lista = db.execute('SELECT * FROM jurnal ORDER BY id DESC LIMIT 1000').fetchall()
    return render_template('jurnal.html', intrari=lista, q=q)


@bp.route('/manual')
@auth.necesita_rol('vizualizare')
def manual():
    return render_template('manual.html', port=config.PORT, domeniu=config.DOMAIN_NETBIOS)


# -- Stare parc, necesar piese, imprimante (ramura „Imprimante“) -------------------------

from urllib.parse import urlencode  # noqa: E402

from . import parc  # noqa: E402

# Coloanele care pot fi alese în tabelul „Stare parc“
COLOANE_PC = [('ip', 'IP'), ('hostname', 'Nume stație'), ('interval_nume', 'Subnet'), ('utilizator', 'Utilizator'),
              ('model', 'Producător / Model'), ('serial', 'Serie'), ('tip', 'Tip sistem'), ('procesor', 'Procesor'),
              ('ram', 'RAM'), ('stocare', 'Stocare'), ('c_liber', 'C: liber'), ('os', 'Sistem de operare'),
              ('antivirus', 'Antivirus'), ('win11', 'Windows 11'), ('tpm', 'TPM'), ('vechime', 'Vechime'),
              ('mac', 'MAC'), ('indicatori', 'Indicatori')]
COLOANE_IMPLICITE = ['ip', 'hostname', 'interval_nume', 'model', 'ram', 'stocare', 'os', 'antivirus', 'win11', 'indicatori']
STARI_AV = {'activ': 'Activ', 'neactualizat': 'Neactualizat', 'dezactivat': 'Dezactivat', 'lipsa': 'Lipsă',
            'indisponibil': 'Indisponibil'}


def _context_filtre(pagina):
    """Date + filtre + reguli comune pentru paginile parc / necesar / imprimante."""
    db = get_db()
    scanare_id = request.args.get('scanare', type=int)
    scanari, dispozitive = parc.incarca(db, scanare_id)
    reguli = parc.reguli_din(request.args, get_setare_int)
    ind = parc.indicatori(reguli)
    f = parc.citeste_filtre(request.args, reguli)
    vederi = db.execute('SELECT * FROM vederi WHERE utilizator = ? AND pagina = ? ORDER BY nume',
                        (g.user['username'], pagina)).fetchall()
    marci = sorted({parc.marca(d) for d in dispozitive if d.get('tip_dispozitiv') == 'Imprimanta'})
    return {'scanari': scanari, 'dispozitive': dispozitive, 'reguli': reguli, 'ind': ind, 'f': f, 'vederi': vederi,
            'scanare_id': scanare_id, 'CATEGORII_OS': parc.CATEGORII_OS, 'TIPURI_SISTEM': parc.TIPURI_SISTEM,
            'marci': marci, 'pagina': pagina, 'query': request.query_string.decode('utf-8', 'replace')}


def _descriere_filtre(c):
    f, parti = c['f'], []
    nume_int = {parc.cheie_interval(s): s['eticheta'] for s in c['scanari']}
    parti.append('Subneturi: ' + (', '.join(nume_int.get(i, i) for i in f['interval']) if f['interval'] else 'toate'))
    if f['os']:
        parti.append('Sisteme: ' + ', '.join(f['os']))
    if f['tip']:
        parti.append('Tip: ' + ', '.join(f['tip']))
    if f['stocare']:
        parti.append('Stocare: ' + ', '.join(f['stocare']))
    if f['ind']:
        parti.append(f'Indicatori ({f["mod_ind"]}): ' + ', '.join(c['ind'][k][0] for k in f['ind'] if k in c['ind']))
    if f['q']:
        parti.append(f'Căutare: „{f["q"]}“')
    if c['scanare_id']:
        parti.append(f'doar scanarea #{c["scanare_id"]}')
    return ' · '.join(parti)


def _randuri_pc(pcuri, ind):
    rez = []
    for d in pcuri:
        w11, motive = parc.compatibil_win11(d)
        r = dict(d)
        r.update(categorie_os=parc.categorie_os(d), w11=w11, w11_motive=motive, ani=parc.vechime_ani(d),
                 av_text=STARI_AV.get(d.get('antivirus_stare'), ''),
                 indicatori=[(k, ind[k][0], ind[k][1]) for k in ind if ind[k][2](d)])
        rez.append(r)
    return rez


@bp.route('/parc')
@auth.necesita_rol('vizualizare')
def stare_parc():
    c = _context_filtre('parc')
    pcuri = parc.filtreaza_pc(c['dispozitive'], c['f'], c['ind'])
    f_impr = dict(c['f'], q='', marca=[])
    imprimante = parc.filtreaza_imprimante(c['dispozitive'], f_impr)
    tot, pe_interval = parc.stare_parc(pcuri, imprimante, c['scanari'], c['ind'], c['reguli']['prag_toner'])
    coloane = c['f']['coloane'] or COLOANE_IMPLICITE
    randuri = _randuri_pc(pcuri, c['ind'])
    descriere = _descriere_filtre(c)
    if request.args.get('export') == 'xlsx':
        jurnal('export', 'stare parc xlsx')
        return Response(csvio.export_xlsx(pcuri, 'Stare parc', 'Stare parc calculatoare', descriere),
                        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        headers={'Content-Disposition': f'attachment; filename="stare_parc_{acum()[:10]}.xlsx"'})
    return render_template('parc.html', **c, tot=tot, pe_interval=pe_interval, randuri=randuri, coloane=coloane,
                           COLOANE_PC=COLOANE_PC, descriere=descriere)


@bp.route('/necesar')
@auth.necesita_rol('vizualizare')
def necesar():
    c = _context_filtre('necesar')
    pcuri = parc.filtreaza_pc(c['dispozitive'], c['f'], c['ind'])
    imprimante = parc.filtreaza_imprimante(c['dispozitive'], dict(c['f'], q='', marca=[]))
    n = parc.necesar(pcuri, imprimante, c['reguli'])
    descriere = _descriere_filtre(c) + f' · RAM țintă {c["reguli"]["ram_tinta_gb"]:g} GB · SSD minim {c["reguli"]["ssd_gb"]:g} GB'
    if request.args.get('export') == 'xlsx':
        jurnal('export', 'necesar piese xlsx')
        return Response(csvio.export_necesar_xlsx(n, 'Necesar piese și consumabile', descriere),
                        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        headers={'Content-Disposition': f'attachment; filename="necesar_piese_{acum()[:10]}.xlsx"'})
    return render_template('necesar.html', **c, n=n, descriere=descriere)


@bp.route('/imprimante')
@auth.necesita_rol('vizualizare')
def imprimante():
    c = _context_filtre('imprimante')
    lista = parc.filtreaza_imprimante(c['dispozitive'], c['f'])
    prag = c['reguli']['prag_toner']
    randuri = []
    for d in lista:
        r = dict(d)
        r.update(marca=parc.marca(d), consumabile=parc.consumabile(d), stari=parc.stari_imprimanta(d),
                 nivel_min=parc.nivel_minim(d))
        randuri.append(r)
    sumar = {'total': len(randuri),
             'toner_scazut': sum(1 for r in randuri if r['nivel_min'] is not None and r['nivel_min'] < prag),
             'probleme': sum(1 for r in randuri if any(n == 'critic' for _t, n in r['stari'])),
             'fara_snmp': sum(1 for r in randuri if not r['prn_consumabile'] and not r['prn_pagini']),
             'pagini': sum(int(r['prn_pagini']) for r in randuri if str(r['prn_pagini']).isdigit())}
    if request.args.get('export') == 'xlsx':
        jurnal('export', 'imprimante xlsx')
        return Response(csvio.export_xlsx(lista, 'Imprimante', 'Imprimante de rețea', _descriere_filtre(c)),
                        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        headers={'Content-Disposition': f'attachment; filename="imprimante_{acum()[:10]}.xlsx"'})
    return render_template('imprimante.html', **c, randuri=randuri, sumar=sumar, prag=prag)


@bp.route('/vederi', methods=['POST'])
@auth.necesita_rol('vizualizare')
def vedere_salveaza():
    pagina = request.form.get('pagina')
    nume = (request.form.get('nume') or '').strip()[:80]
    query = (request.form.get('query') or '')[:4000]
    if pagina not in ('parc', 'necesar', 'imprimante') or not nume:
        flash('Dați un nume vederii.', 'eroare')
    else:
        db = get_db()
        db.execute('DELETE FROM vederi WHERE utilizator = ? AND pagina = ? AND nume = ?', (g.user['username'], pagina, nume))
        db.execute('INSERT INTO vederi (utilizator, pagina, nume, query, creat_la) VALUES (?, ?, ?, ?, ?)',
                   (g.user['username'], pagina, nume, query, acum()))
        db.commit()
        flash(f'Vederea „{nume}“ a fost salvată.', 'succes')
    tinta = {'parc': 'main.stare_parc', 'necesar': 'main.necesar', 'imprimante': 'main.imprimante'}.get(pagina, 'main.stare_parc')
    return redirect(url_for(tinta) + ('?' + query if query else ''))


@bp.route('/vederi/<int:vid>/sterge', methods=['POST'])
@auth.necesita_rol('vizualizare')
def vedere_sterge(vid):
    db = get_db()
    v = db.execute('SELECT * FROM vederi WHERE id = ? AND utilizator = ?', (vid, g.user['username'])).fetchone()
    if v is None:
        abort(404)
    db.execute('DELETE FROM vederi WHERE id = ?', (vid,))
    db.commit()
    tinta = {'parc': 'main.stare_parc', 'necesar': 'main.necesar', 'imprimante': 'main.imprimante'}[v['pagina']]
    return redirect(url_for(tinta))


@bp.app_template_filter('url_cu')
def _url_cu(query, **modificari):
    """Construiește un query string pornind de la cel curent (pentru linkuri pe indicatori)."""
    from urllib.parse import parse_qsl
    perechi = [(k, v) for k, v in parse_qsl(query, keep_blank_values=True) if k not in modificari and k != 'export']
    for k, v in modificari.items():
        for x in (v if isinstance(v, (list, tuple)) else [v]):
            perechi.append((k, x))
    return urlencode(perechi)
