"""URL policy for pages a visitor chooses (spec §19.3.1, Task 26F.1): every non-public address is refused by code, with one
sentence for the UI and never the URL. Deterministic: the resolver and the robots check are injected."""

from __future__ import annotations

import re

import pytest

from parity.pipeline.urlpolicy import READ_ONLY_GOAL, Refusal, Target, check_url, is_public_ip, resolve_public

OWN = "https://parity-u7lcbbxuia-uc.a.run.app"
PUBLIC_V4, PUBLIC_V6 = "93.184.215.14", "2606:2800:21f:cb07:6820:80da:af6b:8b2c"
TABLE: dict[str, list[str]] = {
    "www.w3.org": [PUBLIC_V4, PUBLIC_V6],
    "example.org": [PUBLIC_V4],
    "loop.example": ["127.0.0.1"],
    "ten.example": ["10.1.2.3"],
    "one72.example": ["172.31.255.1"],
    "one92.example": ["192.168.0.10"],
    "link.example": ["169.254.1.1"],
    "meta.example": ["169.254.169.254"],
    "ula.example": ["fd12:3456::1"],
    "fe80.example": ["fe80::1"],
    "v6loop.example": ["::1"],
    "mcast.example": ["224.0.0.251"],
    "v6mcast.example": ["ff02::1"],
    "unspec.example": ["0.0.0.0"],
    "v6unspec.example": ["::"],
    "mapped.example": ["::ffff:10.0.0.1"],
    "sixtofour.example": ["2002:0a00:0001::1"],
    "cgnat.example": ["100.64.0.1"],
    "mixed.example": [PUBLIC_V4, "10.0.0.7"],
    "parity-u7lcbbxuia-uc.a.run.app": [PUBLIC_V4],
    "denied.example": [PUBLIC_V4],
    "sub.denied.example": [PUBLIC_V4],
}


def resolver(host: str) -> list[str]:
    return TABLE[host]  # KeyError plays NXDOMAIN


def check(url: str, **kw) -> Target | Refusal:
    kw.setdefault("deny", ())
    kw.setdefault("resolver", resolver)
    kw.setdefault("robots", lambda url: True)
    return check_url(url, own_origin=OWN, **kw)


def refused(url: str, **kw) -> Refusal:
    r = check(url, **kw)
    assert isinstance(r, Refusal), f"{url} was accepted: {r}"
    return r


def test_public_host_passes():
    t = check("https://www.w3.org/WAI/demos/bad/before/home.html?x=1#top")
    assert isinstance(t, Target)
    assert t.origin == "https://www.w3.org" and t.host == "www.w3.org"
    assert t.url == "https://www.w3.org/WAI/demos/bad/before/home.html?x=1"  # the fragment never reaches a server
    assert set(t.addresses) == {PUBLIC_V4, PUBLIC_V6}


def test_host_is_lower_cased_and_a_bare_host_gets_a_root_path():
    t = check("HTTPS://WWW.W3.ORG")
    assert isinstance(t, Target) and t.host == "www.w3.org" and t.url == "https://www.w3.org/" and t.origin == "https://www.w3.org"


def test_standard_ports_pass_and_are_kept_out_of_the_origin():
    t = check("http://example.org:80/a")
    assert isinstance(t, Target) and t.origin == "http://example.org" and t.url == "http://example.org/a"
    assert isinstance(check("https://example.org:443/"), Target)


def test_refuses_ftp_scheme():
    assert refused("ftp://www.w3.org/pub/") and refused("file:///etc/passwd") and refused("javascript:alert(1)") and refused("www.w3.org/x")


def test_refuses_port_8080():
    assert refused("http://www.w3.org:8080/") and refused("https://www.w3.org:8443/")


def test_refuses_credentials():
    r = refused("https://alice:s3cret@www.w3.org/")
    assert "s3cret" not in r.message and "alice" not in r.message


def test_refuses_ip_literal():
    assert refused("http://93.184.215.14/") and refused("http://[2606:2800:21f:cb07:6820:80da:af6b:8b2c]/") and refused("http://0x7f000001/")


def test_refuses_loopback():
    assert refused("http://loop.example/") and refused("http://localhost/") and refused("http://app.localhost/")


def test_refuses_10_8():
    assert refused("http://ten.example/")


def test_refuses_172_16_12():
    assert refused("http://one72.example/")


def test_refuses_192_168_16():
    assert refused("http://one92.example/")


def test_refuses_169_254_16():
    assert refused("http://link.example/")


