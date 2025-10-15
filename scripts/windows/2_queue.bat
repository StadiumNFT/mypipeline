@echo off
setlocal
pushd "%~dp0\..\.."
echo.
echo =============================================
echo   Create batch job(s) from Scans_Ready
echo =============================================
echo.
set /p BATCH_SIZE=Enter batch size [default: 20]: 
if "%BATCH_SIZE%"=="" set BATCH_SIZE=20
python -m pipeline.run queue --batch-size %BATCH_SIZE%
if errorlevel 1 (
    echo.
    echo Queue step failed. Review the log output above.
) else (
    echo.
    echo Queue step complete.
)
echo.
pause
popd
endlocal
