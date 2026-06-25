"""Read writing_sample.txt, extract voice patterns via Gemma, write voice_profile.json."""
import re
import json
import sys
from pathlib import Path
from openai import OpenAI

CLIENT = OpenAI()
MODEL = "gpt-4o"

SYSTEM = """Analyze this writing sample and extract the author's voice patterns.
Return ONLY a valid JSON object with these exact keys:

{
  "sentence_patterns": {
    "short_punchy": "when and why the author uses short sentences — quote 2-3 examples",
    "long_analytical": "when and why the author uses long sentences — quote 2-3 examples"
  },
  "opening_move": "how the author opens pieces — describe the pattern specifically",
  "closing_move": "how the author closes — describe the pattern and quote the signature move",
  "recurring_moves": ["list of specific structural moves with examples"],
  "tonal_markers": ["actual words or phrases the author uses repeatedly"],
  "voice_summary": "one paragraph — what makes this voice distinct"
}"""


def main():
    sample = Path("writing_sample.txt")
    if not sample.exists():
        sys.exit("writing_sample.txt not found.")

    resp = CLIENT.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": sample.read_text()},
        ],
        temperature=0.2,
        max_tokens=1200,
    )

    raw = re.sub(r"^```json?\n?", "", resp.choices[0].message.content.strip()).rstrip("`").strip()

    profile = json.loads(raw)
    Path("voice_profile.json").write_text(json.dumps(profile, indent=2))
    print("voice_profile.json written.")


if __name__ == "__main__":
    main()
