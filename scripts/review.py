#!/usr/bin/env python3
"""Generate substantive biblical strengths/weaknesses reviews for transcripts."""
from __future__ import annotations
import argparse, json, os, re, sqlite3
from pathlib import Path
import requests
try:
 from dotenv import load_dotenv
 load_dotenv()
except ImportError: pass
def parse_json(text):
 text=text.strip(); text=re.sub(r'^```(?:json)?\s*|\s*```$','',text,flags=re.I|re.S); return json.loads(text)
def as_text(value):
 if isinstance(value,str): return value
 if isinstance(value,dict): return ' '.join(str(v) for v in value.values())
 if isinstance(value,list): return ' '.join(str(v) for v in value)
 return str(value)
def main(limit=20,force=False):
 key=os.getenv('OPEN_ROUTER') or os.getenv('OPENROUTER_API_KEY') or os.getenv('OPENAI_API_KEY')
 if not key: raise SystemExit('Set OPEN_ROUTER/OPENROUTER_API_KEY; no reviews generated')
 db=sqlite3.connect('data/sermons.sqlite3'); db.row_factory=sqlite3.Row
 where="transcript_status='complete' AND transcript!=''"+("" if force else " AND (review_status IS NULL OR review_status='pending')")
 rows=db.execute(f"SELECT id,title,transcript FROM sermons WHERE {where} ORDER BY published_at DESC LIMIT ?",(limit,)).fetchall()
 base='https://openrouter.ai/api/v1'; model=os.getenv('OPENROUTER_REVIEW_MODEL','deepseek/deepseek-v4-flash')
 for row in rows:
  t=row['transcript']; excerpt=t[:8500]+('\n...[middle omitted]...\n'+t[-6500:] if len(t)>15000 else '')
  prompt=f"""Review this sermon according to biblical Christianity, not according to any denomination’s distinctives. Use Scripture and the historic Christian essentials as the standard: the one triune God; Christ’s true deity and humanity, incarnation, sinless life, substitutionary death, bodily resurrection, and return; human sin and judgment; salvation by grace through faith with repentance; justification and adoption; and Spirit-enabled sanctification. Return ONLY valid JSON with exactly two string keys: strengths and weaknesses. Each value should be 1-2 concise paragraphs (roughly 50-90 words). Evaluate the sermon’s actual content: (1) whether it handles the stated biblical passage faithfully and in context, (2) whether its doctrine accords with biblical Christianity, (3) whether its gospel and view of sanctification are clear, and (4) whether its applications follow the text. Strengths must identify concrete exegetical, doctrinal, gospel, or pastoral virtues. Weaknesses must identify concrete omissions, imbalances, interpretive leaps, or application risks; do not invent faults or criticize denominational differences. Do not discuss transcription quality, disclaimers, or verification. Do not say “the sermon claims”; write the evaluation directly.\n\nTitle: {row['title']}\nTranscript:\n{excerpt}"""
  headers={'Authorization':f'Bearer {key}','Content-Type':'application/json','HTTP-Referer':os.getenv('SITE_URL','http://localhost:4173'),'X-Title':'GraceLife sermon archive'}
  res=requests.post(base+'/chat/completions',headers=headers,json={'model':model,'temperature':0.15,'max_tokens':1400,'messages':[{'role':'user','content':prompt}]},timeout=240); res.raise_for_status()
  msg=res.json()['choices'][0]['message']; raw=msg.get('content') or ''
  if not raw: raise RuntimeError(f'LLM returned no review for {row["id"]}')
  review=parse_json(raw); strengths=as_text(review.get('strengths','')).strip(); weaknesses=as_text(review.get('weaknesses','')).strip()
  if not strengths or not weaknesses: raise RuntimeError(f'LLM review missing strengths/weaknesses for {row["id"]}')
  db.execute("UPDATE sermons SET strengths=?,weaknesses=?,review_status='reviewed',updated_at=CURRENT_TIMESTAMP WHERE id=?",(strengths,weaknesses,row['id'])); db.commit(); print(row['id'],'reviewed')
 rows2=[dict(r) for r in db.execute("SELECT * FROM sermons WHERE is_sermon=1 ORDER BY CASE WHEN published_at='' THEN 1 ELSE 0 END,published_at DESC LIMIT 20")]; Path('data/sermons.json').write_text(json.dumps(rows2,indent=2,ensure_ascii=False)); db.close()
if __name__=='__main__':
 ap=argparse.ArgumentParser(); ap.add_argument('--limit',type=int,default=20); ap.add_argument('--force',action='store_true'); a=ap.parse_args(); main(a.limit,a.force)
