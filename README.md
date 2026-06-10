# AI Failure Observatory

Deterministic AI agent reliability platform: ingest → validate → evaluate → classify → transform (dbt) → investigate (LLM optional).

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
cp .env.example .env
python scripts/initialize_warehouse.py
python scripts/generate_synthetic_data.py --count 10000
python scripts/run_local_pipeline.py
pytest tests/unit tests/integration -v
```

See `PROJECT_SPEC.md` for full architecture.
