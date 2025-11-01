# gcpsecrets

GCP Secret Manager as Python Dictionary

A Python library that provides a simple, dictionary-like interface for accessing Google Cloud Platform Secret Manager.

## Installation

```bash
pip install gcpsecrets
```

## Usage

The `GCPSecrets` class implements Python's dictionary protocol, allowing you to access secrets using familiar syntax.

### Basic Example

```python
from gcpsecrets import GCPSecrets

# Use default project from Application Default Credentials
secrets = GCPSecrets()

# Access the latest version of a secret
api_key = secrets['API_KEY']
```

### Key Types

The dictionary accepts two types of keys:
- `str`: Returns the latest active version of the secret
- `tuple[str, str]`: Returns a specific version of the secret

```python
from gcpsecrets import GCPSecrets

secrets = GCPSecrets()

# Get latest version
latest_key = secrets['API_KEY']

# Get specific version
version_1_key = secrets[('API_KEY', '1')]
version_2_key = secrets[('API_KEY', '2')]
```

### Configuration Options

```python
from gcpsecrets import GCPSecrets

# Specify a different GCP project
secrets = GCPSecrets(project="my-gcp-project")

# Disable caching (queries GCP on every access)
secrets = GCPSecrets(cache=False)

# Configure exception handling
secrets = GCPSecrets(raise_exceptions=True)
```

### Dictionary Operations

```python
from gcpsecrets import GCPSecrets

secrets = GCPSecrets()

# Check if a secret exists
if 'API_KEY' in secrets:
    api_key = secrets['API_KEY']

# Check for specific version
if ('API_KEY', '1') in secrets:
    old_key = secrets[('API_KEY', '1')]

# Use the get() method
api_key = secrets.get('API_KEY')
version_key = secrets.get(('API_KEY', '1'))
```

## Authentication

This library uses [Application Default Credentials (ADC)](https://cloud.google.com/docs/authentication/provide-credentials-adc) for authentication. Ensure you have authenticated using one of these methods:

- `gcloud auth application-default login` (for local development)
- Service account key in `GOOGLE_APPLICATION_CREDENTIALS` environment variable
- GCP-managed credentials (when running on GCP services)

## Features

- Dictionary-like interface for intuitive secret access
- Automatic version management (latest vs. specific versions)
- Optional caching for improved performance
- Support for custom GCP projects
- Pythonic error handling (raises `KeyError` for missing secrets)

## License

Apache 2.0