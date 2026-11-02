@echo off
rem Builds two Windows versions:
rem   1) Folder version : dist\MediaConverter\MediaConverter.exe (+ dist\MediaConverter-Windows.zip)
rem   2) Portable       : dist\MediaConverter-Portable.exe (one file, runs from USB, settings saved next to it)
rem Needs Python 3.10+ on the BUILD machine only (users of the .exe do not need Python).
rem If Python is missing, this script offers to install it with winget (Windows 10/11).
setlocal
cd /d "%~dp0"

rem Create a fresh virtual environment (never copy .venv from the Mac)
if exist ".venv\Scripts\python.exe" goto :have_venv
rem Test that Python really runs: Windows ships a "python" shortcut that only opens the Store
set "BASEPY="
py -3 -c "import sys" >nul 2>nul && set "BASEPY=py -3"
if not defined BASEPY (
  python -c "import sys" >nul 2>nul && set "BASEPY=python"
)
if not defined BASEPY call :install_python
if not defined BASEPY goto :nopython
%BASEPY% -m venv .venv || goto :fail

:have_venv
set "PY=.venv\Scripts\python.exe"

echo [1/5] Installing libraries...
"%PY%" -m pip install -q --upgrade pip
rem pillow lets PyInstaller turn the PNG logo into a Windows .ico icon
"%PY%" -m pip install -q -r requirements.txt pyinstaller pillow || goto :fail

echo [2/5] Creating app icon...
if not exist build mkdir build
"%PY%" app.py --export-icon build\icon.png || goto :fail

echo [3/5] Building MediaConverter.exe ...
rem The exe name is ASCII on purpose; the window title and UI stay Arabic
"%PY%" -m PyInstaller --noconfirm --clean --windowed --log-level WARN ^
  --name MediaConverter ^
  --icon build\icon.png ^
  --collect-data imageio_ffmpeg ^
  --exclude-module tkinter ^
  --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtWebEngineWidgets ^
  --exclude-module PySide6.QtQml --exclude-module PySide6.QtQuick --exclude-module PySide6.Qt3DCore ^
  --exclude-module PySide6.QtMultimedia --exclude-module PySide6.QtPdf ^
  app.py || goto :fail

echo [4/5] Building portable MediaConverter-Portable.exe ...
rem The PORTABLE marker tells app.py to keep its settings in an .ini beside the exe
type nul > build\PORTABLE
"%PY%" -m PyInstaller --noconfirm --clean --windowed --onefile --log-level WARN ^
  --name MediaConverter-Portable ^
  --icon build\icon.png ^
  --add-data "build\PORTABLE;." ^
  --collect-data imageio_ffmpeg ^
  --exclude-module tkinter ^
  --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtWebEngineWidgets ^
  --exclude-module PySide6.QtQml --exclude-module PySide6.QtQuick --exclude-module PySide6.Qt3DCore ^
  --exclude-module PySide6.QtMultimedia --exclude-module PySide6.QtPdf ^
  app.py || goto :fail

echo [5/5] Packing zip for sharing...
powershell -NoProfile -Command "Compress-Archive -Force -Path 'dist\MediaConverter' -DestinationPath 'dist\MediaConverter-Windows.zip'" || goto :fail
if exist MediaConverter.spec del MediaConverter.spec
if exist MediaConverter-Portable.spec del MediaConverter-Portable.spec

echo.
echo Done!
echo   App:       dist\MediaConverter\MediaConverter.exe
echo   Zip:       dist\MediaConverter-Windows.zip
echo   Portable:  dist\MediaConverter-Portable.exe
if not defined CI pause
exit /b 0

:fail
echo.
echo [X] Build failed - see the messages above.
if not defined CI pause
exit /b 1

:nopython
echo.
echo [X] Python not found. Install Python 3.10+ from https://www.python.org/downloads/
echo     and tick "Add python.exe to PATH", then run this file again.
if not defined CI pause
exit /b 1

:install_python
rem Offer an automatic install with winget (built into Windows 10/11); only with the user's consent
if defined CI exit /b 0
where winget >nul 2>nul || exit /b 0
echo.
echo Python is not installed on this computer (needed only to build the program).
choice /c YN /m "Install Python 3.12 now using winget (official, free, about 2 minutes)"
if errorlevel 2 exit /b 0
winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
rem PATH is not refreshed in this window, so use the installed python.exe directly
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set BASEPY="%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
exit /b 0
