#!/bin/sh
set -eu
"/Users/samuelvarghese/.prime/agent/kernel-venv/bin/python" scripts/worker.py --limit 7 --model tiny.en
"/Users/samuelvarghese/.prime/agent/kernel-venv/bin/python" scripts/summarize.py --limit 20
"/Users/samuelvarghese/.prime/agent/kernel-venv/bin/python" scripts/build.py
