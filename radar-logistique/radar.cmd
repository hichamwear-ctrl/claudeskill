@echo off
REM ═══════════════════════════════════════════════════════════════════
REM  RADAR COMMERCIAL — lanceur Windows
REM
REM      cd radar-logistique
REM      radar --base radar.sqlite3 statut
REM
REM  Rien a installer : bibliotheque standard de Python, plus PyYAML.
REM  CMD cherche d'abord dans le repertoire courant : etre dans le
REM  dossier du projet suffit, aucun PATH a modifier.
REM
REM  Sous PowerShell, le repertoire courant n'est PAS cherche : il faut
REM  ecrire .\radar (avec le point-antislash).
REM ═══════════════════════════════════════════════════════════════════
setlocal
set "RADAR_RACINE=%~dp0"
set "PYTHONPATH=%RADAR_RACINE%;%PYTHONPATH%"

REM Le rapport contient des filets et des emojis. Deux reglages, et les
REM deux sont necessaires : l'un dit a Python quoi ecrire, l'autre dit a
REM la console quoi afficher. Sans le second, Windows montre du charabia
REM la ou tout est pourtant correct.
set "PYTHONIOENCODING=utf-8"
for /f "tokens=2 delims=:" %%p in ('chcp') do set "RADAR_CHCP=%%p"
chcp 65001 >nul 2>nul

where python >nul 2>nul
if errorlevel 1 (
  echo.
  echo   PYTHON INTROUVABLE
  echo.
  echo   Installez Python 3.11 ou plus recent depuis python.org,
  echo   en cochant « Add python.exe to PATH ».
  echo.
  if defined RADAR_CHCP chcp %RADAR_CHCP% >nul 2>nul
  exit /b 2
)

python -m radar.cli %*
set "RADAR_CODE=%errorlevel%"

REM On rend la console dans l'etat ou on l'a trouvee.
if defined RADAR_CHCP chcp %RADAR_CHCP% >nul 2>nul
exit /b %RADAR_CODE%
