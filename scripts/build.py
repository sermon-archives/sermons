#!/usr/bin/env python3
"""Build a dependency-free static site from data/sermons.json."""
from __future__ import annotations
import html, json, re
from pathlib import Path
from datetime import datetime
import markdown as mdlib
ROOT=Path(__file__).parents[1]; DIST=ROOT/'dist'; CONTENT=ROOT/'content'/'sermons'
CSS="""*{box-sizing:border-box}body{margin:0;background:#f6f3ed;color:#20252b;font:16px/1.55 system-ui,-apple-system,sans-serif;transition:background .2s,color .2s}a{color:#145c63}.site-header{background:#173b42;color:#fff;padding:2rem max(1rem,calc((100% - 1100px)/2)) 1.5rem}.site-header h1{margin:.35rem 0;font-size:clamp(2rem,5vw,3rem)}.site-header p{margin:.35rem 0}.site-header a{color:#bde7de;text-decoration:none}.theme-toggle{float:right;border:1px solid #bde7de;background:transparent;color:#bde7de;border-radius:999px;padding:.35rem .7rem;cursor:pointer}.theme-toggle:hover{background:#ffffff1a}.wrap{max-width:1100px;margin:auto;padding:1.35rem 1rem}.eyebrow{text-transform:uppercase;letter-spacing:.12em;font-size:.78rem;color:#bde7de}.brand-divider{opacity:.55;margin:0 .4rem}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:1rem}.list-heading{margin:.6rem 0}.list-intro{margin:.25rem 0 .8rem;color:#687078}.sermon-list{display:flex;flex-direction:column;gap:0;border-top:1px solid #d9d2c8}.sermon-row{display:grid;grid-template-columns:128px minmax(0,1fr);gap:1rem;align-items:center;background:transparent;border:0;border-bottom:1px solid transparent;border-image:linear-gradient(90deg,#d9d2c8,#9dbeb5 45%,#d9d2c8) 1;padding:1rem 0}.sermon-row:last-child{border-bottom:0}.sermon-row:hover{background:linear-gradient(90deg,#ffffff00,#e4f3ef55,#ffffff00)}.sermon-thumb{width:128px;height:72px;object-fit:cover;border-radius:7px;background:#dfe8e4}.sermon-row h2{margin:.2rem 0;font-size:1.1rem}.sermon-meta{margin:.15rem 0;color:#53636a;font-size:.9rem}.sermon-summary{margin:.35rem 0 0;color:#4d565b;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}.card{background:#fff;border:1px solid #e0dbd2;border-radius:12px;padding:1.25rem;box-shadow:0 2px 8px #233b4210}.tag{display:inline-block;border-radius:99px;background:#e4f3ef;color:#145c63;padding:.15rem .6rem;font-size:.78rem}.muted{color:#687078}.prose{max-width:760px}.prose p{margin:.85rem 0;white-space:normal}.sermon-header{background:transparent;color:#20252b;padding:0;margin-bottom:1rem}.sermon-header a{color:#145c63}.breadcrumb{display:flex;align-items:center;gap:.55rem;flex-wrap:wrap;margin:.1rem 0 .8rem}.breadcrumb a{color:#145c63;text-decoration:none}.breadcrumb .muted{margin:0}.sermon-meta-line{display:flex;align-items:center;gap:.55rem;margin:.2rem 0}.sermon-meta-line .muted{margin:0}.sermon-layout{display:grid;grid-template-columns:minmax(0,1fr) 400px;gap:1.5rem;align-items:start}.review-column{position:sticky;top:1rem;align-self:start;max-height:calc(100vh - 2rem);overflow-y:auto;padding-right:.35rem}.video{aspect-ratio:16/9;margin:1rem 0}.video iframe{width:100%;height:100%;border:0;border-radius:10px}.summary-box{background:transparent;border-top:1px solid #c9d7d2;border-bottom:1px solid #c9d7d2;padding:.75rem 0;margin:1rem 0}.summary-box[open]{padding-bottom:.85rem}.summary-box summary{cursor:pointer;font-weight:650;color:#145c63}.summary-box p{margin:.55rem 0 0}.outline p{margin:.35rem 0}.review-section h2{margin-top:1rem}.review-section:first-child h2{margin-top:0}.review{border-left:4px solid #d6a441;background:#fffaf0;padding:.7rem 1rem;margin:1rem 0}.strength{border-color:#388e69;background:#f0faf4}.outline h1{font-size:1.15rem;margin:.35rem 0}.outline h2{font-size:1.05rem;margin:.4rem 0}.outline h3{font-size:1rem;margin:.4rem 0}.outline ol,.outline ul{margin:.35rem 0;padding-left:1.25rem}.outline li{margin:.25rem 0}.outline li p{margin:.2rem 0}.outline hr{border:none;border-top:1px solid var(--line,#d9d2c8);margin:.6rem 0}.outline{font-size:.95rem;line-height:1.5;padding-left:.1rem}.weakness{border-color:#b47a35;background:#fff8ed}.notice{background:#fff;border:1px solid #ded7cb;border-radius:10px;padding:.7rem .85rem;margin:.7rem 0}footer{border-top:1px solid #ddd5ca;margin-top:3rem;padding:2rem 1rem;color:#687078}h1{font-size:clamp(2rem,5vw,3.5rem);line-height:1.1}h2{line-height:1.2}body[data-theme="dark"]{background:#151b1d;color:#e8eeeb}body[data-theme="dark"] a{color:#8ed1c2}body[data-theme="dark"] .site-header{background:#0c292e}body[data-theme="dark"] .site-header a,body[data-theme="dark"] .theme-toggle{color:#bde7de}body[data-theme="dark"] .sermon-row{border-image:linear-gradient(90deg,#344447,#5c938b 45%,#344447) 1}body[data-theme="dark"] .sermon-row:hover{background:linear-gradient(90deg,#ffffff00,#23433f55,#ffffff00)}body[data-theme="dark"] .muted,body[data-theme="dark"] .sermon-meta,body[data-theme="dark"] .sermon-summary,body[data-theme="dark"] .list-intro{color:#aebbb7}body[data-theme="dark"] .sermon-header{color:#e8eeeb}body[data-theme="dark"] .summary-box{border-color:#47706b}body[data-theme="dark"] .summary-box summary{color:#8ed1c2}body[data-theme="dark"] .notice,body[data-theme="dark"] .review,body[data-theme="dark"] .card{background:#202a2d;border-color:#39484b}body[data-theme="dark"] .strength{background:#19342d}body[data-theme="dark"] .weakness{background:#352b1e}body[data-theme="dark"] footer{border-color:#39484b}@media(max-width:760px){.sermon-row{grid-template-columns:96px minmax(0,1fr);gap:.7rem}.sermon-thumb{width:96px;height:54px}.sermon-row h2{font-size:1rem}.sermon-layout{display:flex;flex-direction:column}.review-column{order:-1;position:static;width:100%;max-height:none;overflow:visible;padding-right:0}.outline-section{order:1}.devotional-section{order:2}}"""
def display_title(title):
    # Preserve YouTube wording while replacing noisy pipe separators.
    title = re.sub(r'\s*\|\s*', ' — ', title)
    title = re.sub(r'\s+', ' ', title).strip(' -—')
    return title

