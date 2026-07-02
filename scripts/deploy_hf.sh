#!/usr/bin/env bash
#
# Deploy Growly to the HuggingFace Space Galym7707/GrowlyAI from your own
# machine. This bypasses GitHub Actions entirely (no billing needed) and the
# Claude Code cloud network block.
#
# Prereqs:
#   - Run from the repo root (folder with Dockerfile + README.md).
#   - Your real .env in the repo root (gitignored - it is NOT committed/pushed).
#   - A HuggingFace WRITE token: https://huggingface.co/settings/tokens
#   - pip install "huggingface_hub>=0.25"
#
# Usage:
#   export HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxx
#   bash scripts/deploy_hf.sh
#
set -euo pipefail

HF_SPACE="Galym7707/GrowlyAI"
HF_USERNAME="Galym7707"
: "${HF_TOKEN:?Set HF_TOKEN to a HuggingFace write token first (export HF_TOKEN=hf_...)}"

echo "==> 1/2  Pushing code to https://huggingface.co/spaces/${HF_SPACE}"
git remote remove hf 2>/dev/null || true
git remote add hf "https://${HF_USERNAME}:${HF_TOKEN}@huggingface.co/spaces/${HF_SPACE}"
# The Space is a deploy target; force-push main so it mirrors this repo.
# .env is gitignored, so ONLY code is pushed - never the .env file itself.
git push --force hf HEAD:main

echo "==> 2/2  Setting Space secrets from .env (via HuggingFace Secrets API)"
if [ -f .env ]; then
  HF_SPACE="$HF_SPACE" HF_ENV="$(cat .env)" python3 scripts/hf_deploy_secrets.py
else
  echo "No .env found in repo root - skipping secret sync."
  echo "Set the Space env vars manually in the HuggingFace UI if needed."
fi

echo "==> Done. Watch the build at https://huggingface.co/spaces/${HF_SPACE}"
