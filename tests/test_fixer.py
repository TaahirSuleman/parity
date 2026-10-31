"""Fixer: the model proposes a patched element; code validates it, applies it once and computes the diff."""

import json
import re
from pathlib import Path

import pytest

from parity.meta.fake import FakeMetaClient
from parity.pipeline.fixer import FixNotApplied, FixRejected, apply_fix, propose_fix, unified_diff
from parity.store.models import Element
from tests.test_runner import META, stage_defaults

BEFORE = '<button id="f5" class="btn" aria-label="Submit"><img alt="" src="x.svg"></button>'
AFTER = '<button id="f5" class="btn">Pay R1,249</button>'
MODEL = "muse-spark-1.3-contributor"


def element(outer_html: str = BEFORE) -> Element:
    return Element(backend_id=1, css_path="#f5", outer_html=outer_html, dom_id="f5")


def response_with(payload) -> dict:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return {"id": "resp_fix", "_request_id": "req-fix", "status": "completed",
            "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}], "usage": {"input_tokens": 10, "output_tokens": 5}}


def test_apply_fix_replaces_once():
    page = f"<main><p>a</p>{BEFORE}<p>b</p></main>"
    assert apply_fix(page, element(), AFTER) == f"<main><p>a</p>{AFTER}<p>b</p></main>"


def test_apply_fix_raises_when_absent():
    with pytest.raises(FixNotApplied):
        apply_fix("<main><p>nothing here</p></main>", element(), AFTER)
    with pytest.raises(FixNotApplied):  # twice is as bad as never: the patch would be ambiguous
        apply_fix(f"<main>{BEFORE}{BEFORE}</main>", element(), AFTER)


def test_patch_path_is_repo_relative():
    from parity.pipeline.fixer import patch_path

    assert patch_path("http://127.0.0.1:8080/store/checkout.html") == "store/checkout.html"
    assert patch_path("file:///Users/me/parity/store/checkout.html") == "store/checkout.html"  # recorded captures
    assert patch_path("https://example.com/shop/cart") == "shop/cart" and patch_path("https://example.com/") == "index.html"


def test_unified_diff_is_a_git_style_patch():
    diff = unified_diff(f"<main>\n{BEFORE}\n</main>\n", f"<main>\n{AFTER}\n</main>\n", "store/checkout.html")
    assert diff.startswith("--- a/store/checkout.html\n+++ b/store/checkout.html\n")
    assert f"-{BEFORE}" in diff and f"+{AFTER}" in diff


async def test_fix_hero_removes_aria_label_or_sets_matching_name(hero, page, store_url):
    """Recorded Spark answer on the hero: the patched button's accessible name is the visible price."""
    cap, finding = hero
    await page.goto(store_url + "checkout.html")
    cap.html = await page.content()
    fake = FakeMetaClient(META, stage_defaults=stage_defaults())
    fix = await propose_fix(fake, finding, cap, run_id="r1", model=MODEL)
    assert fix.before_html == finding.element.outer_html and fix.after_html != fix.before_html
    assert fix.diff.startswith("--- a/store/checkout.html\n+++ b/store/checkout.html\n")
    assert re.search(r'^-\s*<button id="f5" class="btn" aria-label="Submit"', fix.diff, re.M) and re.search(r"^\+.*Pay R1,249", fix.diff, re.M)
    assert fix.model_meta["model"] == MODEL and fix.model_meta["request_id"]
    body = fake.calls[-1]
    assert body["text"] == {"format": {"type": "json_object"}} and "Pay R1,249" in body["input"][0]["content"][0]["text"]
    await page.set_content(apply_fix(cap.html, finding.element, fix.after_html))
    assert await page.get_by_role("button", name=re.compile(r"Pay R1,249")).count() == 1


async def test_fix_rejected_when_tag_changes(hero, tmp_path):
    cap, finding = hero
    fake = FakeMetaClient(tmp_path, default=response_with({"after_html": '<a id="f5" href="#">Pay R1,249</a>', "explanation": "link"}))
    with pytest.raises(FixRejected):
        await propose_fix(fake, finding, cap, run_id="r1", model=MODEL)


async def test_fix_rejected_when_id_changes(hero, tmp_path):
    """A snippet for a different element (another id) must never be spliced in: the fix targets one element."""
    cap, finding = hero
    fake = FakeMetaClient(tmp_path, default=response_with({"after_html": '<button id="f6" class="btn">Pay R1,249</button>', "explanation": ""}))
    with pytest.raises(FixRejected):
        await propose_fix(fake, finding, cap, run_id="r1", model=MODEL)


async def test_fix_rejected_when_snippet_adds_script_or_is_unparseable(hero, tmp_path):
    cap, finding = hero
    for answer in ('<button id="f5" onclick="x()">Pay</button>', '<button id="f5">Pay<script>1</script></button>'):
        fake = FakeMetaClient(tmp_path, default=response_with({"after_html": answer, "explanation": ""}))
        with pytest.raises(FixRejected):
            await propose_fix(fake, finding, cap, run_id="r1", model=MODEL)
    fake = FakeMetaClient(tmp_path, default=response_with("not json at all"))
    with pytest.raises(FixRejected):
        await propose_fix(fake, finding, cap, run_id="r1", model=MODEL)


# --- review fix pass: the patch applies to the file it names; snippets are parsed, not grepped ---
ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "store" / "checkout.html").read_text()
F5 = Element(backend_id=1, css_path="#f5", dom_id="f5")
F6_AFTER = '<button id="f6" class="icon" aria-label="Delete">🗑️</button>'


