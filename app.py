import os
import io
import threading
import webbrowser
from flask import Flask, render_template, request, jsonify, send_file
from dotenv import load_dotenv

load_dotenv()

import persoane_repo as pr
from pdf_generator import generate_pdf

app = Flask(__name__)

UNITATEA = os.environ.get('UNITATEA', 'SRTFC Iași')
PORT = int(os.environ.get('PORT', 5006))


@app.route('/')
def index():
    return render_template('index.html', unitatea=UNITATEA)


@app.route('/api/persoane')
def api_persoane():
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])
    try:
        rezultate = pr.cauta_persoana(q, doar_active=True, limita=20)
        return jsonify([{
            'marca': p['marca'],
            'display': p['nume_afisare'] or '',
            'functie': p['functie'] or '',
            'loc_munca': p['loc_munca'] or UNITATEA,
        } for p in rezultate])
    except FileNotFoundError as e:
        return jsonify({'eroare': str(e)}), 503
    except Exception as e:
        return jsonify({'eroare': str(e)}), 500


@app.route('/genereaza', methods=['POST'])
def genereaza():
    try:
        pdf_bytes = generate_pdf(request.form)
        nr = (request.form.get('nr_ordin') or '0').strip()
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'ordin_deplasare_nr{nr}.pdf',
        )
    except Exception as e:
        app.logger.exception('Eroare PDF')
        return f'Eroare la generarea PDF: {e}', 500


if __name__ == '__main__':
    url = f'http://localhost:{PORT}'
    threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    app.run(host='0.0.0.0', port=PORT, debug=False)
