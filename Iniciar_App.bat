@echo off
title Pipeline GTFS - Streamlit
echo ===================================================
echo Iniciando a Aplicacao do Pipeline GTFS (Streamlit)
echo ===================================================
echo.
echo Ativando ambiente virtual...
call .venv\Scripts\activate.bat

echo.
echo Iniciando o servidor... (Nao feche esta janela)
echo.
python -m streamlit run src/app.py

pause
