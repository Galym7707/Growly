"""Sync HuggingFace Space secrets from an env blob.

Used by the "Deploy to HuggingFace Space" GitHub Action. Reads:
  HF_TOKEN  - HuggingFace write token (required)
  HF_SPACE  - target space repo id, e.g. Galym7707/GrowlyAI (required)
  HF_ENV    - full .env contents (optional). Each KEY=VALUE line becomes a
              Space secret. If empty/unset, nothing is synced.

Kept out of the workflow YAML so there is no fragile inline heredoc.
"""

from __future__ import annotations

import os
import sys


def main() -> int:
    token = os.environ.get("HF_TOKEN", "").strip()
    space = os.environ.get("HF_SPACE", "").strip()
    env_blob = os.environ.get("HF_ENV", "")

    if not token or not space:
        print("HF_TOKEN and HF_SPACE are required.", file=sys.stderr)
        return 1

    if not env_blob.strip():
        print("HF_ENV not set - skipping Space secret sync.")
        return 0

    from huggingface_hub import HfApi

    api = HfApi(token=token)

    count = 0
    for line in env_blob.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            continue
        api.add_space_secret(repo_id=space, key=key, value=value)
        count += 1
        print(f"set secret: {key}")

    api.add_space_variable(
        repo_id=space, key="RUN_DATABASE_MIGRATIONS", value="true"
    )
    print(f"Done: {count} secrets synced.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
