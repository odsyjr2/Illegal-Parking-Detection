@echo off
echo Checking port 8080 status...
echo.

netstat -ano | findstr ":8080"

if errorlevel 1 (
    echo Port 8080 is FREE - Ready to start backend
    echo.
    echo You can now run: gradlew bootRun
) else (
    echo Port 8080 is OCCUPIED by the processes shown above
    echo.
    echo To clean up, run: cleanup-and-run.bat
    echo Or manually kill the processes using: taskkill /F /PID ^<process_id^>
)

pause