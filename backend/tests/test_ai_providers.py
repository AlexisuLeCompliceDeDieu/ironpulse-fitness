"""Tests du routeur multi-IA (failover automatique entre fournisseurs)."""

import pytest

from services import ai_providers, quota_tracker


class FakeProvider:
    def __init__(self, pid, label, model="fake-model", configured=True, fail=None, text="ok",
                 tools_result=None):
        self.id = pid
        self.label = label
        self.model = model
        self.configured = configured
        self.fail = fail
        self.text = text
        self.tools_result = tools_result or {"content": "", "tool_calls": []}
        self.tools_calls = 0

    def generate(self, messages, max_tokens, temperature):
        if self.fail:
            raise self.fail
        return self.text

    def generate_tools(self, messages, tools, max_tokens, temperature, tool_choice="auto"):
        self.tools_calls += 1
        if self.fail:
            raise self.fail
        return self.tools_result

    def stream(self, messages, max_tokens, temperature):
        if self.fail:
            raise self.fail
        for piece in _chunks(self.text):
            yield piece


def _chunks(text, size=20):
    for i in range(0, len(text), size):
        yield text[i:i + size]


@pytest.fixture(autouse=True)
def clean_quota(monkeypatch, tmp_path):
    """Isole l'état du quota par test (fichier temporaire, état vierge)."""
    monkeypatch.setattr(quota_tracker, "_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(quota_tracker, "_QUOTA_FILE", str(tmp_path / "quota.json"))
    quota_tracker._save({
        "rpm_timestamps": [],
        "rpd_date": "2000-01-01",
        "rpd_count": 0,
        "total_all_time": 0,
        "auto_disabled": False,
        "last_warning": "",
    })
    monkeypatch.delenv("AI_PROVIDER_ORDER", raising=False)
    return monkeypatch


def _providers(*fakes):
    return {f.id: f for f in fakes}


# ── Classification des erreurs ─────────────────────────────────────

def test_failure_reason_mapping():
    cases = [
        (ai_providers.ProviderError(429, "429 ... tokens per day (TPD): Limit 200000"), "daily_limit"),
        (ai_providers.ProviderError(429, "429 ... too large OTPM"), "per_minute"),
        (ai_providers.ProviderError(401, "invalid api key"), "invalid_key"),
        (ai_providers.ProviderError(429, "rate limit exceeded"), "rate_limit"),
        (ai_providers.ProviderError(404, "model not found"), "model_not_found"),
        (ai_providers.ProviderError(0, "connection refused"), "server_error"),
        (ai_providers.ProviderError(500, "internal"), "server_error"),
        (ai_providers.ProviderError(400, "bad request"), "bad_request"),
    ]
    for err, expected in cases:
        assert ai_providers._failure_reason(err) == expected, err.message


def test_limite_par_minute_ne_desactive_pas_jusqu_a_minuit():
    """Gemini annonce « per minute and per day » : c'est une limite par minute.

    Sans ce test, le message était classé `daily_limit` et le fournisseur restait
    bloqué jusqu'à minuit alors qu'un simple cooldown de 75 s suffisait.
    """
    err = ai_providers.ProviderError(
        429, "Quota exceeded for quota metric 'Generate requests per minute and per day'")
    assert ai_providers._failure_reason(err) == "per_minute"


def test_handle_failure_daily_disable(monkeypatch):
    calls = []
    monkeypatch.setattr(quota_tracker, "disable_provider",
                        lambda pid, reason: calls.append((pid, reason)))
    quotient = ai_providers._handle_failure(
        "groq", ai_providers.ProviderError(429, "tokens per day (TPD)"))
    assert quotient == "daily_limit"
    assert calls == [("groq", "daily_limit")]


def test_handle_failure_per_minute_cooldown(monkeypatch):
    calls = []
    monkeypatch.setattr(quota_tracker, "set_provider_cooldown",
                        lambda pid, seconds: calls.append((pid, seconds)))
    ai_providers._handle_failure("groq", ai_providers.ProviderError(429, "too large OTPM"))
    assert calls == [("groq", 75)]


# ── Ordre de préférence ────────────────────────────────────────────

def test_provider_order_uses_env_and_appends_configured(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER_ORDER", "groq,openrouter")
    monkeypatch.setattr(ai_providers, "PROVIDERS", _providers(
        FakeProvider("groq", "Groq"),
        FakeProvider("openrouter", "OpenRouter"),
        FakeProvider("gemini", "Gemini"),
    ))
    order = ai_providers.provider_order()
    assert order[0] == "groq"
    assert order[1] == "openrouter"
    assert order[2] == "gemini"  # ajouté car configuré mais absent de l'env


def test_provider_order_drops_unknown(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER_ORDER", "groq,inexistant")
    monkeypatch.setattr(ai_providers, "PROVIDERS", _providers(FakeProvider("groq", "Groq")))
    assert ai_providers.provider_order() == ["groq"]


# ── Failover sur generate_text ─────────────────────────────────────

def test_generate_text_fails_over_on_daily_limit(monkeypatch):
    groq = FakeProvider("groq", "Groq", fail=ai_providers.ProviderError(429, "tokens per day (TPD)"))
    gemini = FakeProvider("gemini", "Google Gemini", text="réponse gemini")
    monkeypatch.setattr(ai_providers, "PROVIDERS", _providers(groq, gemini))

    text, info = ai_providers.generate_text([{"role": "user", "content": "x"}])
    assert text == "réponse gemini"
    assert info["provider"] == "gemini"
    # Groq a été désactivé durablement (limite du jour)
    ok, reason = quota_tracker.can_use_provider("groq")
    assert not ok
    assert reason == "daily_limit"


def test_generate_text_skips_unconfigured(monkeypatch):
    gemini = FakeProvider("gemini", "Google Gemini", text="ok")
    monkeypatch.setattr(ai_providers, "PROVIDERS", _providers(
        FakeProvider("groq", "Groq", configured=False), gemini))

    text, info = ai_providers.generate_text([{"role": "user", "content": "x"}])
    assert text == "ok"
    assert info["provider"] == "gemini"


def test_generate_text_none_when_all_fail(monkeypatch):
    monkeypatch.setattr(ai_providers, "PROVIDERS", _providers(
        FakeProvider("groq", "Groq", fail=ai_providers.ProviderError(500, "boom")),
        FakeProvider("gemini", "Google Gemini", fail=ai_providers.ProviderError(429, "rate limit")),
    ))
    text, info = ai_providers.generate_text([{"role": "user", "content": "x"}])
    assert text is None
    assert info["reason"] == "rate_limit"  # dernière tentative réelle
    assert info["raisons"] == {"groq": "server_error", "gemini": "rate_limit"}


def test_echec_global_ignore_les_fournisseurs_non_configures(monkeypatch):
    """Un fournisseur sans clé ne doit pas masquer la vraie cause de l'échec."""
    monkeypatch.setattr(ai_providers, "PROVIDERS", _providers(
        FakeProvider("groq", "Groq", fail=ai_providers.ProviderError(429, "tokens per day (TPD)")),
        FakeProvider("openrouter", "OpenRouter", configured=False),
    ))
    text, info = ai_providers.generate_text([{"role": "user", "content": "x"}])
    assert text is None
    assert info["reason"] == "daily_limit"
    assert info["raisons"]["openrouter"] == "not_configured"


def test_generate_text_bumps_usage(monkeypatch):
    monkeypatch.setattr(ai_providers, "PROVIDERS", _providers(FakeProvider("groq", "Groq")))
    ai_providers.generate_text([{"role": "user", "content": "x"}])
    ok, reason = quota_tracker.can_use_provider("groq")
    assert ok and reason is None
    st = quota_tracker.get_providers_status()["groq"]
    assert st["rpd_used"] == 1


# ── Disponibilité et cooldown ──────────────────────────────────────

def test_available_provider_skips_blocked(monkeypatch):
    monkeypatch.setattr(ai_providers, "PROVIDERS", _providers(
        FakeProvider("groq", "Groq"),
        FakeProvider("gemini", "Google Gemini"),
    ))
    quota_tracker.set_provider_cooldown("groq", seconds=120)
    pid, _, _ = ai_providers.available_provider()
    assert pid == "gemini"


def test_available_provider_none(monkeypatch):
    monkeypatch.setattr(ai_providers, "PROVIDERS", _providers(FakeProvider("groq", "Groq")))
    quota_tracker.disable_provider("groq", "daily_limit")
    pid, provider, reason = ai_providers.available_provider()
    assert pid is None and provider is None
    assert reason == "none_available"


# ── Diagnostic et réactivation ──────────────────────────────────────

def test_diagnostic_explique_le_blocage(monkeypatch):
    monkeypatch.setattr(quota_tracker, "_provider_configured", lambda pid: pid in ("groq", "gemini"))
    quota_tracker.disable_provider("groq", "daily_limit")
    quota_tracker.set_provider_cooldown("gemini", 120)

    diag = quota_tracker.diagnostic()

    assert diag["configured"] == ["groq", "gemini"]
    assert diag["usable"] == []
    assert "limite quotidienne atteinte" in diag["message"]
    assert quota_tracker.explain("cooldown") == "en attente après une limite par minute"


def test_reset_providers_reactive_les_ia(monkeypatch):
    monkeypatch.setattr(quota_tracker, "_provider_configured", lambda pid: pid == "groq")
    quota_tracker.disable_provider("groq", "daily_limit")
    quota_tracker.set_provider_cooldown("groq", 300)
    assert quota_tracker.can_use_provider("groq")[0] is False

    quota_tracker.reset_providers()

    assert quota_tracker.can_use_provider("groq") == (True, None)
    assert quota_tracker.diagnostic()["usable"] == ["groq"]


# ── Streaming ──────────────────────────────────────────────────────

def test_stream_text_fails_over(monkeypatch):
    groq = FakeProvider("groq", "Groq", fail=ai_providers.ProviderError(429, "too large OTPM"))
    mistral = FakeProvider("mistral", "Mistral AI", text="bonjour le monde")
    monkeypatch.setattr(ai_providers, "PROVIDERS", _providers(groq, mistral))

    it, info = ai_providers.stream_text([{"role": "user", "content": "x"}])
    assert info["provider"] == "mistral"
    assert "".join(it) == "bonjour le monde"
    # Groq est en cooldown (pas désactivé définitivement)
    ok, reason = quota_tracker.can_use_provider("groq")
    assert not ok
    assert reason == "cooldown"


def test_stream_text_none_when_all_fail(monkeypatch):
    monkeypatch.setattr(ai_providers, "PROVIDERS", _providers(
        FakeProvider("groq", "Groq", fail=ai_providers.ProviderError(500, "boom")),
    ))
    it, info = ai_providers.stream_text([{"role": "user", "content": "x"}])
    assert it is None
    # La cause réelle est remontée (elle était masquée par « none_available »)
    assert info["reason"] == "server_error"
    assert info["raisons"] == {"groq": "server_error"}


# ── Function calling (tools) + failover ────────────────────────────

TOOLS = [{
    "type": "function",
    "function": {
        "name": "calculer_macros",
        "description": "Répartit les calories",
        "parameters": {"type": "object", "properties": {"calories": {"type": "number"}}, "required": ["calories"]},
    },
}]


def test_generate_with_tools_returns_normalized_calls(monkeypatch):
    attendu = {"content": "", "tool_calls": [{"id": "c1", "name": "calculer_macros", "arguments": {"calories": 2500}}]}
    groq = FakeProvider("groq", "Groq", tools_result=attendu)
    monkeypatch.setattr(ai_providers, "PROVIDERS", _providers(groq))

    resultat, info = ai_providers.generate_with_tools([{"role": "user", "content": "x"}], TOOLS)
    assert resultat == attendu
    assert info["provider"] == "groq"
    assert groq.tools_calls == 1


def test_generate_with_tools_fails_over(monkeypatch):
    """Groq épuisé pour la journée → l'agent bascule sur Gemini, tools comprises."""
    groq = FakeProvider("groq", "Groq", fail=ai_providers.ProviderError(429, "tokens per day (TPD)"))
    gemini = FakeProvider("gemini", "Google Gemini", tools_result={
        "content": "", "tool_calls": [{"id": "g1", "name": "calculer_macros", "arguments": {"calories": 2000}}],
    })
    monkeypatch.setattr(ai_providers, "PROVIDERS", _providers(groq, gemini))

    resultat, info = ai_providers.generate_with_tools([{"role": "user", "content": "x"}], TOOLS)
    assert resultat["tool_calls"][0]["name"] == "calculer_macros"
    assert info["provider"] == "gemini"
    assert info["label"] == "Google Gemini"
    ok, reason = quota_tracker.can_use_provider("groq")
    assert not ok and reason == "daily_limit"


def test_generate_with_tools_none_when_all_fail(monkeypatch):
    monkeypatch.setattr(ai_providers, "PROVIDERS", _providers(
        FakeProvider("groq", "Groq", fail=ai_providers.ProviderError(500, "boom")),
    ))
    resultat, info = ai_providers.generate_with_tools([{"role": "user", "content": "x"}], TOOLS)
    assert resultat is None
    assert info["reason"] == "server_error"


def test_normalize_openai_message_parses_arguments_string():
    """L'API OpenAI renvoie les arguments en JSON string : on les normalise en dict."""
    message = {
        "content": None,
        "tool_calls": [{"id": "call_x", "function": {"name": "calculer_macros", "arguments": '{"calories": 3000}'}}],
    }
    norm = ai_providers._normalize_openai_message(message)
    assert norm["content"] == ""
    assert norm["tool_calls"] == [{"id": "call_x", "name": "calculer_macros", "arguments": {"calories": 3000}}]


def test_gemini_translates_tool_calls_and_responses():
    """Gemini n'utilise ni le rôle assistant ni le rôle tool : on traduit."""
    messages = [
        {"role": "system", "content": "tu es IRONPULSE"},
        {"role": "user", "content": "répartis 3000 kcal"},
        {"role": "assistant", "content": None, "tool_calls": [{
            "id": "c1", "type": "function",
            "function": {"name": "calculer_macros", "arguments": '{"calories": 3000}'},
        }]},
        {"role": "tool", "tool_call_id": "c1", "name": "calculer_macros", "content": '{"proteines_g": 225}'},
    ]
    system, contents = ai_providers.PROVIDERS["gemini"]._to_gemini_tools(messages, TOOLS, "auto")

    assert system == ["tu es IRONPULSE"]
    assert contents[0] == {"role": "user", "parts": [{"text": "répartis 3000 kcal"}]}
    assert contents[1]["role"] == "model"
    assert contents[1]["parts"][0]["functionCall"] == {"name": "calculer_macros", "args": {"calories": 3000}}
    assert contents[2]["role"] == "user"
    part = contents[2]["parts"][0]["functionResponse"]
    assert part["name"] == "calculer_macros"
    assert part["response"]["result"] == {"proteines_g": 225}