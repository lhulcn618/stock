@echo off
setlocal
call "C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\Tools\VsDevCmd.bat" -arch=x64
if errorlevel 1 exit /b %errorlevel%
set "RUSTUP_HOME=D:\rustup"
set "CARGO_HOME=D:\cargo"
set "PATH=D:\cargo\bin;%PATH%"
set "CARGO_TARGET_DIR=D:\stockapp\target-rustlld-serial"
set "CARGO_TARGET_X86_64_PC_WINDOWS_MSVC_LINKER=D:\rustup\toolchains\stable-x86_64-pc-windows-msvc\lib\rustlib\x86_64-pc-windows-msvc\bin\rust-lld.exe"
set "CARGO_INCREMENTAL=0"
set "CARGO_BUILD_PIPELINING=false"
if "%~1"=="" exit /b 0
%*
exit /b %errorlevel%