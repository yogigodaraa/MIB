# MIB — Mooring Intelligent Backend

[![CI](https://github.com/yogigodaraa/MIB/actions/workflows/ci.yml/badge.svg)](https://github.com/yogigodaraa/MIB/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Live demo:** <https://mib-psi.vercel.app>

Real-time BHP mooring-hook tension monitoring with predictive alerts and a visual crew dashboard.

## What it does

Simulates and analyzes real-time tension measurements from mooring hooks and bollards at a port. Predicts when tension will breach safety thresholds, alerts the crew visually, and tracks ship movements against a four-tier safety state.

**Tension forecasting** — linear-regression trending over recent readings, with time-to-critical calculations.

**Alert tiers**

- Safe — 0–30%
- Caution — 30–70%
- Warning — 70–85%
- Critical — 85%+ (emergency)

Other features include outlier detection with calibration drift monitoring, color-coded tension meters with action buttons, ship movement tracking with 3D hook visualization, and polling updates every 2–3 seconds.

## Tech stack

- Python 3.10+
- FastAPI + Uvicorn
- Pydantic (data contracts)
- Jinja2 (server-rendered templates)
- colorlog, httpx, python-multipart

## Getting started

```bash
pip install -r requirements.txt
python main.py             # http://localhost:8000
```

Optional: run the separate ship-data client to feed simulated readings:

```bash
pip install -r ship_client_requirements.txt
python ship_data_client.py
```

Dashboard at <http://localhost:8000>.

## Project structure

```
main.py                            FastAPI app entry
dashboard.py                       Dashboard routes
enhanced_tension_monitor.py        Tension prediction + alert logic
ship_data_client.py                Simulated sensor feed
ship_movement_analyzer.py          3D hook / ship movement tracking
app/                               Routers, services, models
templates/                         Jinja2 HTML templates
openapi.json                       Generated API spec
TECHNICAL_DOCUMENTATION.md         Full architecture
COMMUNICATION_ARCHITECTURE.md      Service communication design
```

## Status

Active development. See `TECHNICAL_DOCUMENTATION.md` for deep dive.

## Tests

```bash
pip install -r requirements.txt
pytest          # smoke tests: /health, steady readings, spike → outlier
ruff check .
cd web && npm ci && npm run lint && npm run build
```

## Related projects

Part of the BHP / UWA mooring work. Each repo takes a different approach to the same problem:

- [bhp](https://github.com/yogigodaraa/bhp): Mooring Portal (Next.js) with a four-pillar data-quality pipeline
- [TensionBot](https://github.com/yogigodaraa/TensionBot): synthetic sensor-data generator + live dashboard

