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
This project uses Poetry for dependency management:
```bash
# Install dependencies
poetry install

# Add new dependency
poetry add <package>

# Add dev dependency
poetry add --group dev <package>
```

### Testing
```bash
# Run all tests
poetry run pytest

# Run specific test file
poetry run pytest tests/test_values.py

# Run specific test function
poetry run pytest tests/test_values.py::test_existence

# Run with verbose output
poetry run pytest -v

# Run tests matching a pattern
poetry run pytest -k "test_content"
```

**Test Structure:**
- `tests/test_concrete.py`: Unit tests for GCPSecrets initialization and configuration
- `tests/test_values.py`: Integration tests requiring actual GCP secrets (gcpsecrets1, gcpsecrets2)
- Tests use session-scoped fixtures with caching enabled for efficiency

### Code Formatting
```bash
# Format code with black
poetry run black gcpsecrets tests

# Check formatting without modifying
poetry run black --check gcpsecrets tests
```

### Pre-commit Hooks
```bash
# Install pre-commit hooks
poetry run pre-commit install

# Run hooks manually
poetry run pre-commit run --all-files
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
