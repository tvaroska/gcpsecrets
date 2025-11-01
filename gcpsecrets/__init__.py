"""
GCS Secret Manager interface in form of Python Dictionary. Read-only for now

Usage with default project:
    secrets = GCPSecrets()
    api_key = secrets['API_KEY']

Cache behavior:
    By default, secrets are cached for cache_ttl_seconds (default: 300s).
    Set cache=False to always fetch fresh values (slower but no stale data).
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Optional, Union

import google.auth
from google.api_core.exceptions import NotFound
from google.cloud import secretmanager

logger = logging.getLogger(__name__)

KEY_ERROR = "Key can be either string or tuple with 2 strings. Got {} with value {}"


class GCPSecrets:
    """
    GCP Secret Manager interface in form of Python Dictionary. Read-only for now.

    Args:
        project: GCP project ID. If None, uses Application Default Credentials.
        cache: Enable in-memory caching of secrets (default: True)
        cache_ttl_seconds: Time-to-live for cached secrets in seconds (default: 300)

    Usage with default project:
        secrets = GCPSecrets()
        api_key = secrets['API_KEY']

    Cache behavior:
        - Cached secrets expire after cache_ttl_seconds
        - Set cache=False to always fetch fresh values (slower)
        - Rotated secrets are automatically refreshed after TTL expires

    Examples:
        # With caching (recommended for most cases)
        secrets = GCPSecrets(cache=True, cache_ttl_seconds=300)
        api_key = secrets['API_KEY']

        # Without caching (always fresh, but slower)
        secrets = GCPSecrets(cache=False)
        api_key = secrets['API_KEY']

        # Specific version
        old_key = secrets[('API_KEY', '1')]
    """

    def __init__(
        self,
        project: Optional[str] = None,
        cache: Optional[bool] = True,
        cache_ttl_seconds: int = 300,
    ):
        """
        Initialize GCPSecrets client.

        Args:
            project: GCP project ID. If None, uses Application Default Credentials.
            cache: Enable in-memory caching of secrets (default: True)
            cache_ttl_seconds: Time-to-live for cached secrets in seconds (default: 300)

        Raises:
            ValueError: If project is invalid or cannot be determined from ADC
        """
        if cache:
            self.versions = {}
            self.secrets = {}
            self.cache_timestamps = {}  # Track when each secret was cached
            self.cache_ttl = timedelta(seconds=cache_ttl_seconds)
            logger.debug(f"Cache enabled with TTL: {cache_ttl_seconds}s")
        else:
            self.versions = None
            self.secrets = None
            self.cache_timestamps = None
            self.cache_ttl = None
            logger.debug("Cache disabled")

        self.cache = cache

        if project is not None:
            if not isinstance(project, str) or not project.strip():
                raise ValueError("Project must be a non-empty string")
            self.project = project
        else:
            # Get default project_id from the environment
            logger.debug("No project specified, using Application Default Credentials")
            _, self.project = google.auth.default()
            if not self.project:
                raise ValueError(
                    "No GCP project specified and none found in Application Default Credentials. "
                    "Please provide a project explicitly or configure ADC with: gcloud auth application-default login"
                )

        logger.info(f"Initialized GCPSecrets for project: {self.project}")
        self.client = secretmanager.SecretManagerServiceClient()

    def _validate_secret_name(self, name: str) -> None:
        """
        Validate secret name follows GCP naming rules.

        Args:
            name: Secret name to validate

        Raises:
            ValueError: If secret name is invalid
        """
        if not name:
            raise ValueError("Secret name cannot be empty")

        # GCP secret names can contain letters, numbers, hyphens, and underscores
        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            raise ValueError(
                f"Invalid secret name '{name}'. "
                "Secret names can only contain letters, numbers, hyphens, and underscores."
            )

        if len(name) > 255:
            raise ValueError(f"Secret name too long: {len(name)} characters (max 255)")

        logger.debug(f"Validated secret name: {name}")

    def _validate_version(self, version: str) -> None:
        """
        Validate version is numeric or 'latest'.

        Args:
            version: Version string to validate

        Raises:
            ValueError: If version is invalid
        """
        if version != 'latest' and not version.isdigit():
            raise ValueError(
                f"Invalid version '{version}'. Version must be 'latest' or a numeric string."
            )

        logger.debug(f"Validated version: {version}")

    def _is_cache_valid(self, key: Union[str, tuple]) -> bool:
        """
        Check if cached value is still valid (not expired).

        Args:
            key: Secret key to check

        Returns:
            bool: True if cache is valid and not expired
        """
        if not self.cache or key not in self.cache_timestamps:
            return False

        age = datetime.now() - self.cache_timestamps[key]
        is_valid = age < self.cache_ttl

        if is_valid:
            logger.debug(f"Cache hit for '{key}' (age: {age.total_seconds():.1f}s)")
        else:
            logger.debug(f"Cache expired for '{key}' (age: {age.total_seconds():.1f}s)")

        return is_valid

    def __getitem__(self, key: Union[str, tuple]) -> str:
        """
        Get secret value using dictionary-style access.

        Args:
            key: Secret name (str) or (name, version) tuple

        Returns:
            str: Secret value

        Raises:
            KeyError: If secret not found
            ValueError: If key format is invalid
        """
        if self.cache and key in self.secrets and self._is_cache_valid(key):
            logger.debug(f"Returning cached value for: {key}")
            return self.secrets[key]

        return self.get(key)

    def __contains__(self, key: Union[str, tuple]) -> bool:
        """
        Check if secret exists using 'in' operator.

        Args:
            key: Secret name (str) or (name, version) tuple

        Returns:
            bool: True if secret exists
        """
        return self.contains(key)

    def __setitem__(self, key, value):
        """Setting values is not supported (read-only)."""
        raise NotImplementedError("GCPSecrets is read-only. Use GCP Console or API to create/update secrets.")

    def _check_key_version(self, key: Union[str, tuple]) -> bool:
        """
        Validate key format and return whether it's a simple key or versioned key.

        Args:
            key: Secret key to validate

        Returns:
            bool: True if simple key (str), False if versioned key (tuple)

        Raises:
            ValueError: If key format is invalid
        """
        if isinstance(key, str):
            return True
        elif isinstance(key, tuple) and len(key) == 2:
            return False
        else:
            raise ValueError(KEY_ERROR.format(type(key).__name__, key))

    def _get_address(self, secret: Union[str, tuple]) -> str:
        """
        Get the full GCP resource name for a secret.

        Args:
            secret: Secret name (str) or (name, version) tuple

        Returns:
            str: Full GCP resource name

        Raises:
            KeyError: If secret not found
            ValueError: If secret name or version is invalid
        """
        if isinstance(secret, tuple):
            key = secret[0]
            version = secret[1]
        else:
            key = secret
            version = "latest"

        # Validate inputs
        self._validate_secret_name(key)
        self._validate_version(version)

        # Return results from cache if enabled and valid
        if self.cache and (key, version) in self.versions:
            if self._is_cache_valid((key, version)):
                logger.debug(f"Using cached address for: {key}, version: {version}")
                return self.versions[(key, version)]
            else:
                logger.debug(f"Cache expired for address: {key}, version: {version}")

        # Get and potentially cache all the versions from the secret
        logger.debug(f"Listing versions for secret: {key}")
        request = secretmanager.ListSecretVersionsRequest(
            parent=f"projects/{self.project}/secrets/{key}",
        )

        try:
            page_result = self.client.list_secret_versions(request=request)
        except NotFound as exc:
            logger.warning(f"Secret '{key}' not found in project '{self.project}'")
            raise KeyError(f"Secret '{key}' not found in project '{self.project}'") from exc

        active_versions = [
            (i.name.split("/")[-1], i.name, i.create_time)
            for i in page_result
            if i.state == 1
        ]

        if not active_versions:
            raise ValueError(f"Secret '{key}' has no active versions")

        latest = max(active_versions, key=lambda i: i[2])
        active_versions = {i[0]: (i[1]) for i in active_versions}
        active_versions["latest"] = latest[1]

        logger.debug(f"Found {len(active_versions)} active versions for secret: {key}")

        if self.cache:
            now = datetime.now()
            for ver in active_versions:
                cache_key = (key, ver)
                self.versions[cache_key] = active_versions[ver]
                self.cache_timestamps[cache_key] = now
            self.versions[key] = latest[1]
            self.cache_timestamps[key] = now

        return active_versions[version]

    def get(self, key: Union[str, tuple]) -> str:
        """
        Get secret value.

        Args:
            key: Secret name (str) or (name, version) tuple

        Returns:
            str: Secret value

        Raises:
            KeyError: If secret not found
            ValueError: If key format or secret name is invalid

        Examples:
            >>> secrets = GCPSecrets()
            >>> api_key = secrets.get('API_KEY')
            >>> old_key = secrets.get(('API_KEY', '1'))
        """
        logger.debug(f"Getting secret: {key}")
        self._check_key_version(key)
        address = self._get_address(key)

        logger.debug(f"Accessing secret version at: {address}")
        request = secretmanager.AccessSecretVersionRequest(
            name=address,
        )
        response = self.client.access_secret_version(request=request)

        secret = response.payload.data.decode()
        logger.info(f"Successfully retrieved secret: {key if isinstance(key, str) else key[0]}")

        if self.cache:
            now = datetime.now()
            self.secrets[key] = secret
            self.cache_timestamps[key] = now
            if isinstance(key, str):
                latest_key = (key, "latest")
                self.secrets[latest_key] = secret
                self.cache_timestamps[latest_key] = now
            logger.debug(f"Cached secret: {key}")

        return secret

    def contains(self, key: Union[str, tuple]) -> bool:
        """
        Check existence of key in Secrets Manager.

        Args:
            key: Secret name (str) or (name, version) tuple

        Returns:
            bool: True if secret exists

        Examples:
            >>> secrets = GCPSecrets()
            >>> if 'API_KEY' in secrets:
            ...     api_key = secrets['API_KEY']
        """
        try:
            _ = self._get_address(key)
            return True
        except (KeyError, ValueError):
            return False
