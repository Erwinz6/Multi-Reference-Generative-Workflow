# Performance Experiment Workflow

This repository includes a minimal experiment toolchain for end-to-end response analysis.

## Step 1: Batch trigger

```bash
python analysis/run_performance_batch.py
```

## Step 2: Merge logs

```bash
python analysis/merge_logs.py
```

## Step 3: Analyze performance

```bash
python analysis/analyze_performance.py
```

## Notes

- `run_performance_batch.py` only triggers the orchestrator endpoint in sequence.
- The actual completion of all runs depends on the backend queue and generation time.
- Log completeness should be verified before trusting the final summary statistics.
