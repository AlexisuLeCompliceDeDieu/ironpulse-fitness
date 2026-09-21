import sys
from unittest.mock import MagicMock

from services import ai_meal_agent


def test_max_tokens_scaled():
    assert 700 <= ai_meal_agent._max_tokens_for(1) <= 3000
    assert ai_meal_agent._max_tokens_for(2) < ai_meal_agent._max_tokens_for(7)
    assert ai_meal_agent._max_tokens_for(90) <= 3000


def test_create_completion_retries_without_reasoning():
    """Si l'API refuse reasoning_effort, on rejoue sans ce paramètre."""
    client = MagicMock()
    ok = MagicMock()
    ok.choices[0].message.content = "{\"meals\": []}"
    client.chat.completions.create.side_effect = [
        Exception("400 ... reasoning ..."),
        ok,
    ]
    resp = ai_meal_agent._create_completion(client, [{"role": "user", "content": "x"}], 1000)
    assert resp is ok
    assert client.chat.completions.create.call_count == 2
    # le second appel ne doit plus contenir reasoning_effort
    kwargs = client.chat.completions.create.call_args.kwargs
    assert "reasoning_effort" not in kwargs


def test_create_completion_passes_reasoning_when_supported():
    client = MagicMock()
    ok = MagicMock()
    ok.choices[0].message.content = "{}"
    client.chat.completions.create.return_value = ok
    ai_meal_agent._create_completion(client, [{"role": "user", "content": "x"}], 1000)
    kwargs = client.chat.completions.create.call_args.kwargs
    assert kwargs.get("reasoning_effort") == "none"


def test_is_rate_limit():
    assert ai_meal_agent._is_rate_limit(Exception("429 ... too large OTPM"))
    assert ai_meal_agent._is_rate_limit(Exception("quota exceeded"))
    assert not ai_meal_agent._is_rate_limit(Exception("parse error"))


def test_is_tpd_limit():
    assert ai_meal_agent._is_tpd_limit(Exception("429 ... tokens per day (TPD): Limit 200000"))
    assert ai_meal_agent._is_tpd_limit(Exception("Rate limit ... on tokens per day"))
    assert not ai_meal_agent._is_tpd_limit(Exception("429 too large OTPM"))
    assert not ai_meal_agent._is_tpd_limit(Exception("quota exceeded"))


def test_parse_content_strips_thinking_and_markdown():
    content = "```json\n{\"meals\": [{\"day\": 1, \"meal_type\": \"Déjeuner\", \"name\": \"Test\", \"items\": []}]}\n```"
    meals = ai_meal_agent._parse_content(content)
    assert meals[0]["name"] == "Test"


def test_parse_content_clamps_surrounding_text():
    content = "Voici le plan :\n{\"meals\": [{\"day\": 1, \"meal_type\": \"Déjeuner\", \"name\": \"Test\", \"items\": []}]}\nFin du plan."
    meals = ai_meal_agent._parse_content(content)
    assert meals[0]["name"] == "Test"


def test_parse_content_merges_multiple_objects():
    """Le modèle sort parfois un objet JSON par jour : on les fusionne."""
    content = (
        "{\"meals\": [{\"day\": 1, \"meal_type\": \"Déjeuner\", \"name\": \"Jour1\", \"items\": []}]}\n"
        "{\"meals\": [{\"day\": 2, \"meal_type\": \"Dîner\", \"name\": \"Jour2\", \"items\": []}]}"
    )
    meals = ai_meal_agent._parse_content(content)
    assert len(meals) == 2
    assert meals[0]["name"] == "Jour1"
    assert meals[1]["name"] == "Jour2"


def test_parse_content_repairs_trailing_commas():
    content = "{\"meals\": [{\"day\": 1, \"meal_type\": \"Déjeuner\", \"name\": \"Test\", \"items\": [{\"food\": \"riz\", \"quantity\": 100},],}]}"
    meals = ai_meal_agent._parse_content(content)
    assert meals[0]["name"] == "Test"
    assert meals[0]["items"][0]["food"] == "riz"


def test_normalize_day_relative():
    assert ai_meal_agent._normalize_day(1, 2) == 1
    assert ai_meal_agent._normalize_day("2", 2) == 2
    assert ai_meal_agent._normalize_day("lundi", 2) == 1
    assert ai_meal_agent._normalize_day(3, 2) is None  # hors du morceau
    assert ai_meal_agent._normalize_day("", 2) is None


def test_normalize_meal_type():
    assert ai_meal_agent._normalize_meal_type("breakfast") == "Petit-déjeuner"
    assert ai_meal_agent._normalize_meal_type("dîner") == "Dîner"
    assert ai_meal_agent._normalize_meal_type("snack") == "Collation"
    assert ai_meal_agent._normalize_meal_type("apéritif") is None


def test_build_prompt_has_day_offset():
    ctx = {"goal": "prise_masse", "weight": 70, "calories": 3000, "restrictions": [], "foods": [{"name": "riz"}]}
    prompt = ai_meal_agent._build_prompt(ctx, 2, None, day_offset=3)
    assert "JOURS 4 à 5" in prompt
    assert "day 1 = jour 4" in prompt