BOOKS = r"(?:1|2|3)?\s*(?:Samuel|Kings|Chronicles|Corinthians|Thessalonians|Timothy|Peter|John|Genesis|Exodus|Leviticus|Numbers|Deuteronomy|Joshua|Judges|Ruth|Ezra|Nehemiah|Esther|Job|Psalms?|Proverbs|Ecclesiastes|Song of Solomon|Isaiah|Jeremiah|Lamentations|Ezekiel|Daniel|Hosea|Joel|Amos|Obadiah|Jonah|Micah|Nahum|Habakkuk|Zephaniah|Haggai|Zechariah|Malachi|Matthew|Mark|Luke|Acts|Romans|Galatians|Ephesians|Philippians|Colossians|Titus|Philemon|Hebrews|James|Jude|Revelation)"
def sermon_reference(r):
    text=f"{r.get('title','')} {r.get('transcript','')}"
    m=re.search(rf"\b({BOOKS})\s+\d{{1,3}}(?::\d{{1,3}}(?:[-–]\d{{1,3}})?)?", text, re.I)
    return re.sub(r"\s+", " ", m.group(0)).strip() if m else "Scripture reference pending"
def pastor_name(r):
    title=r.get('title','')
    m=re.search(r"\bPastor\s+([^|—]+)", title, re.I)
    if m: return m.group(1).strip(' -')
    parts=re.split(r"\s*\|\s*|\s+—\s+", title)
    tail=parts[-1].strip() if parts else ''
    if re.fullmatch(r"[A-Z][A-Za-z.'-]+(?:\s+[A-Z][A-Za-z.'-]+){1,3}", tail): return tail
    return "Pastor not listed"
