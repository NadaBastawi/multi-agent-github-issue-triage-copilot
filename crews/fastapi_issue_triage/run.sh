#!/bin/bash
# Run script for fastapi_issue_triage crew

set -e

echo "Starting fastapi_issue_triage crew..."

if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment with uv..."
    uv venv
fi

echo "Installing dependencies with uv..."
uv sync

echo "Running crew with arguments: $*"
uv run fastapi_issue_triage "$@"
