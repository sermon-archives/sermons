#!/usr/bin/env python3
"""Generate reflective devotional questions tied to the sermon."""
from __future__ import annotations
import argparse, json, os, sqlite3
from pathlib import Path
import requests
try:
 from dotenv import load_dotenv
 load_dotenv()
except ImportError: pass
def main(limit=20,force=False):
 key=os.getenv('OPEN_ROUTER') or os.getenv('OPENROUTER_API_KEY') or os.getenv('OPENAI_API_KEY')
 if not key: raise SystemExit('Set OPEN_ROUTER/OPENROUTER_API_KEY; no devotional questions generated')
 db=sqlite3.connect('data/sermons.sqlite3'); db.row_factory=sqlite3.Row
 try: db.execute("ALTER TABLE sermons ADD COLUMN devotional_questions TEXT DEFAULT ''")
 except sqlite3.OperationalError: pass
 where="transcript_status='complete' AND transcript!=''"+("" if force else " AND (devotional_questions IS NULL OR devotional_questions='')")
 rows=db.execute(f"SELECT id,title,transcript FROM sermons WHERE {where} ORDER BY published_at DESC LIMIT ?",(limit,)).fetchall()
 model=os.getenv('OPENROUTER_DEVOTIONAL_MODEL','deepseek/deepseek-v4-flash'); url='https://openrouter.ai/api/v1/chat/completions'
 for row in rows:
  t=row['transcript']; excerpt=t[:8000]+('\n...[middle omitted]...\n'+t[-5000:] if len(t)>13000 else '')
  prompt=f"""Write 5 reflective devotional questions a reader should ask themselves based on this sermon. Base each question on the sermon’s actual teaching and application; questions should prompt self-examination, prayer, gratitude, and obedient response in light of Scripture and the gospel. Return only a Markdown list of 5 numbered questions. Do not invent doctrine, do not evaluate the sermon, and do not mention transcription quality. Title: {row['title']}\nTranscript:\n{excerpt}"""
  res=requests.post(url,headers={'Authorization':f'Bearer {key}','Content-Type':'application/json','HTTP-Referer':os.getenv('SITE_URL','http://localhost:4173'),'X-Title':'GraceLife sermon archive'},json={'model':model,'temperature':0.2,'max_tokens':900,'messages':[{'role':'user','content':prompt}]},timeout=240); res.raise_for_status(); out=(res.json()['choices'][0]['message'].get('content') or '').strip()
  if not out: raise RuntimeError(f'LLM returned no devotional questions for {row["id"]}')
  db.execute("UPDATE sermons SET devotional_questions=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(out,row['id'])); db.commit(); print(row['id'],'devotional')
 rows2=[dict(r) for r in db.execute("SELECT * FROM sermons WHERE is_sermon=1 ORDER BY CASE WHEN published_at='' THEN 1 ELSE 0 END,published_at DESC LIMIT 20")]; Path('data/sermons.json').write_text(json.dumps(rows2,indent=2,ensure_ascii=False)); db.close()
if __name__=='__main__':
 ap=argparse.ArgumentParser(); ap.add_argument('--limit',type=int,default=20); ap.add_argument('--force',action='store_true'); a=ap.parse_args(); main(a.limit,a.force)
