# setup_od_server.ps1 — instalare initiala OD (Ordin de Deplasare) pe server
# Ruleaza de pe PC-ul de dezvoltare cu:
#   powershell -ExecutionPolicy Bypass -File "I:\...\setup_od_server.ps1"

$SERVER  = "cl6srvappiasi"
$PYTHON  = "C:\Users\bogdan.pavaluc\AppData\Local\Python\pythoncore-3.14-64\python.exe"
$PORT    = 5008

$APP_DIR_UNC = "\\$SERVER\C`$\DevTools\OD"
$COMUN_UNC   = "\\$SERVER\C`$\DevTools\_comun"
$FLAGDIR     = "\\$SERVER\C`$\DevTools\_server\restart"

Write-Host "`n=== SETUP ORDIN DE DEPLASARE PE SERVER (port $PORT) ===" -ForegroundColor Cyan
Write-Host "Server: $APP_DIR_UNC"

# ---------- 1. persoane.db ----------
Write-Host "`n[1/4] _comun\persoane.db..." -ForegroundColor Yellow
if (Test-Path "$COMUN_UNC\persoane.db") {
    Write-Host "     Exista deja pe server - nu suprascriem." -ForegroundColor DarkGray
} else {
    Write-Host "     ATENTIE: persoane.db nu exista in _comun! Ruleaza mai intai setup_agenda_server.ps1." -ForegroundColor Red
    exit 1
}

# ---------- 2. .env ----------
Write-Host "`n[2/4] .env pe server..." -ForegroundColor Yellow
if (Test-Path "$APP_DIR_UNC\.env") {
    Write-Host "     Exista deja pe server - nu suprascriem." -ForegroundColor DarkGray
} else {
    $lines = @(
        "# Ordin de Deplasare - SERVER ($SERVER)",
        "PORT=$PORT",
        "HOST=0.0.0.0",
        "PRODUCTION_MODE=true",
        "UNITATEA=SRTFC Iasi",
        "PERSOANE_DB_PATH=C:\DevTools\_comun\persoane.db"
    )
    $lines | Set-Content "$APP_DIR_UNC\.env" -Encoding UTF8
    Write-Host "     Creat cu PRODUCTION_MODE=true." -ForegroundColor Green
}

# ---------- 3. .venv + requirements ----------
Write-Host "`n[3/4] .venv si requirements..." -ForegroundColor Yellow
$venvPip = "$APP_DIR_UNC\.venv\Scripts\pip.exe"
if (Test-Path $venvPip) {
    Write-Host "     .venv exista deja." -ForegroundColor DarkGray
} else {
    $appDirServer = "C:\DevTools\OD"
    $logFile      = "C:\DevTools\_server\logs\OD_setup.log"
    $cmd = "`"$PYTHON`" -m venv `"$appDirServer\.venv`" && `"$appDirServer\.venv\Scripts\pip`" install -r `"$appDirServer\requirements.txt`" > `"$logFile`" 2>&1"

    Write-Host "     Creez .venv pe server via schtasks..." -ForegroundColor DarkGray
    schtasks /create /s $SERVER /tn "OD_Setup" /tr "cmd.exe /c $cmd" /sc once /st 00:00 /ru SYSTEM /rl HIGHEST /f | Out-Null
    schtasks /run /s $SERVER /tn "OD_Setup" | Out-Null

    Write-Host "     Astept instalarea (max 90 secunde)..." -ForegroundColor DarkGray
    $tries = 0
    while ($tries -lt 45 -and -not (Test-Path $venvPip)) {
        Start-Sleep -Seconds 2; $tries++
        Write-Host -NoNewline "."
    }
    Write-Host ""

    schtasks /delete /s $SERVER /tn "OD_Setup" /f | Out-Null

    if (Test-Path $venvPip) {
        Write-Host "     .venv si requirements instalate (inclusiv waitress)." -ForegroundColor Green
    } else {
        Write-Host "     Timeout. Log: \\$SERVER\C`$\DevTools\_server\logs\OD_setup.log" -ForegroundColor Red
        Get-Content "\\$SERVER\C`$\DevTools\_server\logs\OD_setup.log" -ErrorAction SilentlyContinue | Select-Object -Last 10
        exit 1
    }
}

# ---------- 4. Pornire ----------
Write-Host "`n[4/4] Pornesc OD via PortalApps-Watcher..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $FLAGDIR | Out-Null
Remove-Item "$FLAGDIR\OD.result.txt" -ErrorAction SilentlyContinue
Get-Date | Set-Content "$FLAGDIR\OD.flag" -Encoding ASCII
schtasks /run /s $SERVER /tn PortalApps-Watcher | Out-Null

$tries = 0
while ($tries -lt 30) {
    Start-Sleep -Seconds 2; $tries++
    if (Test-Path "$FLAGDIR\OD.result.txt") {
        $result = Get-Content "$FLAGDIR\OD.result.txt" -Raw
        Write-Host $result
        if ($result -match "PORNIT") {
            Write-Host "SUCCES: http://${SERVER}:$PORT/" -ForegroundColor Green
        }
        break
    }
}
if ($tries -ge 30) { Write-Host "Fara raspuns de la server in 60 secunde." -ForegroundColor Red }
