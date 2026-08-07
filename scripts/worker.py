#!/usr/bin/env python3
"""Claim and process one-at-a-time transcription jobs from SQLite/Turso-synced queue."""
from __future__ import annotations
import argparse, json, os, re, sqlite3, subprocess, sys
from pathlib import Path
from datetime import datetime, timezone
from transcript_format import reflow_transcript
AUDIO=Path("var/audio"); AUDIO.mkdir(parents=True,exist_ok=True)

def open_db():
    db=sqlite3.connect("data/sermons.sqlite3",timeout=30); db.row_factory=sqlite3.Row
    db.executescript(Path("db/schema.sql").read_text());
    if db.execute("SELECT COUNT(*) FROM sermons").fetchone()[0] == 0 and Path("data/sermons.json").exists():
        for r in json.loads(Path("data/sermons.json").read_text()):
            db.execute("INSERT OR IGNORE INTO sermons(id,title,published_at,url,description,is_sermon,classification_reason,transcript,transcript_engine,transcript_status,strengths,weaknesses,review_status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (r['id'],r['title'],r.get('published_at',''),r['url'],r.get('description',''),r.get('is_sermon',1),r.get('classification_reason',''),r.get('transcript',''),r.get('transcript_engine',''),r.get('transcript_status','pending'),r.get('strengths',''),r.get('weaknesses',''),r.get('review_status','pending')))
    db.execute("INSERT OR IGNORE INTO transcription_queue(sermon_id) SELECT id FROM sermons WHERE is_sermon=1 AND transcript_status!='complete'")
    db.commit(); return db

def claim(db):
    # Recover a runner killed during a download after six hours.
    db.execute("UPDATE transcription_queue SET status='pending',locked_at=NULL,updated_at=CURRENT_TIMESTAMP WHERE status='processing' AND locked_at < datetime('now','-6 hours')")
    db.commit(); db.execute('BEGIN IMMEDIATE')
    row=db.execute("SELECT q.sermon_id FROM transcription_queue q JOIN sermons s ON s.id=q.sermon_id WHERE q.status IN ('pending','downloaded') AND q.available_at<=CURRENT_TIMESTAMP AND s.transcript_status!='complete' ORDER BY CASE WHEN q.status='downloaded' THEN 0 ELSE 1 END,q.priority,q.created_at LIMIT 1").fetchone()
    if not row: db.commit(); return None
    db.execute("UPDATE transcription_queue SET status='processing',attempts=attempts+1,locked_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP WHERE sermon_id=?",(row['sermon_id'],)); db.commit()
    return db.execute("SELECT * FROM sermons WHERE id=?",(row['sermon_id'],)).fetchone()

def finish(db,vid,status,error=''):
    qstatus='completed' if status=='complete' else ('downloaded' if status=='downloaded' else 'failed')
    db.execute("UPDATE transcription_queue SET status=?,last_error=?,locked_at=NULL,available_at=CASE WHEN ?='failed' THEN datetime('now','+6 hours') ELSE CURRENT_TIMESTAMP END,updated_at=CURRENT_TIMESTAMP WHERE sermon_id=?",(qstatus,error,status,vid)); db.commit()

def transcribe(audio: Path, model_name: str) -> tuple[str,str]:
    try: from faster_whisper import WhisperModel
    except ImportError: raise SystemExit("Install faster-whisper first: uv pip install -r requirements.txt")
    model=WhisperModel(model_name, device="auto", compute_type="int8")
    segments,_=model.transcribe(str(audio), vad_filter=True, beam_size=5)
    text=[]
    for seg in segments:
        line=re.sub(r"\s+"," ",seg.text).strip()
        if line: text.append(line)
    return reflow_transcript("\n".join(text), punctuate=os.getenv("PUNCTUATE_TRANSCRIPTS","0")=="1"), f"faster-whisper:{model_name}"

def export(db):
    rows=[dict(r) for r in db.execute("SELECT * FROM sermons WHERE is_sermon=1 ORDER BY CASE WHEN published_at='' THEN 1 ELSE 0 END,published_at DESC LIMIT 20")]
    Path("data").mkdir(exist_ok=True); Path("data/sermons.json").write_text(json.dumps(rows,indent=2,ensure_ascii=False))

def main(limit,model,download_only=False):
    db=open_db(); done=0
    while done<limit:
        row=claim(db)
        if not row: print('queue is empty'); break
        done+=1
        vid=row['id']; audio=AUDIO/f"{vid}.m4a"
        try:
            if not audio.exists():
                subprocess.run([sys.executable,"-m","yt_dlp","--no-playlist","--format","bestaudio/best","--extract-audio","--audio-format","m4a","--sleep-requests","2","--sleep-interval","5","--max-sleep-interval","12","--concurrent-fragments","1","--retries","3","--fragment-retries","3","--output",str(audio),row['url']],check=True,timeout=3600)
            if download_only:
                finish(db,vid,'complete' if False else 'downloaded'); print(f'downloaded {vid}: {audio.stat().st_size/1024/1024:.1f} MiB'); continue
            text,engine=transcribe(audio,model)
            db.execute("UPDATE sermons SET transcript=?,transcript_engine=?,transcript_status='complete',updated_at=CURRENT_TIMESTAMP WHERE id=?",(text,engine,vid)); db.commit(); finish(db,vid,'complete'); print(f"completed {vid}: {len(text)} chars")
        except Exception as exc:
            db.execute("UPDATE sermons SET transcript_status='pending',updated_at=CURRENT_TIMESTAMP WHERE id=?",(vid,)); db.commit(); finish(db,vid,'failed',str(exc)); print(f"failed {vid}: {exc}",file=sys.stderr)
        finally:
            if not download_only and os.getenv('KEEP_AUDIO','0')!='1' and audio.exists(): audio.unlink()
    export(db); db.close()
if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--limit',type=int,default=1); ap.add_argument('--model',default=os.getenv('WHISPER_MODEL','small.en')); ap.add_argument('--download-only',action='store_true'); a=ap.parse_args(); main(a.limit,a.model,a.download_only)
