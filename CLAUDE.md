# LinkedIn Content Pipeline

Voice-matched LinkedIn content engine for Kruthik Hulisandra. Pulls peer-reviewed research from PubMed, generates Mon/Wed/Fri posts in Kruthik's voice, stores drafts in Notion for human approval before anything goes out.

---

## Session Log

### 2026-06-24 — Initial build

**Voice extraction**
- Read full Edison paper PDF (`WithPageNumbersEdisonRemidial-KruthikHulisandra.pdf`)
- Extracted voice patterns manually before writing any code:
  - Opens with macro historical/economic force (not background — the argument)
  - Zooms into personal specifics: named people, real experiments, admitted mistakes
  - Uses frameworks conversationally — thinking out loud, not listicle
  - Rhetorical question mid-piece; single punchy closer
  - Signature move: "So why can't it be me?"
- Seeded `voice_profile.json` directly from this analysis

**Files created**
- `writing_sample.txt` — key narrative sections from Edison paper for Gemma extraction
- `voice_profile.json` — voice analysis seeded from session reading (skip `extract_voice.py` if satisfied with this)
- `extract_voice.py` — re-extracts voice via Gemma if writing sample changes
- `voice_problem.py` — Darwinian Evolver: 20 iterations, Gemma generates, gpt-4o evaluates and mutates, saves winner to `evolved_prompt.txt`
- `generate_posts.py` — PubMed URL → NCBI API fetch → Mon/Wed/Fri posts via Gemma → `posts/YYYY-MM-DD/`
- `linkedin_pipeline.yaml` — Omnigent config: Monday 9am PT, 4 agents, $5 cost cap, human approval gate
- `setup.sh` — preflight checks + `uv` dependency install

**Plugin status**
- `ponytail` installed during session (`/plugin marketplace add DietrichGebert/ponytail` → `/plugin install ponytail@ponytail`)
- Code was written before ponytail was active — not yet audited with `/ponytail-audit`

---

## Stack

| Component | Role |
|---|---|
| gpt-4o / gpt-4o-mini via OpenAI API | All content generation + evolver eval/mutation |
| Darwinian Evolver (`imbue-ai/darwinian_evolver`) | Prompt evolution (manual loop fallback) |
| Flask (`app.py`) | Web UI server on port 8080 |
| NCBI E-utilities API | PubMed paper fetching |
| Omnigent | Weekly pipeline orchestration |
| Notion MCP | Output storage |

> Gemma 4 E4B / LM Studio removed 2026-06-25. All generation now via OpenAI API.

---

## Hard constraints (do not change)

- Posts never mention AI was involved
- Human approval required before anything is posted externally
- Max 200 words per post
- No em dashes, no hashtags, no emojis, no bullet points

---

## Run order

```bash
# Web UI (recommended)
python app.py                          # opens at http://localhost:8080

# CLI
python voice_problem.py                # evolve prompt → evolved_prompt.txt
python generate_posts.py <pubmed-url>  # generate 3 posts → posts/YYYY-MM-DD/
```

---

## Fine-tune (pending)

Model: `gpt-4o-mini`. Waiting on user to provide MD file with writing samples.
Once received: chunk → JSONL → upload → fine-tune job → swap model ID in `app.py` + `generate_posts.py`.

---

### 2026-06-25 — Migration to gpt-4o + web app + evolver fixes

**Stack migration: Gemma → gpt-4o**
- All `.py` files migrated from LM Studio/Gemma to OpenAI API (`gpt-4o`)
- Removed: LM Studio context workarounds (`ABSTRACT_CHARS=250`, retry delays, `ends_clean` check)
- Full paper abstract now passed to generation (no truncation)
- `voice_problem.py`: merged two clients (`GEMMA` + `GPT4O`) into one `CLIENT = OpenAI()`

**Evolver fixes**
- Root cause of prior bad posts: `EVAL_SYSTEM` scored generic LinkedIn quality, not Kruthik's voice
- Fixed: injected `voice_profile.json` + Edison paper reflections section into `EVAL_SYSTEM` and `MUTATE_SYSTEM`
- gpt-4o now evaluates specifically against Kruthik's voice patterns
- Evolver retired in favor of a hand-crafted system prompt grounded in the Edison paper writing sample
- `evolved_prompt.txt` now contains Edison reflections as concrete voice example + 8 explicit rules
- Key rule added: no em dashes, no hallucinated names

**Web app**
- Added `app.py` — Flask server on port 8080 (port 5000 blocked by macOS AirPlay)
- `search.html` updated: "Copy generate command" → "Generate Posts" button
- Clicking Generate Posts calls `/generate`, shows Mon/Wed/Fri posts inline with Copy buttons
- Posts still auto-saved to `posts/YYYY-MM-DD/`

**Fine-tune (pending)**
- Decision: fine-tune `gpt-4o-mini` on Kruthik's writing for voice matching
- Waiting on user to provide MD file with writing samples
- Plan: chunk → JSONL → OpenAI Files API → fine-tune job → swap model ID

---

### 2026-06-24 — Ponytail audit + cuts

Ran `/ponytail-audit` repo-wide. All 5 findings applied. **net: -13 lines, -0 deps.**

| Tag | Cut | File |
|---|---|---|
| `shrink` | 4-line markdown fence stripping → 1 regex | `extract_voice.py` |
| `yagni` | `VoiceProblem` class flattened to module-level functions; thin `_Adapter` kept for darwinian_evolver compat | `voice_problem.py` |
| `delete` | Dead `organism` parameter removed from `evaluate_organism` | `voice_problem.py` |
| `yagni` | `get_prompt()` single-caller function inlined into `main()` | `generate_posts.py` |
| `shrink` | `first_author` 4-line block collapsed to 1 line | `generate_posts.py` |
