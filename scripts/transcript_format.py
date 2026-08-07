"""Sentence-aware paragraph formatting for Whisper transcripts."""
from __future__ import annotations
import re
_SENTENCE_END = re.compile(r"(?<=[.!?])(?:[\"'”’)]*)\s+")
_FIRST_ALPHA = re.compile(r"([A-Za-z])")
_PUNCT_PIPE = None

def _capitalize_start(sentence: str) -> str:
    m=_FIRST_ALPHA.search(sentence)
    if m and m.group(1).islower(): sentence=sentence[:m.start(1)]+m.group(1).upper()+sentence[m.end(1):]
    return re.sub(r"\bi\b", "I", sentence)

def restore_missing_punctuation(text: str) -> str:
    """Restore punctuation with a punctuation model when Whisper omitted it."""
    global _PUNCT_PIPE
    try:
        from transformers import pipeline
        if _PUNCT_PIPE is None:
            _PUNCT_PIPE=pipeline('ner','oliverguhr/fullstop-punctuation-multilang-large',aggregation_strategy='none')
    except Exception:
        return text
    words=text.split(); output=[]; chunk_size=220
    for start in range(0,len(words),chunk_size):
        chunk=words[start:start+chunk_size]; chunk_text=' '.join(chunk)
        try: tags=_PUNCT_PIPE(chunk_text)
        except Exception: return text
        cursor=0; tag_i=0
        for word in chunk:
            begin=cursor; end=cursor+len(word); cursor=end+1; label='0'
            while tag_i<len(tags) and tags[tag_i].get('end',0)<=end:
                label=tags[tag_i].get('entity','0'); tag_i+=1
            # punctuation labels are emitted on the final sub-token of a word
            output.append(word + (label if label in '.,?!-:' else ''))
    return ' '.join(output)

def reflow_transcript(text: str, max_chars: int = 900, target_sentences: int = 5, punctuate: bool = False) -> str:
    """Group complete sentences into paragraphs; never cut at a character limit."""
    blocks=[re.sub(r"\s+", " ", b).strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    if not blocks: return ""
    if punctuate:
        fixed=[]
        for block in blocks:
            punctuation=sum(block.count(x) for x in '.!?')
            if punctuation < max(1, len(block.split())//120): block=restore_missing_punctuation(block)
            fixed.append(block)
        normalized=' '.join(fixed)
    else:
        normalized=' '.join(blocks)
    sentences=[_capitalize_start(x.strip()) for x in _SENTENCE_END.split(normalized) if x.strip()]
    paragraphs=[]; current=[]; chars=0
    for sentence in sentences:
        proposed=chars+len(sentence)+(1 if current else 0)
        if current and (len(current)>=target_sentences or proposed>max_chars):
            paragraphs.append(" ".join(current)); current=[]; chars=0
        current.append(sentence); chars += len(sentence)+(1 if len(current)>1 else 0)
    if current: paragraphs.append(" ".join(current))
    return "\n\n".join(paragraphs)
