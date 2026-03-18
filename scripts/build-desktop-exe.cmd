@echo off
setlocal

set "ROOT_DIR=%~dp0.."
pushd "%ROOT_DIR%"
if errorlevel 1 exit /b %errorlevel%

call "%ROOT_DIR%\scripts\windows-tauri-env.cmd"
if errorlevel 1 goto :fail

echo [1/3] Building Tauri release executable...
call "%ROOT_DIR%\scripts\windows-tauri-env.cmd" cmd /c npx tauri build --no-bundle
if errorlevel 1 goto :fail

set "OUT_DIR=%ROOT_DIR%\builds"
if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"
if errorlevel 1 goto :fail

set "SOURCE_EXE=%ROOT_DIR%\target-rustlld-serial\release\stock-watch-desktop.exe"
set "LATEST_EXE=%OUT_DIR%\stock-watch-desktop-latest.exe"

echo [2/3] Copying latest executable...
copy /Y "%SOURCE_EXE%" "%LATEST_EXE%" >nul
if errorlevel 1 goto :fail

for /f %%i in ('powershell -NoProfile -Command "(Get-Date).ToString(\"yyyyMMdd-HHmmss\")"') do set "BUILD_STAMP=%%i"
set "STAMPED_EXE=%OUT_DIR%\stock-watch-desktop-%BUILD_STAMP%.exe"

echo [3/3] Creating timestamped executable...
copy /Y "%SOURCE_EXE%" "%STAMPED_EXE%" >nul
if errorlevel 1 goto :fail

echo EXE_READY=%LATEST_EXE%
echo EXE_ARCHIVE=%STAMPED_EXE%

popd
exit /b 0

:fail
set "EXIT_CODE=%errorlevel%"
popd
exit /b %EXIT_CODE%
