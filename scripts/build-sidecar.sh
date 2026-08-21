#!/usr/bin/env bash

set -euo pipefail

repo_root=$(cd "$(dirname "$0")/.." && pwd)
cd "$repo_root"

rm -rf build/sherpa-backend artifacts/backend
backend/.venv/bin/pyinstaller \
  --noconfirm \
  --clean \
  --onedir \
  --name sherpa-backend \
  --paths "$repo_root" \
  --hidden-import backend.main \
  --add-data "backend/skills:backend/skills" \
  --add-data "backend/task_planning_skill.md:backend" \
  --add-data "backend/tool_manifest.json:backend" \
  --distpath artifacts/backend \
  --workpath build/sherpa-backend \
  backend/sidecar.py
