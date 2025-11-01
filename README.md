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

# Configure cache TTL (default: 300 seconds)
secrets = GCPSecrets(cache=True, cache_ttl_seconds=600)
```

## Cache Behavior

⚠️ **Important:** Understanding cache behavior is critical for production use.

### Default Caching

By default, secrets are cached in memory for **5 minutes (300 seconds)**:

```python
secrets = GCPSecrets()  # cache=True, cache_ttl_seconds=300
api_key = secrets['API_KEY']  # Fetches from GCP
api_key = secrets['API_KEY']  # Returns cached value (fast)
# After 5 minutes, the next access will refresh from GCP
```

### Cache TTL (Time-To-Live)

You can customize the cache expiration time:

```python
# Cache for 10 minutes
secrets = GCPSecrets(cache_ttl_seconds=600)

# Cache for 1 minute (more frequent updates)
secrets = GCPSecrets(cache_ttl_seconds=60)

# Cache for 1 hour (less API calls, but stale data risk)
secrets = GCPSecrets(cache_ttl_seconds=3600)
```

### When to Disable Caching

Disable caching when you need **always-fresh** values:

```python
# Always fetch from GCP (slower, but guarantees fresh data)
secrets = GCPSecrets(cache=False)
```

**Use cache=False when:**
- Testing secret rotation
- Running short-lived scripts
- Secrets change very frequently
- You need to verify the latest value immediately

### Cache Implications

| Scenario | Recommendation | Example |
|----------|---------------|---------|
| **Long-running web app** | Use caching with appropriate TTL | `GCPSecrets(cache_ttl_seconds=300)` |
| **Background worker** | Use caching with shorter TTL | `GCPSecrets(cache_ttl_seconds=60)` |
| **Short script** | Disable cache | `GCPSecrets(cache=False)` |
| **High-security secrets** | Shorter TTL or no cache | `GCPSecrets(cache_ttl_seconds=60)` |
| **Frequently rotated secrets** | Disable cache | `GCPSecrets(cache=False)` |

### Secret Rotation

When you rotate a secret in GCP:
- **With caching:** The old value remains cached until TTL expires
- **Without caching:** The new value is retrieved immediately

Example:
```python
secrets = GCPSecrets(cache_ttl_seconds=300)
api_key = secrets['API_KEY']  # Gets "old-key-123"

# You rotate the secret in GCP Console to "new-key-456"
api_key = secrets['API_KEY']  # Still returns "old-key-123" (cached)

# Wait 5 minutes (TTL expires)
api_key = secrets['API_KEY']  # Now returns "new-key-456" (refreshed)
```

### Memory Considerations

- Each unique secret/version accessed is cached separately
- Cache grows with the number of unique secrets accessed
- Cache is per-instance (creating a new instance starts fresh)
- Consider cache size for applications accessing many secrets

```python
# For applications with many secrets, use shorter TTL
secrets = GCPSecrets(cache_ttl_seconds=60)  # Faster cache expiration
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

**Note:** If you don't specify a project and ADC doesn't provide one, a `ValueError` will be raised with instructions. You can either:
- Provide a project explicitly: `GCPSecrets(project="my-project")`
- Configure ADC: `gcloud auth application-default login`

## Features

- Dictionary-like interface for intuitive secret access
- Automatic version management (latest vs. specific versions)
- Optional caching for improved performance
- Support for custom GCP projects
- Pythonic error handling (raises `KeyError` for missing secrets)

## License

Apache 2.0