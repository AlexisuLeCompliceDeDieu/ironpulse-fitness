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