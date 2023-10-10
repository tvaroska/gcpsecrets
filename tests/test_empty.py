import pytest

import gcpsecrets


@pytest.fixture
def secrets():
    return gcpsecrets.GCPSecrets()


@pytest.mark.parametrize("name", ["nokey"])
def test_key(secrets, name):

    with pytest.raises(KeyError):
        assert secrets[name] == "Nope"


def test_wrong_keys(secrets):

    with pytest.raises(
        ValueError,
        match="Key can be either string or tuple with 2 strings. Got int with value 1",
    ):
        assert secrets[1] == "test"
