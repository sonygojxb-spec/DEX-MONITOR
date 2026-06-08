# DEX Trading Agent

Automated monitoring, analysis, and trading for tokens on decentralized exchanges (initial target: Solana).

## Layout

```
dex_agent/          # implementation package
  models/           # data models and enums
  providers/        # provider interfaces, fakes, adapters
  repositories/     # persistence abstractions + in-memory repos
  analysis/         # Security_Inspector, Backend_Analyzer, Metrics_Tracker
  decision/         # Signal_Engine, Risk_Manager
  execution/        # Trade_Executor, Authorization_Manager
  control/          # Monitoring Orchestrator, Data_Ingestor
  notify/           # Notifier and channels
  config/           # Config_Manager
  audit/            # Audit / persistence service
  result.py         # shared Result type
  errors.py         # typed error taxonomy
tests/              # test tree mirroring dex_agent/
```

## Development

Install test dependencies and run the suite:

```
pip install -e ".[test]"
pytest
```

Property-based tests use Hypothesis with a default profile of `max_examples=100`
(registered in `tests/conftest.py`).
