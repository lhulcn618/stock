@echo off
setlocal

set "ROOT_DIR=%~dp0.."
pushd "%ROOT_DIR%"
if errorlevel 1 exit /b %errorlevel%

PowerShell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%\scripts\build-desktop-exe.ps1"
if errorlevel 1 goto :fail

popd
exit /b 0

:fail
set "EXIT_CODE=%errorlevel%"
popd
exit /b %EXIT_CODE%
