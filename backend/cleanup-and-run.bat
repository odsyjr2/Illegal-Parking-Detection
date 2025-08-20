@echo off
echo ==========================================
echo Spring Boot Port 8080 Cleanup and Run
echo ==========================================

echo.
echo [1/3] Cleaning up any existing processes on port 8080...

REM Find and kill processes using port 8080
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8080" ^| findstr "LISTENING"') do (
    echo Terminating process %%a using port 8080
    taskkill /F /PID %%a >nul 2>&1
)

REM Kill any lingering Java processes
taskkill /F /IM java.exe >nul 2>&1

echo Port cleanup completed.

echo.
echo [2/3] Waiting for processes to terminate...
timeout /t 2 /nobreak >nul

echo.
echo [3/3] Starting Spring Boot backend...
echo ==========================================

gradlew bootRun

echo.
echo Backend server has stopped.
echo ==========================================