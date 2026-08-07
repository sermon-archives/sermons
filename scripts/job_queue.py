#!/usr/bin/env python3
"""Maintain a durable, SQLite-backed transcription queue.

With TURSO_* set, run scripts/turso_sync.py after queue changes. The local
SQLite file is deliberately the worker's cache because audio/model work is
local; Turso remains the durable coordination/database layer.
"""
from __future__ import annotations
import argparse, sqlite3
from pathlib import Path

def db():
    con=sqlite3.connect('data/sermons.sqlite3', timeout=30); con.row_factory=sqlite3.Row
    con.executescript(Path('db/schema.sql').read_text()); return con

def enqueue(limit=20):
    con=db(); rows=con.execute("SELECT id FROM sermons WHERE is_sermon=1 AND transcript_status!='complete' ORDER BY CASE WHEN published_at='' THEN 1 ELSE 0 END, published_at DESC LIMIT ?",(limit,)).fetchall()
    for row in rows: con.execute("INSERT OR IGNORE INTO transcription_queue(sermon_id) VALUES(?)",(row['id'],))
    con.commit(); print(f'queued {len(rows)} sermon records'); con.close()

def show():
    con=db(); rows=con.execute('SELECT q.*,s.title FROM transcription_queue q JOIN sermons s ON s.id=q.sermon_id ORDER BY q.priority,q.created_at').fetchall()
    for r in rows: print(f"{r['status']:10} attempts={r['attempts']} {r['sermon_id']} {r['title']}")
    con.close()
if __name__=='__main__':
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd',required=True)
    e=sub.add_parser('enqueue'); e.add_argument('--limit',type=int,default=20)
    sub.add_parser('show'); a=ap.parse_args()
    enqueue(a.limit) if a.cmd=='enqueue' else show()
