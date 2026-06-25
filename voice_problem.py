"""
Darwinian Evolver problem: evolve a system prompt to match Kruthik's LinkedIn voice.

Generation: Gemma 4 E4B via LM Studio (local, free)
Evaluation + mutation: gpt-4o via OpenAI API (sparingly)
"""
import json
from pathlib import Path
from openai import OpenAI

CLIENT = OpenAI()
MODEL  = "gpt-4o"

SEED_PROMPT = """\
You are writing a LinkedIn post in the voice of Kruthik Hulisandra — Rutgers MBS student, \
Silicon Valley resident, community builder who runs gatherings on focus and cognition.

Rules:
1. Open with a macro historical or economic force (an era, a crisis, an institutional shift) \
and WHY it mattered to everyone. This is not background — it IS the argument.
2. Zoom from that macro context into something personal and specific: \
a conversation you had, an experiment you ran, a mistake you made.
3. Use a named framework or structure, but deploy it conversationally — \
it should feel like thinking out loud, not a listicle.
4. Ask a bold rhetorical question somewhere in the middle.
5. End with a single punchy sentence or challenge to the reader. \
Signature move: short, declarative, stakes the claim personally.
6. Never sound like a content creator giving tips. \
Sound like someone who just had an insight and has not edited it yet.
7. Max 200 words. No hashtags. No emojis."""

VOICE_PROFILE = json.loads(Path("voice_profile.json").read_text(encoding="utf-8"))
_writing = Path("writing_sample.txt").read_text(encoding="utf-8")
WRITING_SAMPLE = _writing[_writing.index("---REFLECTIONS---"):].strip()

EVAL_SYSTEM = f"""\
You are evaluating whether a LinkedIn post sounds like Kruthik Hulisandra specifically.

Here is Kruthik's actual writing — this is the GROUND TRUTH for his voice:
{WRITING_SAMPLE}

His extracted voice patterns:
- Opening move: macro historical/economic force IS the argument, then zoom personal
- Closing move: short punchy question or declarative that stakes claim ("So why can't it be me?")
- Recurring moves: "This mirrors...", "This shows that...", names real people he met with their title and context, admits mistakes plainly, parenthetical asides
- Register: academic rigor + Silicon Valley directness — structured but never stiff

Score on five criteria. All scores 0.0–1.0. Return ONLY valid JSON:
{{
  "macro_opening": 0.0,
  "personal_zoom": 0.0,
  "kruthik_voice": 0.0,
  "punchy_close": 0.0,
  "not_generic": 0.0,
  "overall": 0.0,
  "feedback": "what is weak or missing, quote the problem line"
}}

macro_opening (0.0–1.0): opens with a real historical/economic/institutional force as the argument — not a broad observation
personal_zoom (0.0–1.0): zooms into something specific — a real person Kruthik met (with title/context), an experiment, a mistake admitted plainly
kruthik_voice (0.0–1.0): matches his actual moves — "This mirrors...", parenthetical asides, analytical label after story, tonal markers from his writing
punchy_close (0.0–1.0): ends short and declarative — stakes a personal claim or challenges reader, NEVER summarizes
not_generic (0.0–1.0): could NOT have been written by anyone else — no hallucinated names, no buzzwords, no AI filler phrases
overall (0.0–1.0): weighted mean — penalize hard if it reads like generic LinkedIn"""

MUTATE_SYSTEM = f"""\
You are a prompt engineer. Rewrite this system prompt so it produces posts that sound \
specifically like Kruthik Hulisandra — not generic LinkedIn content.

Kruthik's actual writing (ground truth):
{WRITING_SAMPLE}

His voice patterns:
{json.dumps(VOICE_PROFILE, indent=2)}

Fix the weaknesses in the feedback. Return ONLY the new prompt text — no explanation, no preamble."""

TEST_TOPIC = (
    "I ran a handwriting-and-focus experiment at my community gathering. "
    "Participants took notes by hand vs. laptop during a talk. "
    "The paper I based it on: a 2024 RCT showing handwriting improves retention by 30% "
    "vs. typing. Here is what I actually observed and where the research did not predict."
)


def generate_with_organism(organism: str) -> str:
    resp = CLIENT.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": organism},
            {"role": "user", "content": f"Write a LinkedIn post about: {TEST_TOPIC}"},
        ],
        temperature=0.85,
        max_tokens=450,
    )
    return resp.choices[0].message.content.strip()


def evaluate_organism(generated: str) -> tuple[float, str]:
    resp = CLIENT.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": EVAL_SYSTEM},
            {"role": "user", "content": generated},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    result = json.loads(resp.choices[0].message.content)
    return float(result["overall"]), result["feedback"]


def mutate_organism(organism: str, feedback: str) -> str:
    resp = CLIENT.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": MUTATE_SYSTEM},
            {"role": "user", "content": f"Current prompt:\n{organism}\n\nFeedback:\n{feedback}"},
        ],
        temperature=0.7,
    )
    return resp.choices[0].message.content.strip()


def _manual_evolve(n_iterations: int) -> str:
    organism = SEED_PROMPT
    best_score, best_organism = 0.0, organism

    for i in range(n_iterations):
        generated = generate_with_organism(organism)
        score, feedback = evaluate_organism(generated)
        print(f"  iter {i+1:2d}: score={score:.2f} | {feedback[:80]}...")
        if score > best_score:
            best_score, best_organism = score, organism
        if score < 0.75:
            organism = mutate_organism(organism, feedback)

    Path("evolved_prompt.txt").write_text(best_organism)
    print(f"evolved_prompt.txt written (best score: {best_score:.2f})")
    return best_organism


def run_evolution(n_iterations: int = 20) -> str:
    try:
        from darwinian_evolver import evolve

        class _Adapter:
            initial_organism = SEED_PROMPT
            def generate_with_organism(self, org): return generate_with_organism(org)
            def evaluate_organism(self, org, gen): return evaluate_organism(gen)
            def mutate_organism(self, org, fb): return mutate_organism(org, fb)

        best = evolve(_Adapter(), n_iterations=n_iterations)
        Path("evolved_prompt.txt").write_text(best)
        print(f"evolved_prompt.txt written ({n_iterations} iterations)")
        return best
    except (ImportError, TypeError):
        print("darwinian_evolver not found or API mismatch — running manual loop")
        return _manual_evolve(n_iterations)


if __name__ == "__main__":
    run_evolution()
