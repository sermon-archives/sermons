#!/usr/bin/env python3
"""Reflow already stored Whisper transcripts into readable paragraphs."""
import json, sqlite3
from pathlib import Path
from transcript_format import reflow_transcript

def main():
    db=sqlite3.connect('data/sermons.sqlite3'); db.row_factory=sqlite3.Row
    for row in db.execute("SELECT id, transcript FROM sermons WHERE transcript_status='complete' AND transcript!=''").fetchall():
        db.execute("UPDATE sermons SET transcript=?,updated_at=CURRENT_TIMESTAMP WHERE id=?", (reflow_transcript(row['transcript'], punctuate=True),row['id']))
    db.commit()
    rows=[dict(r) for r in db.execute("SELECT * FROM sermons WHERE is_sermon=1 ORDER BY CASE WHEN published_at='' THEN 1 ELSE 0 END,published_at DESC LIMIT 20")]
    Path('data/sermons.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False)); db.close()
    print(f'reflowed {sum(1 for r in rows if r["transcript_status"]=="complete")} transcripts')
if __name__=='__main__': main()
