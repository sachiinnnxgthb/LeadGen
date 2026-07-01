"""Streamlit launcher.

Run the application with:

    streamlit run app.py

Thin entry point that delegates to :func:`lead_intel.ui.app.main`.
"""

from __future__ import annotations

from lead_intel.ui.app import main

main()
