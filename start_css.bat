@echo off
rem ============================================================
rem  Porneste aplicatia "Comanda servicii suplimentare" si o
rem  deschide in browser. Fereastra trebuie sa ramana deschisa
rem  cat timp se lucreaza; aplicatia se opreste cu Ctrl+C sau
rem  inchizand fereastra.
rem ============================================================
title Comanda servicii suplimentare
cd /d "%~dp0"

rem --- mediul virtual (.venv) daca exista, altfel Python din sistem ---
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
) else (
    echo [Atentie] Nu exista .venv in "%~dp0" - se foloseste Python din sistem.
)

rem --- verificare rapida: sunt instalate dependentele? ---
python -c "import flask, lxml, PIL, dotenv" 2>nul
if errorlevel 1 (
    echo.
    echo [Eroare] Lipsesc dependentele sau Python nu este instalat. Ruleaza o data:
    echo     pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

rem --- deschide browserul dupa ~3 secunde, in paralel cu pornirea serverului ---
start "" /min cmd /c "ping -n 4 127.0.0.1 >nul & start http://127.0.0.1:5006"

echo Se porneste aplicatia pe http://127.0.0.1:5006 ...
echo (inchideti aceasta fereastra pentru a opri aplicatia)
echo.
python app.py

echo.
echo Aplicatia s-a oprit.
pause
