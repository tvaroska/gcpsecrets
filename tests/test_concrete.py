import pytest

import gcpsecrets


def test_empty():

    secrets = gcpsecrets.GCPSecrets()
    assert secrets.cache is True


def test_specific():

    secrets = gcpsecrets.GCPSecrets("gcpsecrets", False)

    assert secrets.project == "gcpsecrets"
    assert secrets.cache is False


def test_empty_project_string():

    with pytest.raises(ValueError, match="Project must be a non-empty string"):
        gcpsecrets.GCPSecrets(project="")


def test_whitespace_project_string():

    with pytest.raises(ValueError, match="Project must be a non-empty string"):
        gcpsecrets.GCPSecrets(project="   ")


def test_non_string_project():

    with pytest.raises(ValueError, match="Project must be a non-empty string"):
        gcpsecrets.GCPSecrets(project=123)