def test_refuses_the_metadata_address():
    assert refused("http://meta.example/latest/meta-data/") and not is_public_ip("169.254.169.254")


def test_refuses_fc00_7():
    assert refused("http://ula.example/")


def test_refuses_fe80_10():
    assert refused("http://fe80.example/")


def test_refuses_ipv6_loopback():
    assert refused("http://v6loop.example/")


def test_refuses_multicast():
    assert refused("http://mcast.example/") and refused("http://v6mcast.example/")
    assert not is_public_ip("224.0.0.1") and not is_public_ip("ff02::1")  # ipaddress calls these "global"; they are not reachable hosts


def test_refuses_unspecified():
    assert refused("http://unspec.example/") and refused("http://v6unspec.example/")


def test_refuses_metadata_google_internal():
    assert refused("http://metadata.google.internal/computeMetadata/v1/", resolver=lambda host: [PUBLIC_V4])  # even if DNS said otherwise


def test_refuses_dot_internal():
    assert refused("http://foo.internal/", resolver=lambda host: [PUBLIC_V4]) and refused("http://a.b.internal/", resolver=lambda host: [PUBLIC_V4])


def test_refuses_own_origin():
    assert refused(f"{OWN}/api/health") and refused("http://parity-u7lcbbxuia-uc.a.run.app/")


def test_refuses_the_deny_list():
    deny = ("denied.example",)
    r = refused("https://denied.example/page", deny=deny)
    assert r.message == "This site asked not to be audited."
    assert refused("https://sub.denied.example/", deny=deny).message == r.message  # subdomains of a denied host too
    assert isinstance(check("https://example.org/", deny=deny), Target)


def test_refuses_a_robots_disallow():
    seen: list[str] = []

    def robots(url: str) -> bool:
        seen.append(url)
        return False

    r = refused("https://www.w3.org/private/x", robots=robots)
    assert r.message == "robots.txt disallows this page." and seen == ["https://www.w3.org/private/x"]


def test_refuses_over_length():
    assert refused("https://www.w3.org/" + "a" * 2048) and isinstance(check("https://www.w3.org/" + "a" * 2000), Target)


def test_refuses_an_unresolvable_host():
    r = refused("https://nxdomain.example/")
    assert "nxdomain" not in r.message


def test_any_private_answer_among_several_refuses():
    assert refused("https://mixed.example/")
    assert isinstance(resolve_public("mixed.example", resolver), Refusal)
    assert resolve_public("www.w3.org", resolver) == [PUBLIC_V4, PUBLIC_V6]


def test_embedded_ipv4_in_an_ipv6_answer_is_judged_too():
    assert refused("https://mapped.example/") and refused("https://sixtofour.example/") and refused("https://cgnat.example/")
    assert not is_public_ip("::ffff:10.0.0.1") and not is_public_ip("2002:0a00:0001::1") and not is_public_ip("100.64.0.1")
    assert is_public_ip(PUBLIC_V4) and is_public_ip(PUBLIC_V6) and not is_public_ip("not an address")


def test_refusal_messages_are_one_sentence_without_the_url():
    cases = [
        ("ftp://www.w3.org/pub/", {}), ("http://www.w3.org:8080/", {}), ("https://user:secret@www.w3.org/", {}), ("http://93.184.215.14/", {}),
        ("http://loop.example/", {}), ("http://meta.example/", {}), ("http://metadata.google.internal/", {}), ("http://foo.internal/", {}),
        (f"{OWN}/", {}), ("https://denied.example/", {"deny": ("denied.example",)}), ("https://www.w3.org/private/", {"robots": lambda u: False}),
        ("https://www.w3.org/" + "a" * 2048, {}), ("https://nxdomain.example/", {}), ("https://mixed.example/", {}),
    ]
    for url, kw in cases:
        r = refused(url, **kw)
        m = r.message
        assert re.fullmatch(r"(?:[A-Z]|robots\.txt)[^.!?]*\.", m), (url, m)  # one sentence to a full stop; the spec's robots.txt line starts lower-case
        assert len(m) <= 80 and "://" not in m and "www.w3.org" not in m and "example" not in m and "run.app" not in m, (url, m)
    assert refused("http://loop.example/").message == "This address is not public."


def test_read_only_goal_tells_the_agent_what_never_to_do():
    assert "submit" in READ_ONLY_GOAL.lower() and "sign in" in READ_ONLY_GOAL.lower() and "buy" in READ_ONLY_GOAL.lower()
