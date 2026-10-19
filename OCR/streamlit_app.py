"""Backward-compatible entry point for the canonical Streamlit frontend."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from frontend.app import main

main()
