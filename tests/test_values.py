import pytest

import gcpsecrets


@pytest.fixture(scope="session")
def secret():
    secrets = gcpsecrets.GCPSecrets(cache=True)

    yield secrets


@pytest.mark.parametrize("name", ["gcpsecrets1", "gcpsecrets2"])
def test_existence(secret, name):

    assert name in secret


@pytest.mark.parametrize("name", ["nope", "not_even_close"])
def test_non_existence(secret, name):

    assert name not in secret


@pytest.mark.parametrize(
    "name, value",
    [
        ("gcpsecrets1", "new_one"),
        (("gcpsecrets1", "1"), "old_version"),
        ("gcpsecrets2", "original"),
        (("gcpsecrets2", "1"), "original"),
    ],
    ids=["gcpsecrets1-latest", "gcpsecrets1-1", "gcpsecrets2-latest", "gcpsecrets2-1"],
)
def test_content(secret, name, value):

    assert secret[name] == value

    # Text existence of adress in cache
    assert name in secret.versions
    # Text existence of value in cache
    assert name in secret.secrets
