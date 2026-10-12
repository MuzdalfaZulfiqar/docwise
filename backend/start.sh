#!/bin/sh
# Free hosts give one web service, so run the ARQ worker (auto-restarting) beside the API.
# They share this container's disk, which is how the worker finds files the API saved.
( while true; do arq app.worker.WorkerSettings; echo "worker exited, restarting in 2s"; sleep 2; done ) &
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
