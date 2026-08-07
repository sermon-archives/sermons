#!/usr/bin/env python3
"""Rate-limited metadata collector. yt-dlp first; RSS is a polite fallback."""
from __future__ import annotations
import argparse, json, re, sqlite3, subprocess, sys, time, tempfile, os
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

CHANNEL_ID = "UCxTu88in5i5NsZzX-w-z0qQ"
CHANNEL_URL = f"https://www.youtube.com/channel/{CHANNEL_ID}/videos"
NS = {"yt": "http://www.youtube.com/xml/schemas/2015", "media": "http://search.yahoo.com/mrss/"}

def is_sermon_video(title: str, description: str = "") -> tuple[bool, str]:
    """Conservative, explainable classifier; human review remains authoritative."""
    text = f"{title} {description}".lower()
    excluded = ("shorts", "announcement", "weekly update", "worship", "music", "podcast", "q&a", "q & a", "test stream")
    if any(x in text for x in excluded): return False, "excluded non-sermon keyword"
    scripture = re.compile(r"\b(?:[1-3]\s*)?[a-z]{2,15}\s+\d{1,3}(?::\d{1,3}(?:[-–]\d{1,3})?)?\b", re.I)
    positive = ("sermon", "preaching", "pastor", "church", "bible", "christ", "jesus", "lord", "gospel", "word of god", "series")
    if scripture.search(text): return True, "Scripture reference detected"
    # Sentence-like devotional clips are often Shorts rather than full sermons.
    core_title=title.strip()
    if core_title.endswith((".", "!", "?")) and (len(core_title.split()) > 12 or not any(x in text for x in ("sermon", "preaching", "pastor", "church", "bible", "gospel", "series"))):
        return False, "sentence-like clip; likely short/devotional"
    if any(x in text for x in positive): return True, "sermon-like title/description"
    return False, "no sermon signal; review manually"


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values(): yield from _walk(child)
    elif isinstance(value, list):
        for child in value: yield from _walk(child)

def ytdlp_dump(limit: int) -> list[dict]:
    """Parse YouTube lockup continuation dumps when yt-dlp's tab parser lags."""
    with tempfile.TemporaryDirectory(prefix="sermon-ytpages-") as td:
        cmd=[sys.executable,"-m","yt_dlp","--skip-download","--write-pages","--playlist-end",str(limit),"--sleep-requests","2","--sleep-interval","3","--max-sleep-interval","8","--paths",td,CHANNEL_URL]
        subprocess.run(cmd,text=True,capture_output=True,timeout=300)
        found={}
        for path in Path(td).glob("*.dump"):
            try: payload=json.loads(path.read_text(errors="ignore"))
            except Exception: continue
            for item in _walk(payload):
                lv=item.get("lockupViewModel",{}) if isinstance(item,dict) else {}
                if lv.get("contentType")!="LOCKUP_CONTENT_TYPE_VIDEO": continue
                vid=lv.get("contentId"); meta=lv.get("metadata",{}).get("lockupMetadataViewModel",{})
                title=(meta.get("title",{}).get("content") or "Untitled").strip()
                if vid: found[vid]=title
        out=[]
        for vid,title in found.items():
            ok,reason=is_sermon_video(title)
            out.append(dict(id=vid,title=title,published_at="",url=f"https://www.youtube.com/watch?v={vid}",description="",is_sermon=int(ok),classification_reason=reason))
        return out[:limit]

def rss(limit: int) -> list[dict]:
    req = Request(f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}", headers={"User-Agent":"sermon-archive/1.0"})
    with urlopen(req, timeout=30) as response: root = ET.fromstring(response.read())
    out=[]
    for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
        vid=entry.findtext("yt:videoId", namespaces=NS) or ""
        title=entry.findtext("{http://www.w3.org/2005/Atom}title") or "Untitled"
        published=entry.findtext("{http://www.w3.org/2005/Atom}published") or ""
        media=entry.find("media:group",NS)
        desc=media.findtext("media:description",default="",namespaces=NS) if media is not None else ""
        ok,reason=is_sermon_video(title,desc)
        out.append(dict(id=vid,title=title,published_at=published,url=f"https://www.youtube.com/watch?v={vid}",description=desc,is_sermon=int(ok),classification_reason=reason))
    return out[:limit]

def ytdlp(limit: int) -> list[dict]:
    cmd=[sys.executable,"-m","yt_dlp","--flat-playlist","--playlist-end",str(limit),"--dump-single-json","--no-warnings","--sleep-requests","2","--sleep-interval","3","--max-sleep-interval","8","--extractor-retries","2",CHANNEL_URL]
    p=subprocess.run(cmd,text=True,capture_output=True,timeout=240)
    if p.returncode != 0: raise RuntimeError(p.stderr[-500:])
    obj=json.loads(p.stdout); out=[]
    for e in obj.get("entries") or []:
        if not e or not e.get("id"): continue
        title=e.get("title") or "Untitled"; desc=e.get("description") or ""
        ok,reason=is_sermon_video(title,desc)
        out.append(dict(id=e["id"],title=title,published_at=e.get("upload_date") or "",url=f"https://www.youtube.com/watch?v={e['id']}",description=desc,is_sermon=int(ok),classification_reason=reason))
    return out

def store(rows):
    path=Path("data/sermons.sqlite3"); path.parent.mkdir(exist_ok=True)
    db=sqlite3.connect(path); db.row_factory=sqlite3.Row; db.executescript(Path("db/schema.sql").read_text())
    seed_path=Path("data/sermons.json")
    seed_rows=json.loads(seed_path.read_text()) if seed_path.exists() else []
    for r in seed_rows + rows:
        db.execute("""INSERT INTO sermons(id,title,published_at,url,description,is_sermon,classification_reason,updated_at)
        VALUES(?,?,?,?,?,?,?,CURRENT_TIMESTAMP) ON CONFLICT(id) DO UPDATE SET title=excluded.title,published_at=excluded.published_at,url=excluded.url,description=excluded.description,is_sermon=excluded.is_sermon,classification_reason=excluded.classification_reason,updated_at=CURRENT_TIMESTAMP""",
        (r['id'],r['title'],r.get('published_at',''),r['url'],r.get('description',''),r['is_sermon'],r['classification_reason']))
    db.commit();
    # portable export consumed by static build and easy to upload to Turso
    rows2=[dict(x) for x in db.execute("SELECT * FROM sermons WHERE is_sermon=1 ORDER BY published_at DESC LIMIT 20").fetchall()]
    Path("data/sermons.json").write_text(json.dumps(rows2,indent=2,ensure_ascii=False))
    db.close(); print(f"Stored {len(rows)} candidates; {len(rows2)} sermon records")

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--limit',type=int,default=20); args=ap.parse_args()
    try:
        records=ytdlp(args.limit)
        if not records: raise RuntimeError("yt-dlp returned no entries (likely YouTube lockup/consent response)")
    except Exception as exc:
        print(f"yt-dlp channel listing unavailable ({exc}); trying yt-dlp page dumps",file=sys.stderr)
        try:
            records=ytdlp_dump(args.limit)
            if not records: raise RuntimeError("no lockups found")
        except Exception as dump_exc:
            print(f"page dump unavailable ({dump_exc}); using RSS fallback",file=sys.stderr); records=rss(args.limit)
    store(records)
    if os.getenv("TURSO_DATABASE_URL") and os.getenv("TURSO_AUTH_TOKEN"):
        subprocess.run([sys.executable, "scripts/turso_sync.py"], check=True)
