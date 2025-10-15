#!/usr/bin/env bash

# This script is for Linux/macOS and devcontainer usage

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Dependencies
uv sync --group dev # Also install dev dependencies

# Install prek
curl --proto '=https' --tlsv1.2 -LsSf https://github.com/j178/prek/releases/download/v0.2.2/prek-installer.sh | sh

# Install pre-commit hooks
prek install --install-hooks

