"""
Pytest configuration and shared fixtures for gcpsecrets tests.

This module contains:
- Mock fixtures for GCP Secret Manager client
- Helper functions for creating test data
- Common test utilities
"""

import pytest
from unittest.mock import Mock, patch
from google.protobuf.timestamp_pb2 import Timestamp


@pytest.fixture
def mock_secret_client():
    """
    Mock the SecretManagerServiceClient to avoid real GCP API calls.

    This fixture patches the client at the module level and yields the mocked instance.
    All tests using this fixture will use the mocked client instead of making real API calls.
    """
    with patch('gcpsecrets.secretmanager.SecretManagerServiceClient') as mock_client_class:
        yield mock_client_class.return_value


@pytest.fixture
def mock_google_auth():
    """
    Mock google.auth.default() to return a test project.

    This fixture is useful for testing project configuration when no explicit
    project is provided to GCPSecrets.
    """
    with patch('gcpsecrets.google.auth.default') as mock_auth:
        mock_auth.return_value = (None, "test-project")
        yield mock_auth


def create_secret_version(name, version, state=1, create_time_seconds=1000000):
    """
    Helper function to create a mock secret version response.

    Args:
        name: Secret name (e.g., "my-secret")
        version: Version number (e.g., "1", "2")
        state: State of the version (1 = ENABLED, 2 = DISABLED, etc.)
        create_time_seconds: Unix timestamp in seconds

    Returns:
        Mock object representing a SecretVersion resource

    Example:
        >>> version = create_secret_version("api-key", "1", create_time_seconds=1000000)
        >>> version.name
        'projects/test-project/secrets/api-key/versions/1'
        >>> version.state
        1
    """
    mock_version = Mock()
    mock_version.name = f"projects/test-project/secrets/{name}/versions/{version}"
    mock_version.state = state  # 1 = ENABLED

    # Create a mock timestamp that supports comparison
    mock_timestamp = Mock(spec=Timestamp)
    mock_timestamp.seconds = create_time_seconds
    # Make it comparable for max() function
    mock_timestamp.__lt__ = lambda self, other: self.seconds < other.seconds
    mock_timestamp.__gt__ = lambda self, other: self.seconds > other.seconds
    mock_timestamp.__le__ = lambda self, other: self.seconds <= other.seconds
    mock_timestamp.__ge__ = lambda self, other: self.seconds >= other.seconds
    mock_timestamp.__eq__ = lambda self, other: self.seconds == other.seconds

    mock_version.create_time = mock_timestamp
    return mock_version


def create_secret_payload(data):
    """
    Helper function to create a mock AccessSecretVersionResponse.

    Args:
        data: Secret value as string or bytes

    Returns:
        Mock object representing an AccessSecretVersionResponse

    Example:
        >>> response = create_secret_payload("my-secret-value")
        >>> response.payload.data
        b'my-secret-value'
    """
    mock_response = Mock()
    mock_response.payload.data = data.encode() if isinstance(data, str) else data
    return mock_response


@pytest.fixture
def gcpsecrets_factory(mock_secret_client, mock_google_auth):
    """
    Factory fixture for creating GCPSecrets instances with different configurations.

    This fixture simplifies test setup when you need to create multiple GCPSecrets
    instances with different settings.

    Args:
        project: Optional project name (default: "test-project")
        cache: Optional cache setting (default: True)

    Returns:
        Function that creates GCPSecrets instances

    Example:
        >>> def test_something(gcpsecrets_factory):
        ...     secrets = gcpsecrets_factory(project="my-project", cache=False)
        ...     assert secrets.project == "my-project"
    """
    import gcpsecrets

    def _create(project="test-project", cache=True):
        return gcpsecrets.GCPSecrets(project=project, cache=cache)

    return _create


@pytest.fixture
def secret_scenarios():
    """
    Common test scenarios for different types of secret values.

    Returns:
        List of tuples (secret_name, secret_value) representing various test cases

    Example:
        >>> def test_all_scenarios(secret_scenarios, mock_secret_client):
        ...     for name, value in secret_scenarios:
        ...         # Setup mock and test
    """
    return [
        ("simple-secret", "simple_value"),
        ("utf8-secret", "Hello 世界! 🔑"),
        ("json-secret", '{"key": "value"}'),
        ("multiline-secret", "line1\nline2\nline3"),
        ("empty-secret", ""),
        ("numeric-secret", "12345"),
        ("whitespace-secret", "   \n\t  "),
    ]


