@echo off
python -m venv .venv
call .venv\Scripts\activate
pip install -r requirements.txt
python main.py
echo Output written to ..\support_tickets\output.csv
