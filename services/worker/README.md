# Worker Service

Async background runtime for jobs that should not block API requests:

- public transport feed ingestion
- heatmap aggregation
- notification scheduling

## Local dev

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
arq worker.queue.WorkerSettings
```