@pytest.fixture
def multi_version_setup(mock_secret_client):
    """
    Setup fixture for tests requiring multiple versions of secrets.

    This fixture configures the mock client to return multiple versions
    and provides helper methods for common multi-version test scenarios.

    Returns:
        Dictionary with helper functions and configuration

    Example:
        >>> def test_versions(multi_version_setup):
        ...     setup = multi_version_setup
        ...     # Mock client is already configured with versions
    """
    def setup_versions(secret_name, versions_data):
        """
        Setup multiple versions for a secret.

        Args:
            secret_name: Name of the secret
            versions_data: List of tuples (version, value, create_time_seconds, state)
        """
        mock_versions = []
        for version, _, create_time, state in versions_data:
            mock_versions.append(
                create_secret_version(secret_name, version, state=state, create_time_seconds=create_time)
            )
        mock_secret_client.list_secret_versions.return_value = mock_versions

        def access_side_effect(request):
            for version, value, _, _ in versions_data:
                if f"versions/{version}" in request.name:
                    return create_secret_payload(value)
            return create_secret_payload("unknown")

        mock_secret_client.access_secret_version.side_effect = access_side_effect

    return {
        "client": mock_secret_client,
        "setup_versions": setup_versions,
    }


# Parameterized Mock Setup Fixtures

@pytest.fixture
def setup_single_secret(mock_secret_client):
    """Setup a single secret with one version"""
    def _setup(secret_name="my-secret", value="test_value", version="1", create_time=1000000):
        mock_secret_client.list_secret_versions.return_value = [
            create_secret_version(secret_name, version, create_time_seconds=create_time),
        ]
        mock_secret_client.access_secret_version.return_value = create_secret_payload(value)
    return _setup


@pytest.fixture
def setup_multi_version_secret(mock_secret_client):
    """Setup a secret with multiple versions"""
    def _setup(secret_name, versions):
        """
        Args:
            secret_name: Name of the secret
            versions: List of tuples (version, value, create_time_seconds)
        """
        mock_versions = [
            create_secret_version(secret_name, ver, create_time_seconds=time)
            for ver, _, time in versions
        ]
        mock_secret_client.list_secret_versions.return_value = mock_versions

        def access_side_effect(request):
            # Match exact version number by checking for end of string or '/' after version
            for ver, val, _ in versions:
                # Build exact pattern: ends with /versions/{ver}
                if request.name.endswith(f"/versions/{ver}"):
                    return create_secret_payload(val)
            return create_secret_payload("unknown")

        mock_secret_client.access_secret_version.side_effect = access_side_effect
    return _setup


@pytest.fixture
def setup_secret_not_found(mock_secret_client):
    """Setup mock to simulate secret not found"""
    from google.api_core.exceptions import NotFound
    mock_secret_client.list_secret_versions.side_effect = NotFound("Secret not found")


@pytest.fixture
def setup_disabled_versions(mock_secret_client):
    """Setup a secret with all disabled versions"""
    def _setup(secret_name="disabled-secret"):
        mock_secret_client.list_secret_versions.return_value = [
            create_secret_version(secret_name, "1", state=2, create_time_seconds=1000000),  # Disabled
            create_secret_version(secret_name, "2", state=0, create_time_seconds=2000000),  # Destroyed
        ]
    return _setup


@pytest.fixture
def setup_multiple_secrets(mock_secret_client):
    """Setup multiple different secrets"""
    def _setup(secrets_config):
        """
        Args:
            secrets_config: Dict mapping secret names to list of (version, value, create_time) tuples
        """
        def list_versions_side_effect(request):
            for secret_name, versions in secrets_config.items():
                if secret_name in request.parent:
                    return [
                        create_secret_version(secret_name, ver, create_time_seconds=time)
                        for ver, _, time in versions
                    ]
            return []

        def access_version_side_effect(request):
            for secret_name, versions in secrets_config.items():
                if secret_name in request.name:
                    for ver, val, _ in versions:
                        if request.name.endswith(f"/versions/{ver}"):
                            return create_secret_payload(val)
            return create_secret_payload("unknown")

        mock_secret_client.list_secret_versions.side_effect = list_versions_side_effect
        mock_secret_client.access_secret_version.side_effect = access_version_side_effect
    return _setup
