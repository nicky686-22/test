echo   https://github.com/nicky686-22/SwarmIA
echo.
echo %GREEN%══════════════════════════════════════════════════════════════%NC%

pause
exit /b 0

REM ============================================
REM Subroutines
REM ============================================

:download_via_curl
echo   Downloading via curl...
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/nicky686-22/SwarmIA/archive/refs/heads/main.zip' -OutFile '%SWARMIA_DIR%\swarmia.zip'"

if exist "%SWARMIA_DIR%\swarmia.zip" (
    echo   Extracting files...
    powershell -Command "Expand-Archive -Path '%SWARMIA_DIR%\swarmia.zip' -DestinationPath '%SWARMIA_DIR%' -Force"
    
    REM Move files from subdirectory
    if exist "%SWARMIA_DIR%\SwarmIA-main" (
        xcopy "%SWARMIA_DIR%\SwarmIA-main\*" "%SWARMIA_DIR%\" /E /I /Y >nul
        rmdir /s /q "%SWARMIA_DIR%\SwarmIA-main" >nul 2>&1
    )
    
    del "%SWARMIA_DIR%\swarmia.zip" >nul 2>&1
) else (
    echo %RED%Failed to download SwarmIA files%NC%
    pause
    exit /b 1
)
exit /b