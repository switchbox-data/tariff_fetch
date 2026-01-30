#!/usr/bin/env bash
set -euo pipefail

# install-python-deps.sh - Install Python dependencies using uv
#
# Usage:
#   ./install-python-deps.sh [path/to/workspace]
#
# This script:
# 1. Checks if Python is installed
# 2. Installs uv package manager
# 3. Installs Python dependencies from pyproject.toml + uv.lock
#
# Requirements:
#   - Python must be installed
#   - pyproject.toml and uv.lock must exist in the workspace directory

WORKSPACE_PATH="${1:-.}"

echo "===================================================================="
echo "🐍 Installing Python dependencies from pyproject.toml + uv.lock"
echo "===================================================================="
echo

# Check if Python is installed
if command -v python3 >/dev/null 2>&1; then
  PYTHON_VERSION=$(python3 --version)
  echo "✅ Using: ${PYTHON_VERSION}"
else
  echo "❌ ERROR: Python is not installed" >&2
  echo "" >&2
  echo "Please install Python before running this script:" >&2
  echo "  • Ubuntu/Debian: sudo apt-get install python3" >&2
  echo "  • macOS: brew install python3" >&2
  exit 1
fi
echo

# Check if pyproject.toml exists
PYPROJECT_PATH="${WORKSPACE_PATH}/pyproject.toml"
if [ -f "${PYPROJECT_PATH}" ]; then
  echo "✅ Found pyproject.toml: $(realpath "${PYPROJECT_PATH}")"
else
  echo "❌ ERROR: pyproject.toml is necessary but not found in ${WORKSPACE_PATH}" >&2
  exit 1
fi
echo

# Check if uv is already installed
# Add common uv installation paths to PATH for checking
export PATH="${HOME}/.local/bin:${PATH}"

if command -v uv >/dev/null 2>&1; then
  UV_VERSION=$(uv --version 2>&1)
  echo "✅ uv already installed: ${UV_VERSION}"
else
  # Install uv package manager
  echo "📦 Installing uv package manager..."
  curl -LsSf https://astral.sh/uv/install.sh | sh

  # Add uv to PATH for this session so command can be used
  # The installer adds uv to ~/.local/bin
  export PATH="${HOME}/.local/bin:${PATH}"

  # Verify installation
  if UV_VERSION=$(uv --version 2>&1); then
    echo "✅ Installed: ${UV_VERSION}"
  else
    echo "❌ ERROR: uv installation failed or uv command not found" >&2
    echo "Expected location: ${HOME}/.local/bin/uv" >&2
    exit 1
  fi
fi
echo

# Change to workspace directory
cd "${WORKSPACE_PATH}"

# Install Python dependencies
echo "📥 Installing Python dependencies from pyproject.toml + uv.lock..."
UV_OUTPUT=$(uv sync --group dev 2>&1)
echo "$UV_OUTPUT"
echo

# Parse uv output to determine what happened
if echo "$UV_OUTPUT" | grep -q "Installed [0-9]"; then
  PACKAGE_COUNT=$(echo "$UV_OUTPUT" | grep -o "Installed [0-9]\+ package" | grep -o "[0-9]\+")
  echo "✅ Installed ${PACKAGE_COUNT} Python packages"
elif echo "$UV_OUTPUT" | grep -q "Audited [0-9]"; then
  PACKAGE_COUNT=$(echo "$UV_OUTPUT" | grep -o "Audited [0-9]\+ package" | grep -o "[0-9]\+")
  echo "✅ ${PACKAGE_COUNT} Python packages already installed"
else
  echo "✅ Python packages ready"
fi
echo

echo "===================================================================="
echo "✨ Python dependencies installed successfully!"
echo "===================================================================="
echo
echo
