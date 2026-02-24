import pawlabeling_cli as cli


def test_get_version_returns_string():
    version = cli.get_version()
    assert isinstance(version, str)
    assert version
