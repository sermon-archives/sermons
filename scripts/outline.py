#!/usr/bin/env python3
"""Generate a text-grounded sermon outline with OpenRouter."""
from __future__ import annotations
import argparse, json, os, re as _re, sqlite3
from pathlib import Path
import requests
try:
 from dotenv import load_dotenv
 load_dotenv()
except ImportError: pass
def clean_title(raw):
    parts=[x.strip() for x in _re.split(r"\s*\|\s*|\s+—\s+", raw) if x.strip()]
    books=r"(?:1|2|3)?\s*(?:Samuel|Kings|Chronicles|Corinthians|Thessalonians|Timothy|Peter|John|Genesis|Exodus|Leviticus|Numbers|Deuteronomy|Joshua|Judges|Ruth|Ezra|Nehemiah|Esther|Job|Psalms?|Proverbs|Ecclesiastes|Song of Solomon|Isaiah|Jeremiah|Lamentations|Ezekiel|Daniel|Hosea|Joel|Amos|Obadiah|Jonah|Micah|Nahum|Habakkuk|Zephaniah|Haggai|Zechariah|Malachi|Matthew|Mark|Luke|Acts|Romans|Galatians|Ephesians|Philippians|Colossians|Titus|Philemon|Hebrews|James|Jude|Revelation)"
    kept=[]
    for part in parts:
        if _re.search(r"\bPastor\b",part,_re.I): continue
        if _re.search(rf"\b{books}\s+\d{{1,3}}",part,_re.I): continue
        kept.append(part)
    if len(kept)>1 and _re.fullmatch(r"[A-Z][A-Za-z.'-]+(?:\s+[A-Z][A-Za-z.'-]+){1,3}",kept[-1]): kept.pop()
    return _re.sub(r"\s+"," "," — ".join(kept or parts)).strip(" -—")

def main(limit=20,force=False):
 key=os.getenv('OPEN_ROUTER') or os.getenv('OPENROUTER_API_KEY') or os.getenv('OPENAI_API_KEY')
 if not key: raise SystemExit('Set OPEN_ROUTER/OPENROUTER_API_KEY; no outlines generated')
 db=sqlite3.connect('data/sermons.sqlite3'); db.row_factory=sqlite3.Row
 try: db.execute("ALTER TABLE sermons ADD COLUMN outline TEXT DEFAULT ''")
 except sqlite3.OperationalError: pass
 where="transcript_status='complete' AND transcript!=''"+("" if force else " AND (outline IS NULL OR outline='')")
 rows=db.execute(f"SELECT id,title,transcript FROM sermons WHERE {where} ORDER BY published_at DESC LIMIT ?",(limit,)).fetchall()
 model=os.getenv('OPENROUTER_OUTLINE_MODEL','deepseek/deepseek-v4-flash'); url='https://openrouter.ai/api/v1/chat/completions'
 for row in rows:
  t=row['transcript']; excerpt=t[:8000]+('\n...[middle omitted]...\n'+t[-5000:] if len(t)>13000 else '')
  prompt=f"""Create a brief sermon outline from this transcript. Begin with a single H1 heading that is the sermon title ONLY (no Bible reference and no pastor name). On the next line state the primary biblical text separately. Then give 3–5 short numbered main points, each a single concise line (ideally under 18 words). Skip sub-points except where essential. Do NOT repeat the Bible reference in the title heading. Preserve the actual progression and main applications. Do not invent, pad, evaluate, mention transcription quality, or say “the sermon claims.” Title: {clean_title(row['title'])}\nTranscript:\n{excerpt}"""
  res=requests.post(url,headers={'Authorization':f'Bearer {key}','Content-Type':'application/json','HTTP-Referer':os.getenv('SITE_URL','http://localhost:4173'),'X-Title':'GraceLife sermon archive'},json={'model':model,'temperature':0.1,'max_tokens':1800,'messages':[{'role':'user','content':prompt}]},timeout=240); res.raise_for_status(); out=(res.json()['choices'][0]['message'].get('content') or '').strip()
  if not out: raise RuntimeError(f'LLM returned no outline for {row["id"]}')
  db.execute("UPDATE sermons SET outline=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(out,row['id'])); db.commit(); print(row['id'],'outlined')
 rows2=[dict(r) for r in db.execute("SELECT * FROM sermons WHERE is_sermon=1 ORDER BY CASE WHEN published_at='' THEN 1 ELSE 0 END,published_at DESC LIMIT 20")]; Path('data/sermons.json').write_text(json.dumps(rows2,indent=2,ensure_ascii=False)); db.close()
if __name__=='__main__':
 ap=argparse.ArgumentParser(); ap.add_argument('--limit',type=int,default=20); ap.add_argument('--force',action='store_true'); a=ap.parse_args(); main(a.limit,a.force)
