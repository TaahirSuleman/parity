from parity.config import load_settings


def test_settings_defaults_replay():
    s = load_settings(env={})
    assert s.default_mode == "replay"
    assert s.live_per_ip_per_hour == 3


def test_model_for_defaults_contributor():
    s = load_settings(env={})
    assert s.model_for("comparator") == "muse-spark-1.3-contributor"
    assert s.model_for("judge") == "muse-spark-1.3"


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
