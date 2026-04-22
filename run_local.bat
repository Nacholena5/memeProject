@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo ERROR: .venv no existe. Crea el entorno primero.
  exit /b 1
)

if not exist ".env.local" (
  if exist ".env.local.example" copy ".env.local.example" ".env.local" >nul
)

set DATABASE_URL=sqlite:///./meme_research.db
.venv\Scripts\python.exe scripts\ops.py scenario full
start http://127.0.0.1:8000
.venv\Scripts\python.exe scripts\ops.py serve-sqlite --host 127.0.0.1 --port 8000
