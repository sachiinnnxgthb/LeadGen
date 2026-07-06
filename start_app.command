#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate
echo "Starting Lead Intelligence app... your browser will open automatically."
echo "To stop it later: close this window or press Control + C."
streamlit run app.py