def git_apply_check(tmp_path, diff: str, rel: str = "store/checkout.html", source: str = SOURCE) -> None:
    import subprocess

    target = tmp_path / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source)
    (tmp_path / "fix.patch").write_text(diff)
    res = subprocess.run(["git", "apply", "--check", "fix.patch"], cwd=tmp_path, capture_output=True, text=True)
    assert res.returncode == 0, res.stderr


def test_locate_in_source_finds_the_element_by_id():
    from parity.pipeline.fixer import locate_in_source

    start, end = locate_in_source(SOURCE, F5)
    assert SOURCE[start:end].startswith('<button id="f5" class="btn" aria-label="Submit">') and SOURCE[start:end].endswith("</button>")
    s, e = locate_in_source(SOURCE, Element(backend_id=2, css_path="#f1", dom_id="f1"))  # a void element is its start tag
    assert SOURCE[s:e].startswith('<img id="f1"') and SOURCE[s:e].endswith('">') and SOURCE[s:e].count("<img") == 1 and "<button" not in SOURCE[s:e]
    nested = '<main><div id="a"><div>inner</div></div><p>tail</p></main>'
    s, e = locate_in_source(nested, Element(backend_id=3, css_path="#a", dom_id="a"))
    assert nested[s:e] == '<div id="a"><div>inner</div></div>'
    assert locate_in_source(SOURCE, Element(backend_id=4, css_path="x", dom_id="nope")) is None
    assert locate_in_source('<p id="d">1</p><p id="d">2</p>', Element(backend_id=5, css_path="#d", dom_id="d")) is None  # ambiguous


def test_apply_fix_splices_into_the_served_source_by_id():
    """The DOM serialisation (&lt;svg in the attribute) never matches the source text; the id does."""
    dom = Element(backend_id=1, css_path="#f5", dom_id="f5", outer_html='<button id="f5" class="btn" aria-label="Submit"><img alt="" src="data:image/svg+xml;utf8,&lt;svg&gt;"></button>')
    out = apply_fix(SOURCE, dom, AFTER)
    assert AFTER in out and 'aria-label="Submit"><img' not in out and out.count("<button") == SOURCE.count("<button")


def test_patch_applies_with_git(tmp_path):
    """The exported patch must apply to the repo file it names: `git apply --check` is the judge."""
    git_apply_check(tmp_path, unified_diff(SOURCE, apply_fix(SOURCE, F5, AFTER), "store/checkout.html"))


