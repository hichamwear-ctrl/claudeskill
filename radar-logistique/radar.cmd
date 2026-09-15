@echo off
REM ═══════════════════════════════════════════════════════════════════
REM  RADAR COMMERCIAL — lanceur Windows
REM
REM      radar analyse-du-jour --import mon-export.tsv
REM      radar opportunites
REM      radar statut
REM
REM  Il n'y a rien a installer : le radar n'utilise que la bibliotheque
REM  standard de Python, plus PyYAML. Ce fichier ne fait que rappeler
REM  « python -m radar.cli » depuis le bon dossier.
REM ═══════════════════════════════════════════════════════════════════
setlocal
set "RADAR_RACINE=%~dp0"
set "PYTHONPATH=%RADAR_RACINE%;%PYTHONPATH%"
set "PYTHONIOENCODING=utf-8"

where python >nul 2>nul
if errorlevel 1 (
  echo.
  echo   PYTHON INTROUVABLE
  echo.
  echo   Installez Python 3.11 ou plus recent depuis python.org,
  echo   en cochant « Add python.exe to PATH ».
  echo.
  exit /b 2
)

python -m radar.cli %*
exit /b %errorlevel%
