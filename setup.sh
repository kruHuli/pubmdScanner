#!/usr/bin/env bash
set -e

echo "=== LinkedIn Pipeline Setup ==="

# 1. Check LM Studio
echo ""
echo "Checking LM Studio at http://localhost:1234/v1 ..."
if curl -s --max-time 5 http://localhost:1234/v1/models > /dev/null 2>&1; then
  echo "  LM Studio is running."
  echo "  Loaded models:"
  curl -s http://localhost:1234/v1/models | python3 -c \
    "import sys,json; [print('   -', m['id']) for m in json.load(sys.stdin)['data']]" 2>/dev/null || true
else
  echo "  ERROR: LM Studio is not running or not reachable at localhost:1234."
  echo "  Start LM Studio, load Gemma 3 4B Instruct, and enable the local server."
  exit 1
fi

# 2. Check OPENAI_API_KEY
echo ""
echo "Checking OPENAI_API_KEY ..."
if [ -z "${OPENAI_API_KEY}" ]; then
  echo "  ERROR: OPENAI_API_KEY is not set."
  echo "  Run: export OPENAI_API_KEY=sk-..."
  exit 1
else
  echo "  OPENAI_API_KEY is set (${#OPENAI_API_KEY} chars)."
fi

# 3. Install darwinian_evolver and openai via uv
echo ""
echo "Installing dependencies via uv ..."
if ! command -v uv &> /dev/null; then
  echo "  uv not found — installing via pip ..."
  pip install uv --quiet
fi

uv pip install --quiet \
  "openai>=1.0" \
  "git+https://github.com/imbue-ai/darwinian_evolver.git"

echo "  Dependencies installed."

# 4. Create folder structure
echo ""
echo "Creating folder structure ..."
mkdir -p posts

echo "  posts/ ready."

# 5. Summary
echo ""
echo "=== Setup complete ==="
echo ""
echo "Run these in order:"
echo ""
echo "  1. Extract your voice profile (optional — voice_profile.json already seeded):"
echo "       python extract_voice.py"
echo ""
echo "  2. Evolve the writing prompt (20 iterations, uses gpt-4o for eval/mutation):"
echo "       python voice_problem.py"
echo ""
echo "  3. Generate posts from a PubMed paper:"
echo "       python generate_posts.py https://pubmed.ncbi.nlm.nih.gov/XXXXXXXX/"
echo ""
echo "  4. Run the full weekly pipeline via Omnigent:"
echo "       omnigent run linkedin_pipeline.yaml"
echo ""
echo "NOTE: Make sure your LM Studio model ID matches GEMMA_MODEL in each .py file."
echo "      Check with: curl -s http://localhost:1234/v1/models | python3 -m json.tool"
