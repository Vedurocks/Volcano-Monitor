@echo off
setlocal EnableDelayedExpansion
title Volcano Eruption Monitor — Build
color 0A

:: Change to the folder where this .bat file lives
cd /d "%~dp0"

echo.
echo  ============================================================
echo   VOLCANO ERUPTION MONITOR v5.0  ^|  Vedurocks Ltd 2026
echo  ============================================================
echo.
echo  [OK]  Working directory: %CD%
echo.

:: ════════════════════════════════════════════════════════════
::  FLAGS
:: ════════════════════════════════════════════════════════════
set SKIP_PIP=0
set SKIP_ASSETS=0
set BUILD_DIR=C:\VEMBuild

:: ════════════════════════════════════════════════════════════
::  FIND PYTHON
:: ════════════════════════════════════════════════════════════
set PYEXE=

for %%P in (python.exe python3.exe) do (
    if not defined PYEXE (
        where %%P >nul 2>&1 && (
            for /f "tokens=*" %%F in ('where %%P 2^>nul') do (
                if not defined PYEXE set PYEXE=%%F
            )
        )
    )
)

for %%D in (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "C:\Python313\python.exe"
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
) do (
    if not defined PYEXE if exist %%D set PYEXE=%%~D
)

if not defined PYEXE (
    echo  [ERROR] Python not found.
    pause & exit /b 1
)

echo  [OK]  Python : !PYEXE!

for %%F in ("!PYEXE!") do set PYHOME=%%~dpF
if "!PYHOME:~-1!"=="\" set PYHOME=!PYHOME:~0,-1!
echo  [OK]  Home   : !PYHOME!

:: ════════════════════════════════════════════════════════════
::  FIX ENVIRONMENT
:: ════════════════════════════════════════════════════════════
set PYTHONHOME=!PYHOME!
set PYTHONPATH=
set PYTHONSTARTUP=
echo  [OK]  PYTHONHOME set
echo.

"!PYEXE!" -c "import sys; print('  sys.prefix =', sys.prefix)" 2>nul
if errorlevel 1 (
    echo  [ERROR] Python broken. Reinstall from python.org
    pause & exit /b 1
)
echo.

:: ════════════════════════════════════════════════════════════
::  INSTALL DEPENDENCIES
:: ════════════════════════════════════════════════════════════
if "!SKIP_PIP!"=="1" (
    echo  [SKIP] pip install
    goto :assets
)

echo  Upgrading pip...
"!PYEXE!" -m pip install --upgrade pip --quiet
echo.

echo  Installing required packages...
"!PYEXE!" -m pip install pyserial pillow requests pyinstaller --quiet
if errorlevel 1 (
    echo  [ERROR] Failed to install core packages.
    pause & exit /b 1
)
echo  [OK]  Core packages ready.

:: matplotlib is OPTIONAL - app works without it (graphs disabled)
echo.
echo  Installing matplotlib ^(optional - graphs will be disabled if this fails^)...
"!PYEXE!" -m pip install --only-binary=:all: matplotlib --quiet
if errorlevel 1 (
    echo  [WARN] Latest matplotlib unavailable, trying 3.8.x...
    "!PYEXE!" -m pip install --only-binary=:all: "matplotlib>=3.8,<3.9" --quiet
    if errorlevel 1 (
        echo  [WARN] matplotlib 3.8.x unavailable, trying 3.7.x...
        "!PYEXE!" -m pip install --only-binary=:all: "matplotlib>=3.7,<3.8" --quiet
        if errorlevel 1 (
            echo.
            echo  [INFO] matplotlib could not be installed ^(no binary wheel for your Python^).
            echo         The app will still work - graphs will show "pip install matplotlib".
            echo         This is normal and safe to ignore.
            echo.
        ) else (
            echo  [OK]  matplotlib 3.7.x installed.
        )
    ) else (
        echo  [OK]  matplotlib 3.8.x installed.
    )
) else (
    echo  [OK]  matplotlib installed.
)

echo.
echo  TIP: set SKIP_PIP=1 at top of this file to skip next time.
echo.

:assets
:: ════════════════════════════════════════════════════════════
::  GENERATE ASSETS
:: ════════════════════════════════════════════════════════════
if "!SKIP_ASSETS!"=="1" (
    echo  [SKIP] Assets
) else if exist "volcano.ico" if exist "logo.png" (
    echo  [SKIP] Assets exist
) else (
    echo  Generating assets...
    "!PYEXE!" gen_assets.py
    if errorlevel 1 echo  [WARN] Asset generation failed.
)
echo.

:: ════════════════════════════════════════════════════════════
::  COPY TO C:\VEMBuild
:: ════════════════════════════════════════════════════════════
echo  Copying to !BUILD_DIR! ...
if exist "!BUILD_DIR!" rmdir /s /q "!BUILD_DIR!"
mkdir "!BUILD_DIR!"

copy /Y "VolcanoEruptionMonitor.pyw"  "!BUILD_DIR!\" >nul
copy /Y "VolcanoEruptionMonitor.spec" "!BUILD_DIR!\" >nul
if exist "gen_assets.py" copy /Y "gen_assets.py" "!BUILD_DIR!\" >nul
if exist "logo.png"      copy /Y "logo.png"      "!BUILD_DIR!\" >nul
if exist "volcano.ico"   copy /Y "volcano.ico"   "!BUILD_DIR!\" >nul

echo  [OK]  Ready
echo.

:: ════════════════════════════════════════════════════════════
::  BUILD
:: ════════════════════════════════════════════════════════════
echo  Building from !BUILD_DIR! ...
echo  ^(~60-120s first time, ~15-30s rebuilds^)
echo.

pushd "!BUILD_DIR!"

echo  Cleaning build cache...
if exist "build" rmdir /s /q "build"
echo.

"!PYEXE!" -m PyInstaller VolcanoEruptionMonitor.spec --noconfirm
set RESULT=!errorlevel!
popd

if "!RESULT!" NEQ "0" (
    echo.
    echo  ============================================================
    echo   BUILD FAILED
    echo  ============================================================
    echo.
    pause & exit /b 1
)

:: ════════════════════════════════════════════════════════════
::  COPY OUTPUT BACK
:: ════════════════════════════════════════════════════════════
set SRC=!BUILD_DIR!\dist\VolcanoEruptionMonitor
set DST=%~dp0dist\VolcanoEruptionMonitor

echo  Copying output...
if exist "!DST!" rmdir /s /q "!DST!"
if not exist "%~dp0dist" mkdir "%~dp0dist"
xcopy /E /I /Q "!SRC!" "!DST!" >nul
echo  [OK]  Output: !DST!
echo.

:: ════════════════════════════════════════════════════════════
::  DONE
:: ════════════════════════════════════════════════════════════
set EXE=!DST!\VolcanoEruptionMonitor.exe

echo  ============================================================
echo   BUILD SUCCEEDED
echo  ============================================================
echo.
if exist "!EXE!" (
    for %%A in ("!EXE!") do (
        echo   EXE  : %%~fA
        echo   Size : %%~zA bytes
    )
)
echo   Dir  : !DST!\
echo.
echo  DISTRIBUTE: zip the dist\VolcanoEruptionMonitor\ folder.
echo.
echo  Launch? [Y/N]
choice /c YN /n /t 8 /d N
if errorlevel 2 goto :end
if exist "!EXE!" start "" "!EXE!"

:end
echo.
endlocal