def test_combined_patch_for_adjacent_fixes_applies(tmp_path):
    """Two approved fixes on adjacent lines (f5, f6) must come out as one diff against one base."""
    from parity.pipeline.fixer import combine_patch

    diff = combine_patch(SOURCE, [(F5, AFTER), (Element(backend_id=2, css_path="#f6", dom_id="f6"), F6_AFTER)], "store/checkout.html")
    assert "Pay R1,249" in diff and 'aria-label="Delete"' in diff and diff.count("+++ b/") == 1
    git_apply_check(tmp_path, diff)


def test_unified_diff_keeps_no_newline_at_eof(tmp_path):
    src = "<p id='a'>a</p>\n<p>b</p>"  # no trailing newline, like many real files
    diff = unified_diff(src, src.replace("<p>b</p>", "<p>c</p>"), "x.html")
    assert "\\ No newline at end of file" in diff
    git_apply_check(tmp_path, diff, "x.html", src)


BAD_SNIPPETS = [
    '<button id="f5"><img src="x"onerror=alert(1)></button>',
    '<button id="f5"><svg/onload=alert(1)></svg></button>',
    '<button id="f5"><a href="java&#115;cript:alert(1)">x</a></button>',
    '<button id="f5"><a href="java\tscript:alert(1)">x</a></button>',
    '<button id="f5"><iframe srcdoc="&lt;script&gt;alert(1)&lt;/script&gt;"></iframe></button>',
    '<button id="f5"><object data="data:text/html,x"></object></button>',
    '<button id="f5" formaction="javascript&colon;alert(1)">x</button>',
    '<button id="f5"><meta http-equiv="refresh" content="0;url=https://evil"></button>',
    '<button id="f5"><base href="https://evil/"></button>',
    '<button id="f5"><style>body{display:none}</style>x</button>',
    '<button id="f5"><link rel="stylesheet" href="https://evil/x.css">x</button>',
    '<button id="f5">x</button><img src="x">',
    'text <button id="f5">x</button>',
    '<button id="f5">x',
    '<button id="f5"><span id="f5">x</span></button>',
]


@pytest.mark.parametrize("snippet", BAD_SNIPPETS)
def test_validator_rejects_smuggled_behaviour(snippet):
    from parity.pipeline.fixer import validate_snippet

    with pytest.raises(FixRejected):
        validate_snippet(BEFORE, snippet)


def test_validator_accepts_real_fixes_and_kept_handlers():
    from parity.pipeline.fixer import validate_snippet

    validate_snippet(BEFORE, AFTER)
    validate_snippet(BEFORE, '<button id="f5" class="btn"><img alt="Pay R1,249" width="118" height="20" src="data:image/svg+xml;utf8,<svg xmlns=\'http://www.w3.org/2000/svg\'><text>Pay</text></svg>"></button>')
    before = '<button id="x" onclick="go()" aria-label="Submit">a</button>'
    validate_snippet(before, '<button id="x" onclick="go()">Pay R1,249</button>')  # an existing handler, unchanged, is fine
    with pytest.raises(FixRejected):
        validate_snippet(before, '<button id="x" onclick="steal()">Pay R1,249</button>')


async def test_fix_refused_when_the_element_source_is_too_large(hero, tmp_path):
    from parity.pipeline.fixer import MAX_FIX_HTML

    cap, finding = hero
    cap.html = SOURCE.replace('<button id="f5" class="btn" aria-label="Submit">', '<button id="f5" class="btn" aria-label="Submit" data-x="' + "y" * MAX_FIX_HTML + '">')
    fake = FakeMetaClient(tmp_path, default=response_with({"after_html": AFTER, "explanation": ""}))
    with pytest.raises(FixRejected):
        await propose_fix(fake, finding, cap, run_id="r1", model=MODEL)
    assert not fake.calls  # refused before spending a model call
