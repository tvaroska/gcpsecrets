"""
Implementation and mock behavior tests for GCPSecrets

These tests verify detailed implementation behavior including caching,
version resolution, edge cases, and mock interactions.
"""

import pytest

import gcpsecrets
from .conftest import create_secret_version, create_secret_payload


class TestCaching:
    """Test caching implementation details"""

    def test_cache_prevents_duplicate_api_calls(self, setup_single_secret, mock_secret_client, mock_google_auth):
        """Test that caching prevents duplicate API calls for the same secret"""
        setup_single_secret("cached-secret", "cached_value")

        secrets = gcpsecrets.GCPSecrets(cache=True)

        # Multiple accesses
        value1 = secrets["cached-secret"]
        value2 = secrets["cached-secret"]
        value3 = secrets["cached-secret"]

        assert value1 == value2 == value3 == "cached_value"

        # Should only call API once due to caching
        assert mock_secret_client.access_secret_version.call_count == 1
        assert mock_secret_client.list_secret_versions.call_count == 1

    def test_no_cache_calls_api_every_time(self, setup_single_secret, mock_secret_client):
        """Test that without caching, API is called every time"""
        setup_single_secret("uncached-secret", "uncached_value")

        secrets = gcpsecrets.GCPSecrets(project="test-project", cache=False)

        # Multiple accesses
        value1 = secrets["uncached-secret"]
        value2 = secrets["uncached-secret"]

        assert value1 == value2 == "uncached_value"

        # Should call API each time
        assert mock_secret_client.access_secret_version.call_count == 2
        assert mock_secret_client.list_secret_versions.call_count == 2

    def test_cache_stores_version_mappings(self, setup_multi_version_secret):
        """Test that cache stores version to resource name mappings"""
        setup_multi_version_secret("versioned-secret", [
            ("1", "value1", 1000000),
            ("2", "value2", 2000000),
        ])

        secrets = gcpsecrets.GCPSecrets(project="test-project", cache=True)

        # Access the secret
        _ = secrets["versioned-secret"]

        # Check that versions cache was populated
        assert ("versioned-secret", "1") in secrets.versions
        assert ("versioned-secret", "2") in secrets.versions
        assert ("versioned-secret", "latest") in secrets.versions
        assert "versioned-secret" in secrets.versions

    def test_cache_stores_versions_separately(self, setup_multi_version_secret):
        """Test that different versions and keys are cached separately"""
        setup_multi_version_secret("multi-version", [
            ("1", "v1_value", 1000000),
            ("2", "v2_value", 2000000),
        ])

        secrets = gcpsecrets.GCPSecrets(project="test-project", cache=True)

        # Access different versions
        latest = secrets["multi-version"]  # Gets v2 (latest by time)
        v1 = secrets[("multi-version", "1")]
        v2 = secrets[("multi-version", "2")]

        # All should be cached separately
        assert secrets.secrets["multi-version"] == "v2_value"
        assert secrets.secrets[("multi-version", "1")] == "v1_value"
        assert secrets.secrets[("multi-version", "2")] == "v2_value"

    def test_cache_isolation_between_instances(self, setup_single_secret):
        """Test that cache is isolated between different GCPSecrets instances"""
        setup_single_secret("isolated-secret", "value")

        # Create two separate instances with caching
        secrets1 = gcpsecrets.GCPSecrets(project="test-project", cache=True)
        secrets2 = gcpsecrets.GCPSecrets(project="test-project", cache=True)

        # Access in first instance
        _ = secrets1["isolated-secret"]

        # Second instance should have its own cache
        assert "isolated-secret" in secrets1.secrets
        assert "isolated-secret" not in secrets2.secrets


