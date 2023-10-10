# gcpsecrets
GCP Secret Manager as Python Dictonary

### Install
pip install git+https://github.com/tvaroska/gcpsecrets

### Ussage

Dictionary accepts two types of keys:
- str: the latest active version of the secter
- tuple[str, str]: the exact version of the secret

Examples:

from gcpsecrets import GCPSecrets

secrets = GCPSecrets() # to use other than default project use argument project=...

api_key = secrets['API_KEY']