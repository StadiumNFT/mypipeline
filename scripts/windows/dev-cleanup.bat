@echo off
title Ageless Pipeline Dev Cleanup
echo ============================================
echo   AGELESS PIPELINE - DEVELOPMENT CLEANUP
echo ============================================
echo.

set ROOT=%~dp0..\..\

echo [1/6] Removing Node.js modules...
if exist "%ROOT%AgelessPipelineUI\node_modules" (
    rmdir /s /q "%ROOT%AgelessPipelineUI\node_modules"
)

echo [2/6] Clearing Python build caches...
for /r "%ROOT%" %%d in (__pycache__) do (
    if exist "%%d" rmdir /s /q "%%d"
)

echo [3/6] Cleaning pipeline output folders...
for %%F in (json txt csv batches logs) do (
    if exist "%ROOT%pipeline\output\%%F" (
        rmdir /s /q "%ROOT%pipeline\output\%%F"
        mkdir "%ROOT%pipeline\output\%%F"
        echo Created fresh folder: pipeline\output\%%F
    )
)

echo [4/6] Cleaning Electron runtime cache...
if exist "%ROOT%AgelessPipelineUI\Cache" rmdir /s /q "%ROOT%AgelessPipelineUI\Cache"
if exist "%ROOT%AgelessPipelineUI\UserData" rmdir /s /q "%ROOT%AgelessPipelineUI\UserData"

echo [5/6] Cleaning temporary scan errors...
if exist "%ROOT%Scans_Error" (
    rmdir /s /q "%ROOT%Scans_Error"
    mkdir "%ROOT%Scans_Error"
)

echo [6/6] Removing logs and temp files...
del /s /q "%ROOT%*.log" >nul 2>&1

echo.
echo Cleanup complete! ✅
echo Repository is now fresh and ready for development.
pause
