# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`gcpsecrets` is a Python library that provides a dictionary-like interface for accessing Google Cloud Platform (GCP) Secret Manager. It wraps the official `google-cloud-secret-manager` client with a simpler, more Pythonic API.

## Core Architecture

### Main Component: GCPSecrets Class (gcpsecrets/__init__.py)

The `GCPSecrets` class implements Python's dictionary protocol (`__getitem__`, `__contains__`) to provide transparent access to GCP secrets.

**Key Design Patterns:**
- **Dual Key Types**: Supports both `str` (latest version) and `tuple[str, str]` (specific version) as keys
  - `secrets['API_KEY']` → latest active version
  - `secrets[('API_KEY', '1')]` → specific version
- **Optional Caching**: Constructor parameter `cache=True` (default) stores retrieved secrets and version metadata in memory
  - `self.versions` dict: maps `(key, version)` tuples to GCP resource names
  - `self.secrets` dict: maps keys to decoded secret values
- **Lazy Version Resolution**: The `_get_adress()` method queries GCP to list all active versions and determines the "latest" by finding the maximum `create_time`
- **Read-Only**: `__setitem__` raises `NotImplementedError`

**Important Implementation Details:**
- Line 39: typo `self.versoins` should be `self.versions` (when cache is disabled)
- Lines 94-101: Active versions filtered by `state == 1`, "latest" computed as max by creation time
- Error handling: GCP `NotFound` exceptions converted to Python `KeyError` (line 92)

## Development Commands

### Dependency Management
This project uses uv for dependency management:
```bash
# Install dependencies
uv sync

# Add new dependency
uv add <package>

# Add dev dependency
uv add --dev <package>

# Install the package in editable mode
uv pip install -e .
```

### Testing
```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_values.py

# Run specific test function
uv run pytest tests/test_values.py::test_existence

# Run with verbose output
uv run pytest -v

# Run tests matching a pattern
uv run pytest -k "test_content"
```

**Test Structure:**
- `tests/test_concrete.py`: Unit tests for GCPSecrets initialization and configuration
- `tests/test_values.py`: Integration tests requiring actual GCP secrets (gcpsecrets1, gcpsecrets2)
- Tests use session-scoped fixtures with caching enabled for efficiency

### Code Formatting
```bash
# Format code with black
uv run black gcpsecrets tests

# Check formatting without modifying
uv run black --check gcpsecrets tests
```

### Pre-commit Hooks
```bash
# Install pre-commit hooks
uv run pre-commit install

# Run hooks manually
uv run pre-commit run --all-files
```

## GCP Authentication

The library uses Application Default Credentials (ADC). When no project is specified:
- Line 48: Uses `google.auth.default()` to determine the project from the environment
- Set project explicitly: `GCPSecrets(project="my-project")`

## Testing Notes

Integration tests in `test_values.py` expect specific secrets to exist:
- `gcpsecrets1`: version 1 = "old_version", latest = "new_one"
- `gcpsecrets2`: version 1 = "original", latest = "original"

These tests require valid GCP credentials and an accessible project with these secrets configured.