class TestVersionResolution:
    """Test version resolution implementation details"""

    def test_latest_is_newest_by_create_time(self, setup_multi_version_secret, mock_secret_client):
        """Test that 'latest' version is determined by create_time, not version number"""
        # Version 3 was created first, version 1 was created last (out of order)
        setup_multi_version_secret("time-test", [
            ("3", "oldest", 1000000),
            ("2", "middle", 2000000),
            ("1", "newest_value", 3000000),  # Latest by time
        ])

        secrets = gcpsecrets.GCPSecrets(project="test-project", cache=True)
        value = secrets["time-test"]

        # Should get version 1 because it has the latest create_time
        call_args = mock_secret_client.access_secret_version.call_args
        assert "versions/1" in call_args.kwargs['request'].name

    def test_only_enabled_versions_considered(self, mock_secret_client):
        """Test that disabled versions are not considered for 'latest'"""
        mock_secret_client.list_secret_versions.return_value = [
            create_secret_version("state-test", "1", state=1, create_time_seconds=1000000),
            create_secret_version("state-test", "2", state=2, create_time_seconds=2000000),  # Disabled
            create_secret_version("state-test", "3", state=0, create_time_seconds=3000000),  # Destroyed
        ]
        mock_secret_client.access_secret_version.return_value = create_secret_payload("enabled_value")

        secrets = gcpsecrets.GCPSecrets(project="test-project", cache=True)
        value = secrets["state-test"]

        # Should get version 1 because it's the only enabled version
        call_args = mock_secret_client.access_secret_version.call_args
        assert "versions/1" in call_args.kwargs['request'].name


class TestRealWorldScenarios:
    """Test scenarios that match real-world usage patterns"""

    def test_multiple_secrets_multiple_versions(self, setup_multiple_secrets):
        """Test accessing multiple different secrets with various versions"""
        setup_multiple_secrets({
            "api-key": [
                ("1", "api_key_v1", 1000000),
                ("2", "api_key_v2", 2000000),
            ],
            "db-password": [
                ("1", "db_pass", 1500000),
            ],
        })

        secrets = gcpsecrets.GCPSecrets(project="test-project", cache=True)

        # Access different secrets
        api_key_latest = secrets["api-key"]
        api_key_v1 = secrets[("api-key", "1")]
        db_password = secrets["db-password"]

        assert api_key_latest == "api_key_v2"
        assert api_key_v1 == "api_key_v1"
        assert db_password == "db_pass"


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.mark.parametrize("secret_name,secret_value", [
        ("empty-secret", ""),
        ("whitespace-secret", "   \n\t  "),
        ("numeric-secret", "12345"),
        ("special-chars", "my-secret_v2"),
    ])
    def test_simple_edge_case_values(self, setup_single_secret, secret_name, secret_value):
        """Test various edge case secret values"""
        setup_single_secret(secret_name, secret_value)

        secrets = gcpsecrets.GCPSecrets(project="test-project", cache=False)
        value = secrets[secret_name]

        assert value == secret_value
        assert isinstance(value, str)

    def test_very_large_secret(self, setup_single_secret):
        """Test secret near 64KB limit (GCP limit is 65536 bytes)"""
        large_value = "x" * 60000
        setup_single_secret("large-secret", large_value)

        secrets = gcpsecrets.GCPSecrets(project="test-project", cache=False)
        value = secrets["large-secret"]

        assert len(value) == 60000
        assert value == large_value

    def test_no_active_versions(self, setup_disabled_versions):
        """Test secret with all disabled versions raises error"""
        setup_disabled_versions()

        secrets = gcpsecrets.GCPSecrets(project="test-project", cache=False)

        with pytest.raises(ValueError):
            _ = secrets["disabled-secret"]

    def test_multiline_secret_value(self, setup_single_secret):
        """Test secret containing multiple lines"""
        multiline_value = "line1\nline2\nline3\nline4"
        setup_single_secret("multiline-secret", multiline_value)

        secrets = gcpsecrets.GCPSecrets(project="test-project", cache=False)
        value = secrets["multiline-secret"]

        assert value == multiline_value
        assert value.count('\n') == 3

    def test_json_secret_value(self, setup_single_secret):
        """Test secret containing JSON data"""
        json_value = '{"api_key": "abc123", "endpoint": "https://api.example.com"}'
        setup_single_secret("json-secret", json_value)

        secrets = gcpsecrets.GCPSecrets(project="test-project", cache=False)
        value = secrets["json-secret"]

        assert value == json_value
        # Verify it's a valid JSON string
        import json
        parsed = json.loads(value)
        assert parsed["api_key"] == "abc123"

    def test_utf8_encoded_secret(self, mock_secret_client):
        """Test handling UTF-8 encoded secret data"""
        mock_secret_client.list_secret_versions.return_value = [
            create_secret_version("utf8-secret", "1", create_time_seconds=1000000),
        ]
        utf8_data = "Hello 世界! 🔑".encode('utf-8')
        mock_secret_client.access_secret_version.return_value = create_secret_payload(utf8_data)

        secrets = gcpsecrets.GCPSecrets(project="test-project", cache=False)
        value = secrets["utf8-secret"]

        assert value == "Hello 世界! 🔑"
        assert isinstance(value, str)