def summary(r):
    if r.get('summary'): return r['summary']
    text=re.sub(r"\s+", " ", r.get('transcript','') or r.get('description','')).strip()
    if not text: return "Transcript pending."
    # Skip greetings and fellowship remarks when no LLM summary has been generated.
    chunks=re.split(r"(?<=[.!?])\s+", text)
    ref=sermon_reference(r)
    ref_words=ref.replace('Scripture reference pending','').strip()
    start=next((i for i,x in enumerate(chunks) if ref_words and ref_words.lower() in x.lower()), None)
    if start is None:
        start=next((i for i,x in enumerate(chunks) if len(x)>80 and re.search(r"\b(?:Romans|Matthew|Mark|Luke|John|Peter|Scripture|Bible|gospel)\b",x,re.I)),0)
    return " ".join(chunks[start:start+2])[:360]
def sermon_title(r):
    """YouTube title with the separately displayed reference/speaker removed."""
    raw=r.get('title','')
    parts=[x.strip() for x in re.split(r"\s*\|\s*|\s+—\s+", raw) if x.strip()]
    kept=[]
    for part in parts:
        if re.search(r"\bPastor\b", part, re.I): continue
        if re.search(rf"\b{BOOKS}\s+\d{{1,3}}(?::\d{{1,3}}(?:[-–]\d{{1,3}})?)?", part, re.I):
            part=re.sub(rf"\s*[-–—:]?\s*{BOOKS}\s+\d{{1,3}}(?::\d{{1,3}}(?:[-–]\d{{1,3}})?)?.*$", "", part, flags=re.I).strip(' -–—:')
            if not part: continue
        kept.append(part)
    # A final capitalized name (e.g. “Greg DeWeese”) is the speaker label.
    if len(kept)>1 and re.fullmatch(r"[A-Z][A-Za-z.'-]+(?:\s+[A-Z][A-Za-z.'-]+){1,3}", kept[-1]): kept.pop()
    return display_title(' — '.join(kept or parts or [raw]))
def slug(s): return re.sub(r'[^a-z0-9]+','-',s.lower()).strip('-')[:70]
def date(v):
    try:return datetime.fromisoformat(v.replace('Z','+00:00')).strftime('%b %-d, %Y')
    except:return v or 'Date unavailable'
def page(title,body,home="index.html",detail=False):
    headline=title if detail else "Sermon Archive"
    subtitle="Transcript, summary, and biblical review." if detail else "Each row includes the pastor, detected Scripture reference, and a short summary."
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)} · GraceLife sermon archive</title><style>{CSS}</style></head><body><header class="site-header"><button class="theme-toggle" id="theme-toggle" type="button" aria-label="Toggle dark mode">☾ Dark</button><a href="{home}"><span class="eyebrow">Unofficial GraceLife London <span class="brand-divider">|</span> Sermon Archive</span><h1>{html.escape(headline)}</h1></a><p>{subtitle}</p></header><main class="wrap">{body}</main><footer class="wrap">Automated transcript and review. Compare quotations with Scripture and the original video.</footer><script>(function(){{const b=document.body,k="sermon-theme",saved=localStorage.getItem(k),dark=saved? saved==="dark":matchMedia("(prefers-color-scheme: dark)").matches;if(dark)b.dataset.theme="dark";const t=document.getElementById("theme-toggle");function set(d){{b.dataset.theme=d?"dark":"light";localStorage.setItem(k,d?"dark":"light");t.textContent=d?"☀ Light":"☾ Dark"}}set(dark);t.addEventListener("click",()=>set(b.dataset.theme!=="dark"));}})();</script></body></html>"""
def listish_html(text):
    if not text: return '<p class="muted">Devotional questions pending.</p>'
    lines=[]
    for line in text.splitlines():
        line=line.strip()
        if not line: continue
        m=re.match(r"^\d+[.)]\s+",line)
        if m: lines.append(f"<p><strong>{html.escape(line)}</strong></p>")
        elif line.startswith(('-', '*')): lines.append(f"<p>· {html.escape(line[1:].strip())}</p>")
        else: lines.append(f"<p>{html.escape(line)}</p>")
    return ''.join(lines)
def outline_html(text):
    if not text: return '<p class="muted">Outline pending.</p>'
    try:
        body=mdlib.markdown(text, extensions=['extra'])
    except Exception:
        return '<p>' + html.escape(text) + '</p>'
    return body
def transcript_html(text):
    if not text:return '<p class="muted">This sermon is catalogued but not transcribed yet.</p>'
    return ''.join(f'<p>{html.escape(p.strip())}</p>' for p in re.split(r'\n\s*\n',text) if p.strip())
def markdown(r):
    title=sermon_title(r).replace('"', "'")
    return f"""---
