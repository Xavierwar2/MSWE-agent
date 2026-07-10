#!/usr/bin/env bash
set -euo pipefail

DEFAULT_PR_FILE="data/ts/vuejs__core_dataset.jsonl"
DEFAULT_MODEL_NAME="gpt54"
DEFAULT_CONFIG_FILE="config/default.yaml"

usage() {
  cat <<'EOF'
Usage:
  ./run.sh [test_cases.jsonl] [extra run.py args...]
  ./run.sh --test-cases tests/test_cases/test_cases_vuejs.jsonl [extra run.py args...]
  ./run.sh --instance vuejs__core-8911 [extra run.py args...]

Options:
  --test-cases PATH     File with lines like vuejs/core:pr-8911.
  --instance ID         Instance id accepted by run.py, e.g. vuejs__core-8911.
  --pr-file PATH        Dataset jsonl passed to run.py. Default: data/ts/vuejs__core_dataset.jsonl.
  --model-name NAME     Model name passed to run.py. Default: gpt54.
  --config-file PATH    Config file passed to run.py. Default: config/default.yaml.
  --dry-run             Print the resolved command without executing it.
  -h, --help            Show this help.

Any other arguments are forwarded to run.py after the defaults.
EOF
}

test_cases_file=""
instance_filter=""
pr_file="$DEFAULT_PR_FILE"
model_name="$DEFAULT_MODEL_NAME"
config_file="$DEFAULT_CONFIG_FILE"
dry_run=false
extra_args=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --test-cases)
      test_cases_file="${2:?--test-cases requires a path}"
      shift 2
      ;;
    --instance)
      instance_filter="^${2:?--instance requires an instance id}$"
      shift 2
      ;;
    --instance-filter|--instance_filter)
      instance_filter="${2:?--instance-filter requires a regex}"
      shift 2
      ;;
    --pr-file|--pr_file)
      pr_file="${2:?--pr-file requires a path}"
      shift 2
      ;;
    --model-name|--model_name)
      model_name="${2:?--model-name requires a model name}"
      shift 2
      ;;
    --config-file|--config_file)
      config_file="${2:?--config-file requires a path}"
      shift 2
      ;;
    --dry-run)
      dry_run=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    -*)
      extra_args+=("$1")
      if [[ $# -gt 1 && "$2" != -* ]]; then
        extra_args+=("$2")
        shift 2
      else
        shift
      fi
      ;;
    *)
      if [[ -z "$test_cases_file" && -f "$1" ]]; then
        test_cases_file="$1"
      elif [[ -z "$instance_filter" ]]; then
        instance_filter="^$1$"
      else
        extra_args+=("$1")
      fi
      shift
      ;;
  esac
done

if [[ -n "$test_cases_file" ]]; then
  if [[ ! -f "$test_cases_file" ]]; then
    echo "Test cases file not found: $test_cases_file" >&2
    exit 1
  fi

  instance_filter="$(python3 - "$test_cases_file" <<'PY'
from __future__ import annotations

import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
ids: list[str] = []
seen: set[str] = set()

for raw_line in path.read_text(encoding="utf-8").splitlines():
    line = raw_line.strip()
    if not line or line.startswith("#"):
        continue

    match = re.fullmatch(r"([^/\s]+)/([^:\s]+):pr-(\d+)", line)
    if match:
        org, repo, number = match.groups()
        instance_id = f"{org}__{repo}-{number}"
    else:
        instance_id = line

    if instance_id not in seen:
        seen.add(instance_id)
        ids.append(instance_id)

if not ids:
    raise SystemExit(f"No instances found in {path}")

print("^(" + "|".join(re.escape(instance_id) for instance_id in ids) + ")$")
PY
)"
fi

cmd=(
  python3 run.py
  --model_name "$model_name"
  --cache_task_images True
  --pre_build_all_images False
  --remove_image False
  --pr_file "$pr_file"
  --config_file "$config_file"
  --skip_existing=True
  --per_instance_cost_limit 5.00
  --print_config=False
  --max_workers_build_image 16
)

if [[ -n "$instance_filter" ]]; then
  cmd+=(--instance_filter "$instance_filter")
fi

cmd+=("${extra_args[@]}")

if [[ "$dry_run" == true ]]; then
  printf '%q ' "${cmd[@]}"
  printf '\n'
  exit 0
fi

exec "${cmd[@]}"
