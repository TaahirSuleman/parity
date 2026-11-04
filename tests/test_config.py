from parity.config import load_settings


def test_settings_defaults_replay():
    s = load_settings(env={})
    assert s.default_mode == "replay"
    assert s.live_per_ip_per_hour == 3


def test_model_for_defaults_contributor():
    """The judge too, since the 4 Nov sweep (eval/results/model-sweep.md): the contributor tier at high effort matched the
    standard tier's 94% agreement with 0% needing review at $0.0006 a finding against $0.0108. The fallback stays standard."""
    s = load_settings(env={})
    assert s.model_for("comparator") == "muse-spark-1.3-contributor"
    assert s.model_for("judge") == "muse-spark-1.3-contributor"
    assert s.model_for("judge_fallback") == "muse-spark-1.3"
    assert s.effort_for("judge") == "high"


def test_private_mode_uses_standard_spark():
    s = load_settings(env={"PARITY_PRIVATE": "true"})
    assert s.model_for("comparator") == "muse-spark-1.3"
    assert s.model_for("navigator") == "muse-spark-1.3"


def test_settings_never_exposes_key():
    s = load_settings(env={"MODEL_API_KEY": "sk-very-secret-value"})
    assert s.model_api_key == "sk-very-secret-value"
    assert "sk-very-secret-value" not in repr(s)
    assert "sk-very-secret-value" not in str(s)


def test_env_overrides_defaults():
    s = load_settings(env={"PARITY_LIVE_PER_IP_PER_HOUR": "7", "PARITY_DEFAULT_MODE": "live"})
    assert s.live_per_ip_per_hour == 7
    assert s.default_mode == "live"


def test_judge_fallback_model_comes_from_settings():
    """The judge's fallback tier is configuration, not a literal in the stage (plan Global Constraints)."""
    from parity.config import load_settings

    assert load_settings(env={}).model_for("judge_fallback") == "muse-spark-1.3"
    assert load_settings(env={"PARITY_JUDGE_FALLBACK_MODEL": "muse-spark-1.3-contributor"}).model_for("judge_fallback") == "muse-spark-1.3-contributor"


def test_no_model_id_literals_outside_config_and_pricing():
    """Every runtime model id is a setting: a stage must never name a model."""
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "parity"
    offenders = []
    for path in root.rglob("*.py"):
        if path.name in ("config.py", "pricing.py", "fake.py"):
            continue
        for n, line in enumerate(path.read_text().splitlines(), 1):
            if re.search(r"[\"']muse-[a-z]", line):
                offenders.append(f"{path.relative_to(root)}:{n}: {line.strip()[:80]}")
    assert offenders == [], offenders


def test_open_url_defaults_to_whether_a_key_is_present():
    """Spec §19.3.3: the visitor-URL mode is on when the server can run Live at all; PARITY_OPEN_URL=0 is the kill switch."""
    assert load_settings(env={}).open_url is False
    assert load_settings(env={"MODEL_API_KEY": "sk-x"}).open_url is True
    assert load_settings(env={"MODEL_API_KEY": "sk-x", "PARITY_OPEN_URL": "0"}).open_url is False
    assert load_settings(env={"PARITY_OPEN_URL": "1"}).open_url is True  # explicit wins, even without a key (the route still needs the client)


def test_external_caps_lists_and_contact_parse():
    s = load_settings(env={})
    assert (s.external_run_usd, s.external_daily_usd, s.external_per_origin_per_day, s.external_timeout_s) == (0.5, 5.0, 3, 300)
    assert s.url_deny == () and s.suggested_urls == () and s.contact_email == "tai.suleman@gmail.com"
    s = load_settings(env={"PARITY_URL_DENY": " Denied.example, other.example ,,", "PARITY_SUGGESTED_URLS": "https://a.example/, https://b.example/x",
                           "PARITY_CONTACT_EMAIL": "x@y.z", "PARITY_EXTERNAL_RUN_USD": "0.25", "PARITY_EXTERNAL_DAILY_USD": "10",
                           "PARITY_EXTERNAL_PER_ORIGIN_PER_DAY": "2", "PARITY_EXTERNAL_TIMEOUT_S": "120"})
    assert s.url_deny == ("denied.example", "other.example") and s.suggested_urls == ("https://a.example/", "https://b.example/x")
    assert s.contact_email == "x@y.z" and (s.external_run_usd, s.external_daily_usd, s.external_per_origin_per_day, s.external_timeout_s) == (0.25, 10.0, 2, 120)


def test_per_stage_model_override_falls_back_to_parity_model():
    s = load_settings(env={"PARITY_MODEL": "muse-spark-1.2", "PARITY_SEER_MODEL": "muse-wonder-1.0"})
    assert s.model_for("seer") == "muse-wonder-1.0"
    assert s.model_for("comparator") == "muse-spark-1.2"
    assert s.model_for("navigator") == "muse-spark-1.2"
    assert s.model_for("fixer") == "muse-spark-1.2"


def test_each_stage_reads_its_own_override():
    s = load_settings(env={"PARITY_NAVIGATOR_MODEL": "n", "PARITY_SEER_MODEL": "s", "PARITY_COMPARATOR_MODEL": "c", "PARITY_FIXER_MODEL": "f", "PARITY_JUDGE_MODEL": "j"})
    assert [s.model_for(x) for x in ("navigator", "seer", "comparator", "fixer", "judge")] == ["n", "s", "c", "f", "j"]


def test_reaudit_follows_the_comparator_model_and_private_mode_still_maps():
    s = load_settings(env={"PARITY_COMPARATOR_MODEL": "muse-spark-1.2"})
    assert s.model_for("reaudit") == "muse-spark-1.2"
    p = load_settings(env={"PARITY_PRIVATE": "true", "PARITY_SEER_MODEL": "muse-spark-1.3-contributor"})
    assert p.model_for("seer") == "muse-spark-1.3"


def test_defaults_are_unchanged_without_overrides():
    s = load_settings(env={})
    for stage in ("navigator", "seer", "comparator", "fixer", "reaudit", "judge"):
        assert s.model_for(stage) == "muse-spark-1.3-contributor"
    assert s.model_for("judge_fallback") == "muse-spark-1.3"


def test_effort_for_defaults_match_the_spec():
    s = load_settings(env={})
    assert {x: s.effort_for(x) for x in ("navigator", "seer", "comparator", "judge", "fixer", "reaudit")} == {
        "navigator": "low", "seer": "medium", "comparator": "medium", "judge": "high", "fixer": "medium", "reaudit": "low"}


def test_effort_for_reads_per_stage_overrides():
    s = load_settings(env={"PARITY_NAVIGATOR_EFFORT": "high", "PARITY_SEER_EFFORT": "low", "PARITY_COMPARATOR_EFFORT": "high", "PARITY_JUDGE_EFFORT": "low", "PARITY_FIXER_EFFORT": "high"})
    assert [s.effort_for(x) for x in ("navigator", "seer", "comparator", "judge", "fixer", "reaudit")] == ["high", "low", "high", "low", "high", "low"]


def test_effort_override_outside_the_api_values_is_refused():
    import pytest

    with pytest.raises(ValueError, match="PARITY_SEER_EFFORT"):
        load_settings(env={"PARITY_SEER_EFFORT": "extreme"})
