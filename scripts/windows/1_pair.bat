@echo off
setlocal
pushd "%~dp0\..\.."
echo.
echo =============================================
echo   Pair front/back scans from Scans_Inbox
echo =============================================
echo.
python -m pipeline.run pair
if errorlevel 1 (
    echo.
    echo Pairing step failed. Review the log output above.
) else (
    echo.
    echo Pairing complete.
)
echo.
pause
popd
endlocal
