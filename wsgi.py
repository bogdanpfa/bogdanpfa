"""Entry point pentru servere.ps1 (waitress --listen ... wsgi:app)."""
from serve import verifica_dependinte
verifica_dependinte()
from audit import create_app
app = create_app()
