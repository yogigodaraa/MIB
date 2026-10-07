# Copilot instructions for MIB (Mooring Intelligence Backend)

- **Stack:** Python 3.10+, FastAPI, Pydantic v2, Jinja2 templates (`templates/`); Next.js app in `web/`.
- **Run:** `pip install -r requirements.txt`, `python main.py` (port 8000), `pytest`, `ruff check .`. Web: `cd web && npm ci && npm run lint && npm run build`.
- **Layout:** `main.py` wires the routers in `app/api/`. Domain logic lives in `app/services/` (`tension_monitoring.py`: outliers, drift, smoothing, confidence). Models live in `app/models/`. Root-level `dashboard.py`, `enhanced_tension_monitor.py` and `ship_movement_analyzer.py` are the earlier single-file version.
- **Safety thresholds** (`alert_thresholds`: 30 / 70 / 85 / 95 %) drive crew alerts. Changes need tests in `tests/`.
- **Don't:** commit logs (`*.log`), `__pycache__`, `.env`, or real vessel and port data.
