@echo off
cd /d %~dp0
call venv\Scripts\activate
set PYTHONPATH=%CD%\src
uvicorn api:app --host 127.0.0.1 --port 8000 --reload
