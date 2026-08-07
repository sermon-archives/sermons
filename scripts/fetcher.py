#!/usr/bin/env python3
"""Periodic, rate-limited YouTube metadata fetcher and Turso queue updater."""
from __future__ import annotations
import argparse, os, subprocess, sys, time
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
ROOT=Path(__file__).parents[1]
def once(limit: int):
    subprocess.run([sys.executable,'scripts/collect.py','--limit',str(limit)],cwd=ROOT,check=True)
    subprocess.run([sys.executable,'scripts/job_queue.py','enqueue','--limit',str(limit)],cwd=ROOT,check=True)
    if os.getenv('TURSO_DATABASE_URL') and os.getenv('TURSO_AUTH_TOKEN'):
        subprocess.run([sys.executable,'scripts/turso_sync.py'],cwd=ROOT,check=True)
    print('fetch cycle complete',flush=True)
def main(interval,limit,run_once):
    while True:
        try: once(limit)
        except Exception as exc: print(f'fetch cycle failed: {exc}',file=sys.stderr,flush=True)
        if run_once: return
        print(f'next fetch in {interval} seconds',flush=True); time.sleep(interval)
if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--interval',type=int,default=21600); ap.add_argument('--limit',type=int,default=20); ap.add_argument('--once',action='store_true'); a=ap.parse_args(); main(a.interval,a.limit,a.once)
