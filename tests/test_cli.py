"""The public-audit CLI's URL handling: credentials never reach run.json."""

from parity.cli import public_target


def test_public_target_drops_credentials_and_keeps_the_rest():
    assert public_target("https://user:pw@shop.example:8443/a/b?q=1#frag") == ("https://shop.example:8443", "/a/b?q=1", "shop.example:8443")
    assert public_target("http://shop.example") == ("http://shop.example", "/", "shop.example")
    assert public_target("ftp://shop.example/x") is None and public_target("shop.example") is None
