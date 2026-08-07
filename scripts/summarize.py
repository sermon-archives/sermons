#!/usr/bin/env python3
"""Generate concise sermon summaries with an OpenAI-compatible LLM."""
from __future__ import annotations
import argparse, json, os, sqlite3
from pathlib import Path
import requests
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def main(limit=20, force=False):
    openrouter=bool(os.getenv("OPEN_ROUTER") or os.getenv("OPENROUTER_API_KEY"))
    key=os.getenv("OPEN_ROUTER") or os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not key: raise SystemExit("Set OPENROUTER_API_KEY or OPENAI_API_KEY; no summaries were generated")
    db=sqlite3.connect("data/sermons.sqlite3"); db.row_factory=sqlite3.Row
    try: db.execute("ALTER TABLE sermons ADD COLUMN summary TEXT DEFAULT ''")
    except sqlite3.OperationalError: pass
    where="transcript_status='complete' AND transcript!=''" + ("" if force else " AND (summary IS NULL OR summary='')")
    rows=db.execute(f"SELECT id,title,transcript FROM sermons WHERE {where} ORDER BY published_at DESC LIMIT ?",(limit,)).fetchall()
    default_base="https://openrouter.ai/api/v1" if openrouter else "https://api.openai.com/v1"
    url=os.getenv("OPENAI_BASE_URL",default_base).rstrip("/")+"/chat/completions"
    model=os.getenv("OPENROUTER_MODEL" if openrouter else "OPENAI_MODEL", "deepseek/deepseek-v4-flash-0731" if openrouter else "gpt-4o-mini")
    for row in rows:
        t=row["transcript"]; excerpt=t[:7000] + ("\n...[middle omitted]...\n"+t[-5000:] if len(t)>12000 else "")
        prompt=f"""Summarize this Christian sermon in 150–200 words, using a clear paragraph or two. Ignore greetings, travel, announcements, and fellowship remarks. State the main biblical text, central teaching, and principal application directly; do not begin with phrases such as ‘the sermon claims’ or ‘the speaker says’. Do not invent anything, do not evaluate the sermon, and do not mention transcription quality.\n\nTitle: {row['title']}\nTranscript:\n{excerpt}"""
        headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"}
        if openrouter: headers.update({"HTTP-Referer":os.getenv("SITE_URL","http://localhost:4173"),"X-Title":"GraceLife sermon archive"})
        res=requests.post(url,headers=headers,json={"model":model,"temperature":0.2,"max_tokens":2500,"reasoning":{"exclude":True},"messages":[{"role":"user","content":prompt}]},timeout=120)
        res.raise_for_status(); message=res.json()["choices"][0]["message"]; summary=(message.get("content") or "").strip()
        if not summary: raise RuntimeError("LLM returned no summary content; increase max_tokens or choose a non-reasoning model")
        db.execute("UPDATE sermons SET summary=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(summary,row["id"])); db.commit(); print(row["id"],summary)
    rows2=[dict(r) for r in db.execute("SELECT * FROM sermons WHERE is_sermon=1 ORDER BY CASE WHEN published_at='' THEN 1 ELSE 0 END,published_at DESC LIMIT 20")]
    Path("data/sermons.json").write_text(json.dumps(rows2,indent=2,ensure_ascii=False)); db.close()
if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--limit",type=int,default=20); ap.add_argument("--force",action="store_true"); a=ap.parse_args(); main(a.limit,a.force)
