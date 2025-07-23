@echo off
cd /d C:\Users\User\Project_Big\custom_dataset
start python -m http.server 8000
timeout /t 2 >nul
start cmd /k lt --port 8000
