@echo off
setlocal
pushd "%~dp0\..\.."
echo.
echo =============================================
echo   Post-process a batch job
echo =============================================
echo.
set /p JOB_ID=Enter job id to post-process: 
if "%JOB_ID%"=="" (
    echo.
    echo Job id is required. Aborting.
    goto finish
)
python -m pipeline.run post --job-id "%JOB_ID%"
if errorlevel 1 (
    echo.
    echo Post-processing step failed. Review the log output above.
) else (
    echo.
    echo Post-processing complete.
)
:finish
echo.
pause
popd
endlocal
