import gcpsecrets


def test_empty():

    secrets = gcpsecrets.GCPSecrets()
    assert secrets.cache is True
    assert secrets.raise_exceptions is True


def test_specific():

    secrets = gcpsecrets.GCPSecrets("gcpsecrets", False, True)

    assert secrets.project == "gcpsecrets"
    assert secrets.cache is False
    assert secrets.raise_exceptions is True
