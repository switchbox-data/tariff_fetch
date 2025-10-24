# =============================================================================
# ⭐ DEFAULT
# =============================================================================
# If you run `just` you should get the options available, not a full install of the package

default:
    @just --list


# =============================================================================
# 🔍 CODE QUALITY & TESTING
# =============================================================================
# These commands check your code quality and run tests

# Run code quality tools
check:
    echo "🚀 Checking lock file consistency with 'pyproject.toml'"
    uv lock --locked
    echo "🚀 Linting, formatting, and type checking code"
    prek run -a
    echo "🚀 Checking for obsolete dependencies: Running deptry"
    uv run deptry .

# Test the code with pytest
test:
    echo "🚀 Testing code: Running pytest"
    uv run python -m pytest --doctest-modules





# =============================================================================
# 📚 DOCUMENTATION
# =============================================================================
# These commands help you build and serve project documentation

# Test if documentation can be built without warnings or errors
docs-test:
    uv run mkdocs build -s

# Build and serve the documentation
docs:
    uv run mkdocs serve

# =============================================================================
# 📦 BUILD & RELEASE
# =============================================================================
# These commands build your package and publish it to PyPI

# Clean build artifacts
clean-build:
    echo "🚀 Removing build artifacts"
    uv run python -c "import shutil; import os; shutil.rmtree('dist') if os.path.exists('dist') else None"

# Build wheel file
build: clean-build
    echo "🚀 Creating wheel file"
    uvx --from build pyproject-build --installer uv

# Publish a release to PyPI
publish:
    echo "🚀 Publishing."
    uvx twine upload --repository-url https://upload.pypi.org/legacy/ dist/*

# Build and publish
build-and-publish: build publish


# =============================================================================
# 🏗️  DEVELOPMENT ENVIRONMENT SETUP
# =============================================================================
# These commands help you set up your development environment

# Install the virtual environment and install the pre-commit hooks
install:
    echo "🚀 Creating virtual environment using uv"
    .devcontainer/postCreateCommand.sh

# Clean generated files and caches
clean:
    rm -rf .pytest_cache .ruff_cache site dist build tmp


rateacuity:
    uv run python -m tariff_fetch.rateacuity.state

openei:
    uv run python -m tariff_fetch.openei.utility_rates "Consolidated Edison Co-NY Inc"

arcadia:
    uv run python -m tariff_fetch.genability.tariffs 2252

cli:
    uv run python -m tariff_fetch.cli

cligas:
    uv run python -m tariff_fetch.cli_gas
