@echo off
REM ═══════════════════════════════════════════════════════════════════
REM  RADAR COMMERCIAL — lanceur Windows
REM
REM      cd radar-logistique
REM      radar --base radar.sqlite3 statut
REM
REM  Dependances : bibliotheque standard, plus PyYAML et tzdata.
REM      py -m pip install pyyaml tzdata
REM
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

REM ─────────────────────────────────────────────────────────────────
REM  QUEL INTERPRETEUR ?
REM
REM  « where python » ne suffit PAS, et c'est le defaut qu'on corrige
REM  ici : Windows 10 et 11 livrent un FAUX python.exe dans
REM  WindowsApps. Ce fichier existe, « where » le trouve, et il ne fait
REM  qu'afficher « Python introuvable » en renvoyant une erreur. Le
REM  lanceur croyait donc Python present et echouait a l'appel.
REM
REM  On n'interroge plus le PATH : on EXECUTE chaque candidat et on
REM  garde le premier qui repond vraiment. Le faux python.exe echoue au
REM  test et se disqualifie tout seul.
REM
REM  Ordre : « python » d'abord, pour qu'un environnement virtuel actif
REM  reste celui qu'on utilise — « py » ignore le venv et prendrait un
REM  autre interpreteur. Puis « py -3 », le lanceur officiel Windows,
REM  qui est le seul present sur le poste de test. Puis « python3 ».
REM ─────────────────────────────────────────────────────────────────
set "RADAR_PYTHON="
call :essayer python
if not defined RADAR_PYTHON call :essayer py -3
if not defined RADAR_PYTHON call :essayer python3
if not defined RADAR_PYTHON goto :sans_python

REM Version trop ancienne, PyYAML absent, fuseau Europe/Brussels
REM introuvable : le script le dit en clair et nomme la ligne a taper.
REM C'est ce qui manquait le jour ou tzdata a bloque un poste neuf.
%RADAR_PYTHON% "%RADAR_RACINE%outils\verifier_environnement.py" >nul 2>nul
if errorlevel 1 (
  %RADAR_PYTHON% "%RADAR_RACINE%outils\verifier_environnement.py"
  if defined RADAR_CHCP chcp %RADAR_CHCP% >nul 2>nul
  exit /b 2
)

%RADAR_PYTHON% -m radar.cli %*
set "RADAR_CODE=%errorlevel%"

REM On rend la console dans l'etat ou on l'a trouvee.
if defined RADAR_CHCP chcp %RADAR_CHCP% >nul 2>nul
exit /b %RADAR_CODE%

:essayer
REM Un candidat n'est retenu que s'il DEMARRE VRAIMENT. Le test reste
REM volontairement minuscule : aucun operateur de comparaison, qui serait
REM lu par CMD comme une redirection. La version et les dependances sont
REM verifiees juste apres, en Python, ou on peut le faire proprement.
%* -c "import sys" >nul 2>nul
if not errorlevel 1 set "RADAR_PYTHON=%*"
goto :eof

:sans_python
echo.
echo   PYTHON 3.11 OU PLUS RECENT EST INTROUVABLE
echo.
echo   Aucun de ces trois appels n'a repondu :
echo       python -c "import sys"
echo       py -3   -c "import sys"
echo       python3 -c "import sys"
echo.
echo   Installez Python 3.11 ou plus recent depuis python.org,
echo   en cochant « Add python.exe to PATH », puis :
echo       py -m pip install pyyaml tzdata
echo.
echo   Si « python » ouvre le Microsoft Store, c'est le faux python.exe
echo   de Windows : il ne compte pas comme une installation.
echo.
if defined RADAR_CHCP chcp %RADAR_CHCP% >nul 2>nul
exit /b 2
