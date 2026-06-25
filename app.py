"""Flask web app for the LinkedIn content pipeline."""
import os
import re
import datetime
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from flask import Flask, request, jsonify, Response
from openai import OpenAI

BASE_DIR = Path(__file__).parent
app = Flask(__name__)

MODEL  = "gpt-4o"

def _openai_key() -> str:
    if key := os.environ.get("OPENAI_API_KEY", ""):
        return key
    # file drop via file-browser
    data_dir = os.environ.get("OPENHOST_APP_DATA_DIR", "")
    if data_dir:
        p = Path(data_dir) / "openai_key.txt"
        if p.exists():
            return p.read_text().strip()
    # pull from secrets app via OpenHost zone domain
    zone  = os.environ.get("OPENHOST_ZONE_DOMAIN", "")
    token = os.environ.get("OPENHOST_APP_TOKEN", "")
    if zone and token:
        try:
            req = urllib.request.Request(
                f"https://secrets.{zone}/api/export",
                headers={"Authorization": f"Bearer {token}"},
            )
            with urllib.request.urlopen(req, timeout=5) as r:
                for line in r.read().decode().splitlines():
                    if line.startswith("export OPENAI_API_KEY="):
                        return line.split("=", 1)[1].strip().strip('"\'')
        except Exception:
            pass
    return ""


def _client():
    return OpenAI(api_key=_openai_key() or None)

EVOLVED_PROMPT = Path("evolved_prompt.txt")
FALLBACK_PROMPT = (
    "You are writing a LinkedIn post in the voice of Kruthik Hulisandra. "
    "Open with a macro historical or economic force. Zoom into something personal. "
    "Ask a rhetorical question. End punchy. Max 200 words. No hashtags. No emojis."
)
_data_dir = os.environ.get("OPENHOST_APP_DATA_DIR")
POSTS_DIR = Path(_data_dir) / "posts" if _data_dir else Path("posts")


def load_system_prompt():
    if EVOLVED_PROMPT.exists():
        return EVOLVED_PROMPT.read_text(encoding="utf-8").strip()
    return FALLBACK_PROMPT


def fetch_pubmed(url):
    match = re.search(r"/(\d{6,9})/?", url)
    if not match:
        raise ValueError(f"Could not extract PMID from: {url}")
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
        "pmid": pmid, "title": title, "abstract": abstract,
        "first_author": first_author,
        "year": root.findtext(".//PubDate/Year") or "",
        "url": url,
    }


def _clean_truncate(text, limit=1100):
    CTA = "Come test this with us"
    if CTA in text:
        cta_idx  = text.rfind(CTA)
        cta_end  = text.find("\n", cta_idx)
        cta_line = text[cta_idx : cta_end if cta_end > -1 else len(text)].strip()
        body     = text[:cta_idx].strip()
        budget   = limit - len(cta_line) - 2
        if len(body) > budget:
            chunk = body[:budget]
            for p in ("?", "!", "."):
                idx = chunk.rfind(p)
                if idx > budget * 0.5:
                    body = chunk[:idx+1].strip()
                    break
        return body + "\n\n" + cta_line
    if len(text) <= limit:
        return text
    chunk = text[:limit]
    for p in ("?", "!", "."):
        idx = chunk.rfind(p)
        if idx > limit * 0.5:
            return chunk[:idx+1].strip()
    return chunk.strip()


def generate_post(system_prompt, instruction):
    resp = _client().chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": instruction},
        ],
        temperature=0.85,
        max_tokens=600,
    )
    return _clean_truncate(resp.choices[0].message.content.strip())


@app.route("/")
def index():
    html = (BASE_DIR / "search.html").read_text(encoding="utf-8")
    return Response(html, mimetype="text/html")


@app.route("/generate", methods=["POST"])
def generate():
    url = request.json.get("url", "").strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        paper = fetch_pubmed(url)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    system_prompt = load_system_prompt()
    context = (
        f"Paper: {paper['title']}\n"
        f"Authors: {paper['first_author']} et al. ({paper['year']})\n"
        f"Abstract: {paper['abstract']}"
    )

    monday = generate_post(system_prompt,
        f"{context}\n\nMONDAY POST — open with the macro force that makes this research matter "
        "right now, then zoom into a specific experiment or observation Kruthik made at his "
        "gathering. End punchy. 200 words max.")

    wednesday = generate_post(system_prompt,
        f"{context}\n\nWEDNESDAY POST — personal story from the gathering: a reaction, a "
        "surprise, a conversation. Open macro, zoom personal, ask a bold rhetorical question. "
        "End punchy. 200 words max.")

    friday = generate_post(system_prompt,
        f"{context}\n\nFRIDAY POST — what was learned, one thing the research did not predict, "
        "a challenge to the reader. End with exactly: "
        "'Come test this with us — next gathering: [DATE PLACEHOLDER]' — 200 words max.")

    today   = datetime.date.today().isoformat()
    out_dir = POSTS_DIR / today
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "monday.txt").write_text(monday,    encoding="utf-8")
    (out_dir / "wednesday.txt").write_text(wednesday, encoding="utf-8")
    (out_dir / "friday.txt").write_text(friday,    encoding="utf-8")

    return jsonify({
        "paper": {"title": paper["title"], "pmid": paper["pmid"], "year": paper["year"]},
        "posts": {"monday": monday, "wednesday": wednesday, "friday": friday},
        "saved_to": str(out_dir),
    })


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=8080, debug=debug)
