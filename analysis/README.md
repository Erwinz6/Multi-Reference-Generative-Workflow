# Analysis Scripts

This directory contains scripts for the thesis-oriented performance experiment workflow.

- `run_performance_batch.py`: sequentially triggers the orchestrator endpoint.
- `merge_logs.py`: merges multi-stage JSONL logs into one CSV table.
- `analyze_performance.py`: computes end-to-end performance metrics from merged runs.

The scripts preserve the original experiment logic while using repository-relative paths for public release.
