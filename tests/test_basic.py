"""
Simple library tests for GCPSecrets

These tests verify the basic functionality of the library without
testing implementation details or mock behavior.
"""

import pytest

import gcpsecrets


class TestBasicRetrieval:
    """Test basic secret retrieval functionality"""

    @pytest.mark.parametrize("cache", [True, False])
    def test_get_secret(self, setup_single_secret, cache, mock_google_auth):
        """Test retrieving a secret with and without caching"""
        setup_single_secret()

        secrets = gcpsecrets.GCPSecrets(cache=cache)
        value = secrets["my-secret"]

        assert value == "test_value"

    def test_get_specific_version(self, setup_multi_version_secret):
        """Test retrieving a specific version using tuple key"""
        setup_multi_version_secret("my-secret", [
            ("1", "version_1_value", 1000000),
            ("2", "version_2_value", 2000000),
        ])

        secrets = gcpsecrets.GCPSecrets(project="test-project", cache=False)
        value = secrets[("my-secret", "1")]

        assert value == "version_1_value"


class TestErrorHandling:
    """Test error handling"""

    def test_secret_not_found(self, setup_secret_not_found):
        """Test handling of non-existent secrets"""
        secrets = gcpsecrets.GCPSecrets(project="test-project", cache=False)

        with pytest.raises(KeyError, match="Secret 'nonexistent' not found"):
            _ = secrets["nonexistent"]

    def test_version_not_found(self, setup_single_secret):
        """Test requesting a version that doesn't exist"""
        setup_single_secret()

        secrets = gcpsecrets.GCPSecrets(project="test-project", cache=False)

        with pytest.raises(KeyError):
            _ = secrets[("my-secret", "99")]

    @pytest.mark.parametrize("invalid_key", [
        123,
        ("a", "b", "c"),
    ])
    def test_invalid_key_type(self, mock_secret_client, invalid_key):
        """Test that invalid key types raise ValueError"""
        secrets = gcpsecrets.GCPSecrets(project="test-project", cache=False)

        with pytest.raises(ValueError, match="Key can be either string or tuple"):
            _ = secrets[invalid_key]

    def test_setitem_not_implemented(self, mock_secret_client):
        """Test that setting values raises NotImplementedError"""
        secrets = gcpsecrets.GCPSecrets(project="test-project", cache=False)

        with pytest.raises(NotImplementedError):
            secrets["new-key"] = "value"


class TestContainsMethod:
    """Test the 'in' operator"""

    def test_contains_existing_secret(self, setup_single_secret):
        """Test that 'in' operator works for existing secrets"""
        setup_single_secret("existing-secret")

        secrets = gcpsecrets.GCPSecrets(project="test-project", cache=False)

        assert "existing-secret" in secrets

    def test_contains_non_existing_secret(self, setup_secret_not_found):
        """Test that 'in' operator returns False for non-existent secrets"""
        secrets = gcpsecrets.GCPSecrets(project="test-project", cache=False)

        assert "nonexistent" not in secrets

    def test_contains_specific_version(self, setup_single_secret):
        """Test 'in' operator with specific version tuple"""
        setup_single_secret("versioned")

        secrets = gcpsecrets.GCPSecrets(project="test-project", cache=False)

        assert ("versioned", "1") in secrets
        assert ("versioned", "99") not in secrets


class TestProjectConfiguration:
    """Test project configuration"""

    def test_explicit_project(self, mock_secret_client):
        """Test providing explicit project name"""
        secrets = gcpsecrets.GCPSecrets(project="my-custom-project", cache=False)
        assert secrets.project == "my-custom-project"

    def test_default_project_from_auth(self, mock_secret_client, mock_google_auth):
        """Test getting project from google.auth.default()"""
        mock_google_auth.return_value = (None, "default-project")

        secrets = gcpsecrets.GCPSecrets(cache=False)
        assert secrets.project == "default-project"

    @pytest.mark.parametrize("invalid_project", [
        "",
        "   ",
        123,
    ])
    def test_invalid_project_raises_error(self, mock_secret_client, invalid_project):
        """Test that invalid project values raise ValueError"""
        with pytest.raises(ValueError, match="Project must be a non-empty string"):
            gcpsecrets.GCPSecrets(project=invalid_project, cache=False)