title: "{title}"
youtube: {r['url']}
published: {r.get('published_at','')}
transcript_status: {r.get('transcript_status','pending')}
review_status: {r.get('review_status','pending')}
---

# {title}

[Watch the original sermon]({r['url']}) · **Published:** {date(r.get('published_at',''))}

## Transcript

{r.get('transcript') or '_Not transcribed yet._'}

## Strengths (biblical review)

{r.get('strengths') or '_Pending review by a biblically orthodox Christian reviewer._'}

## Weaknesses / biblical cautions

{r.get('weaknesses') or '_Pending review; no theological conclusions should be inferred from this automated catalog._'}
"""
def main():
    records=json.loads((ROOT/'data'/'sermons.json').read_text()) if (ROOT/'data'/'sermons.json').exists() else []
    if DIST.exists():
        import shutil; shutil.rmtree(DIST)
    DIST.mkdir(exist_ok=True); CONTENT.mkdir(parents=True,exist_ok=True); cards=[]
    for r in records:
        title=sermon_title(r)
        ident=slug(r['id']+'-'+title); (CONTENT/f'{ident}.md').write_text(markdown(r))
        status='Transcribed' if r.get('transcript_status')=='complete' else 'Queued'
        note='' if status=='Transcribed' else 'Queued for transcription.'
        cards.append(f'<article class="sermon-row"><a href="sermons/{ident}.html"><img class="sermon-thumb" src="https://i.ytimg.com/vi/{html.escape(r["id"])}/mqdefault.jpg" alt="" loading="lazy"></a><div><span class="tag">{status}</span><h2><a href="sermons/{ident}.html">{html.escape(title)}</a></h2><p class="sermon-meta"><strong>{html.escape(pastor_name(r))}</strong> · {html.escape(sermon_reference(r))} · {date(r.get("published_at",""))}</p><p class="sermon-summary">{html.escape(summary(r))}</p></div></article>')
        detail_note='Transcript available.' if status=='Transcribed' else 'Queued for transcription.'
        body=f'''<p class="breadcrumb"><a href="../index.html">← All sermons</a><span class="brand-divider">|</span><span class="tag">{status}</span><span class="muted">{date(r.get("published_at",""))} · {html.escape(pastor_name(r))} · <a href="{html.escape(r["url"])}">Open on YouTube</a></span></p><div class="sermon-layout"><article class="prose transcript-column"><div class="video"><iframe src="https://www.youtube-nocookie.com/embed/{html.escape(r["id"])}?rel=0" title="Watch {html.escape(title)}" loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe></div><details class="summary-box"><summary>Summary</summary><p>{html.escape(summary(r))}</p></details><h2>Transcript</h2>{transcript_html(r.get("transcript", ""))}</article><aside class="review-column"><div class="review-section outline-section"><h2>Sermon outline</h2><div class="review outline">{outline_html(r.get("outline", ""))}</div></div><div class="review-section devotional-section"><h2>Devotional questions</h2><div class="review devotional">{listish_html(r.get("devotional_questions", ""))}</div></div></aside></div>'''
        (DIST/'sermons').mkdir(exist_ok=True); (DIST/'sermons'/f'{ident}.html').write_text(page(title,body,'../index.html',True))
    body='<section class="sermon-list">'+''.join(cards)+'</section>'
    (DIST/'index.html').write_text(page('Sermon archive',body)); (DIST/'robots.txt').write_text('User-agent: *\nAllow: /\n'); print(f'Built {len(records)} sermon pages in {DIST}')
if __name__=='__main__': main()
