# Local Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .
cp .env.example .env
python scripts/initialize_warehouse.py
python scripts/generate_synthetic_data.py --count 10000
python scripts/run_local_pipeline.py --skip-generate
python scripts/refresh_metadata.py
```

## Run Services

```bash
streamlit run app/dashboard/streamlit_app.py
uvicorn app.api.main:app --reload --host localhost --port 8000
```

No Airflow, cloud credentials, or paid APIs required.
