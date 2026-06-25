"""
Generate Mon/Wed/Fri LinkedIn posts from a PubMed paper URL.

Usage: python generate_posts.py <pubmed-url>

All generation via gpt-4o. System prompt: evolved_prompt.txt (from voice_problem.py).
"""
import re
import sys
import json
import datetime
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from openai import OpenAI

CLIENT = OpenAI()
MODEL  = "gpt-4o"

POSTS_DIR      = Path("posts")
EVOLVED_PROMPT = Path("evolved_prompt.txt")

FALLBACK_PROMPT = """\
You are writing a LinkedIn post in the voice of Kruthik Hulisandra.
Open with a macro historical or economic force. Zoom into something personal and specific.
Think out loud — not tips. Ask a rhetorical question. End with one punchy sentence.
Max 200 words. No hashtags. No emojis."""


def load_system_prompt() -> str:
    if EVOLVED_PROMPT.exists():
        prompt = EVOLVED_PROMPT.read_text(encoding="utf-8").strip()
        print(f"System prompt: evolved_prompt.txt ({len(prompt)} chars)")
        return prompt
    print("System prompt: fallback (run voice_problem.py to evolve a better one)")
    return FALLBACK_PROMPT


def fetch_pubmed(url: str) -> dict:
    match = re.search(r"/(\d{6,9})/?", url)
    if not match:
        sys.exit(f"Could not extract PMID from: {url}")
    pmid = match.group(1)

    api = (
        f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        f"?db=pubmed&id={pmid}&rettype=xml&retmode=xml"
    )
    with urllib.request.urlopen(api, timeout=15) as r:
        root = ET.fromstring(r.read())

    title    = root.findtext(".//ArticleTitle") or "Unknown title"
    abstract = " ".join(
        (p.text or "").strip() for p in root.findall(".//AbstractText") if p.text
    ) or "No abstract available."

    authors = root.findall(".//Author")
    first_author = (
        f"{authors[0].findtext('ForeName') or ''} {authors[0].findtext('LastName') or ''}".strip()
        if authors else ""
    )

    return {
        "pmid":         pmid,
        "title":        title,
        "abstract":     abstract,
        "first_author": first_author,
        "year":         root.findtext(".//PubDate/Year") or "",
        "url":          url,
    }


def _clean_truncate(text: str, limit: int = 1100) -> str:
    CTA = "Come test this with us"
    if CTA in text:
        cta_idx  = text.rfind(CTA)
        cta_end  = text.find("\n", cta_idx)
        cta_line = text[cta_idx : cta_end if cta_end > -1 else len(text)].strip()
        body     = text[:cta_idx].strip()
        budget   = limit - len(cta_line) - 2
        if len(body) > budget:
            chunk = body[:budget]
            for punct in ("?", "!", "."):
                idx = chunk.rfind(punct)
                if idx > budget * 0.5:
                    body = chunk[:idx + 1].strip()
                    break
        return body + "\n\n" + cta_line

    if len(text) <= limit:
        return text
    chunk = text[:limit]
    for punct in ("?", "!", "."):
        idx = chunk.rfind(punct)
        if idx > limit * 0.5:
            return chunk[:idx + 1].strip()
    return chunk.strip()


def generate(system_prompt: str, instruction: str, label: str) -> str:
    resp = CLIENT.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": instruction},
        ],
        temperature=0.85,
        max_tokens=600,
    )
    text   = resp.choices[0].message.content.strip()
    result = _clean_truncate(text)
    print(f"  {label}: {len(result)} chars ({len(result.split())} words)")
    return result


def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: python generate_posts.py <pubmed-url>")

    print("Fetching paper...")
    paper = fetch_pubmed(sys.argv[1])
    print(f"  {paper['title'][:80]}...")
    print()

    system_prompt = load_system_prompt()
    print()

    context = (
        f"Paper: {paper['title']}\n"
        f"Authors: {paper['first_author']} et al. ({paper['year']})\n"
        f"Abstract: {paper['abstract']}"
    )

    print("Generating posts...")
    monday = generate(system_prompt, (
        f"{context}\n\n"
        "MONDAY POST — open with the macro force that makes this research matter right now, "
        "then zoom into the specific experiment Kruthik ran at his gathering. End punchy. 200 words max."
    ), "monday")

    wednesday = generate(system_prompt, (
        f"{context}\n\n"
        "WEDNESDAY POST — personal story from the gathering: a reaction, a surprise, "
        "a conversation. Open macro, zoom personal, ask a bold rhetorical question. End punchy. 200 words max."
    ), "wednesday")

    friday = generate(system_prompt, (
        f"{context}\n\n"
        "FRIDAY POST — what was learned, one thing the research did not predict, "
        "a challenge to the reader. End with exactly: "
        "'Come test this with us — next gathering: [DATE PLACEHOLDER]' — 200 words max."
    ), "friday")

    print()
    today   = datetime.date.today().isoformat()
    out_dir = POSTS_DIR / today
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "monday.txt").write_text(monday,    encoding="utf-8")
    (out_dir / "wednesday.txt").write_text(wednesday, encoding="utf-8")
    (out_dir / "friday.txt").write_text(friday,    encoding="utf-8")
    (out_dir / "source.json").write_text(json.dumps(paper, indent=2), encoding="utf-8")

    print(f"Saved to {out_dir}/")


if __name__ == "__main__":
    main()
