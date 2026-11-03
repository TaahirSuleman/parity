"""URL policy for pages a visitor chooses (spec §19.3.1): code decides what is public; a model never sees a non-public address.

``check_url`` is the one door: scheme, port, credentials, length and the host's shape are checked first (free), then the
name is resolved and every answer judged, then robots.txt. A ``Refusal`` is one sentence for the UI and never carries the
URL, so nothing a visitor typed is echoed back. The same ``resolve_public`` is what the browser's request guard uses for
every request an external run makes (Task 26F.2), redirects included.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlsplit

MAX_URL_LEN = 2048
STANDARD_PORTS = {"http": 80, "https": 443}
METADATA_HOST = "metadata.google.internal"
METADATA_IP = "169.254.169.254"
LOCAL_NAMES = ("localhost", ".localhost", ".internal", ".local")  # a bare name, or a suffix with its dot
READ_ONLY_GOAL = ("Read this page as a visitor would: what it is about, what it offers and where it leads. "
                  "Do not follow links, do not fill in or submit anything, do not sign in, and do not buy or order anything.")

Resolver = Callable[[str], list[str]]  # host -> every A and AAAA answer; raises when the name does not resolve


@dataclass(frozen=True)
class Target:
    url: str  # the address to open: no credentials, no fragment, a lower-case host, a path
    origin: str  # scheme://host, the standard port left out
    host: str
    addresses: tuple[str, ...]  # what the name resolved to when it was checked


@dataclass(frozen=True)
class Refusal:
    message: str  # one sentence for the UI; never the URL


NOT_PUBLIC = Refusal("This address is not public.")
NOT_WEB = Refusal("Only http and https addresses are accepted.")
NO_HOST = Refusal("This address has no host name.")
BAD_PORT = Refusal("Only the standard web ports are accepted.")
CREDENTIALS = Refusal("Addresses with a username or password are not accepted.")
TOO_LONG = Refusal("This address is too long.")
UNRESOLVED = Refusal("This host name could not be resolved.")
OWN = Refusal("Parity does not audit its own address.")
DENIED = Refusal("This site asked not to be audited.")
ROBOTS = Refusal("robots.txt disallows this page.")


def is_public_ip(ip: str) -> bool:
    """A globally routable unicast address. Multicast is 'global' to ipaddress but no host; an IPv6 answer that embeds an
    IPv4 (mapped, 6to4, Teredo) is judged by that address as well; the cloud metadata address is never public."""
    try:
        addr = ipaddress.ip_address(ip.strip())
    except ValueError:
        return False
    embedded = [a for a in (getattr(addr, "ipv4_mapped", None), getattr(addr, "sixtofour", None), *(getattr(addr, "teredo", None) or ())) if a is not None]
    return all(_routable(a) for a in (addr, *embedded))


def _routable(addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if str(addr) == METADATA_IP:
        return False
    if addr.is_multicast or addr.is_loopback or addr.is_link_local or addr.is_private or addr.is_unspecified or addr.is_reserved or getattr(addr, "is_site_local", False):
        return False
    return addr.is_global


def _local_name(host: str) -> bool:
    return host == METADATA_HOST or any(host == n or host.endswith(n) for n in LOCAL_NAMES)


def system_resolver(host: str) -> list[str]:
    """Every A and AAAA answer the system resolver gives (blocking; callers on the loop run it in a thread)."""
    infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    return sorted({info[4][0] for info in infos})


def resolve_public(host: str, resolver: Resolver | None = None) -> list[str] | Refusal:
    """The host's addresses, or a Refusal when the name is local by construction, does not resolve, or any answer is not public."""
    host = host.strip().lower().rstrip(".")
    if not host or _local_name(host):
        return NOT_PUBLIC
    try:
        addresses = (resolver or system_resolver)(host)
    except Exception:
        return UNRESOLVED
    if not addresses:
        return UNRESOLVED
    if not all(is_public_ip(a) for a in addresses):
        return NOT_PUBLIC
    return list(addresses)


def check_url(url: str, *, own_origin: str, deny: tuple[str, ...] | list[str] = (), resolver: Resolver | None = None,
              robots: Callable[[str], bool] | None = None) -> Target | Refusal:
    """The whole policy for a visitor's URL, cheapest check first. ``robots`` defaults to the guard's robots_allows."""
    if len(url) > MAX_URL_LEN:
        return TOO_LONG
    parts = urlsplit(url.strip())
    if parts.scheme.lower() not in STANDARD_PORTS:
        return NOT_WEB
    scheme = parts.scheme.lower()
    if parts.username is not None or parts.password is not None:
        return CREDENTIALS
    try:
        host, port = parts.hostname, parts.port  # .port raises on a non-numeric or out-of-range port
    except ValueError:
        return BAD_PORT
    host = fold_host(host or "")
    if not host:
        return NO_HOST
    if port not in (None, STANDARD_PORTS[scheme]):
        return BAD_PORT
    if _ip_literal(host):
        return NOT_PUBLIC
    own = urlsplit(own_origin).hostname
    if own and host == own.lower():
        return OWN
    for entry in deny:
        entry = entry.strip().lower().rstrip(".")
        if entry and (host == entry or host.endswith("." + entry)):
            return DENIED
    resolved = resolve_public(host, resolver)
    if isinstance(resolved, Refusal):
        return resolved
    origin = f"{scheme}://{host}"
    clean = origin + (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
    if not (robots or _robots_allows)(clean):
        return ROBOTS
    return Target(url=clean, origin=origin, host=host, addresses=tuple(resolved))


def fold_host(host: str) -> str:
    """The one spelling of a host name every resolver and browser sees: lower-case, no trailing dot, IDNA-folded ("ｅxample.com" is
    example.com). An empty string when the name cannot be folded (review I2)."""
    host = host.strip().lower().rstrip(".")
    if not host:
        return ""
    try:
        return host.encode("idna").decode("ascii")
    except UnicodeError:
        return ""


def landing_refusal(url: str, *, deny: tuple[str, ...] | list[str] = (), robots: Callable[[str], bool] | None = None) -> str | None:
    """The policy that applies again where the start address landed (after its redirects): the deny list and robots.txt (review I1).
    Public-ness was judged by the browser's guard hop by hop; this is the opt-out promise. None when the landing may be audited."""
    host = fold_host(urlsplit(url).hostname or "")
    if not host:
        return NO_HOST.message
    for entry in deny:
        entry = fold_host(entry)
        if entry and (host == entry or host.endswith("." + entry)):
            return DENIED.message
    if not (robots or _robots_allows)(url):
        return ROBOTS.message
    return None


def _ip_literal(host: str) -> bool:
    """An IPv4 or IPv6 literal, including the spellings a browser accepts and ipaddress does not (0x7f000001, 2130706433, 127.1)."""
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        pass
    # every dotted part a decimal or hex number: 127.1, 2130706433, 0x7f.1, 0177.0.0.1; a name with a letter outside such a part
    # ("1a2b.cafe", "1.bad.cafe") is a name and goes to the resolver, which judges the addresses it answers
    return bool(host) and all(re.fullmatch(r"0x[0-9a-f]*|[0-9]+", part, re.IGNORECASE) for part in host.split("."))


def _robots_allows(url: str) -> bool:
    from parity.pipeline.guard import robots_allows

    return robots_allows(url)
