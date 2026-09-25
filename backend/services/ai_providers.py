"""Routeur multi-fournisseurs IA avec FAILOVER automatique (gratuit, 100 % stdlib).

Fournisseurs (tous avec un tier gratuit, clé optionnelle via l'environnement) :
  - groq       : Groq          (GROQ_API_KEY,  défaut qwen/qwen3.8-27b)
  - gemini     : Google Gemini (GEMINI_API_KEY, défaut gemini-2.0-flash)
  - mistral    : Mistral AI    (MISTRAL_API_KEY, défaut open-mistral-nemo)
  - openrouter : OpenRouter    (OPENROUTER_API_KEY, défaut qwen/qwen-2.5-72b-instruct:free)

Ordre de préférence : `AI_PROVIDER_ORDER` (ex: "groq,gemini,mistral,openrouter").
Un fournisseur est sauté s'il n'est pas configuré, s'il a dépassé son quota du
jour (désactivé jusqu'à minuit) ou s'il est en cooldown (limite par minute).
Chaque erreur d'API le disqualifie automatiquement et on essaie le suivant —
l'utilisateur ne voit rien, ou seulement le nom du fournisseur qui a répondu.
"""

import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from services import quota_tracker

logger = logging.getLogger(__name__)

DEFAULT_ORDER = ["groq", "gemini", "mistral", "openrouter"]
HTTP_TIMEOUT = 90


class ProviderError(Exception):
    """Erreur réseau/API d'un fournisseur. `status` 0 = échec réseau."""

    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = str(message)


# ── Helpers HTTP ────────────────────────────────────────────────────

def _http_json(url, headers, payload):
    """POST JSON, retourne (status, dict). Lève ProviderError en cas d'échec."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        raise ProviderError(e.code, body[:500]) from e
    except urllib.error.URLError as e:
        raise ProviderError(0, str(e.reason)) from e
    except Exception as e:
        raise ProviderError(0, str(e)) from e


def _openai_chat(url, key, model, messages, max_tokens, temperature, extra=None):
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    if extra:
        payload.update(extra)
    _, data = _http_json(url, headers, payload)
    return data["choices"][0]["message"]["content"]


def _openai_chat_tools(url, key, model, messages, tools, max_tokens, temperature,
                       tool_choice="auto", extra=None):
    """POST JSON avec function calling (API OpenAI-compatible). Retourne le message brut."""
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": messages,
        "tools": tools,
        "tool_choice": tool_choice,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    if extra:
        payload.update(extra)
    _, data = _http_json(url, headers, payload)
    return data["choices"][0]["message"]


def _normalize_openai_message(message):
    """Message OpenAI → format normalisé de l'agent : {content, tool_calls}."""
    tool_calls = []
    for tc in (message.get("tool_calls") or []):
        fn = tc.get("function") or {}
        args = fn.get("arguments")
        if isinstance(args, str):
            try:
                args = json.loads(args or "{}")
            except ValueError:
                args = {}
        if not isinstance(args, dict):
            args = {}
        tool_calls.append({
            "id": tc.get("id") or f"call_{len(tool_calls)}",
            "name": fn.get("name") or "",
            "arguments": args,
        })
    return {"content": message.get("content") or "", "tool_calls": tool_calls}


def _sse_stream(url, key, model, messages, max_tokens, temperature, extra=None):
    """Générateur de morceaux de texte via un flux SSE (OpenAI-compatible)."""
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }
    if extra:
        payload.update(extra)
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                payload_line = line[5:].strip()
                if payload_line == "[DONE]":
                    break
                try:
                    obj = json.loads(payload_line)
                except ValueError:
                    continue
                delta = (obj.get("choices") or [{}])[0].get("delta", {}).get("content")
                if delta:
                    yield delta
    except Exception as e:
        logger.error(f"SSE interrompu ({model}): {e}")
        yield ""  # signal d'arrêt propre, l'appelant émet une erreur si rient n'a coulé


# ── Fournisseurs ────────────────────────────────────────────────────

class _BaseProvider:
    id = ""
    label = ""
    key_env = ""
    default_model = ""

    @property
    def configured(self):
        return bool(os.environ.get(self.key_env, ""))

    @property
    def model(self):
        return os.environ.get(f"{self.id.upper()}_MODEL", self.default_model)

    def generate(self, messages, max_tokens, temperature):  # pragma: no cover - interface
        raise NotImplementedError

    def generate_tools(self, messages, tools, max_tokens, temperature, tool_choice="auto"):  # pragma: no cover - interface
        raise NotImplementedError

    def stream(self, messages, max_tokens, temperature):  # pragma: no cover - interface
        raise NotImplementedError


class GroqProvider(_BaseProvider):
    id = "groq"
    label = "Groq"
    key_env = "GROQ_API_KEY"
    default_model = "qwen/qwen3.8-27b"

    def generate(self, messages, max_tokens, temperature):
        url = "https://api.groq.com/openai/v1/chat/completions"
        key = os.environ.get("GROQ_API_KEY")
        try:
            return _openai_chat(url, key, self.model, messages, max_tokens, temperature,
                                extra={"reasoning_effort": "none"})
        except ProviderError as e:
            # Certains modèles n'acceptent pas reasoning_effort : on rejoue sans.
            low = e.message.lower()
            if (e.status == 400 or "reasoning" in low or "invalid" in low):
                return _openai_chat(url, key, self.model, messages, max_tokens, temperature)
            raise

    def stream(self, messages, max_tokens, temperature):
        url = "https://api.groq.com/openai/v1/chat/completions"
        key = os.environ.get("GROQ_API_KEY")
        try:
            return _sse_stream(url, key, self.model, messages, max_tokens, temperature,
                               extra={"reasoning_effort": "none"})
        except ProviderError as e:
            low = e.message.lower()
            if (e.status == 400 or "reasoning" in low or "invalid" in low):
                return _sse_stream(url, key, self.model, messages, max_tokens, temperature)
            raise

    def generate_tools(self, messages, tools, max_tokens, temperature, tool_choice="auto"):
        url = "https://api.groq.com/openai/v1/chat/completions"
        key = os.environ.get("GROQ_API_KEY")
        try:
            message = _openai_chat_tools(url, key, self.model, messages, tools, max_tokens,
                                         temperature, tool_choice,
                                         extra={"reasoning_effort": "none"})
        except ProviderError as e:
            low = e.message.lower()
            if (e.status == 400 or "reasoning" in low or "invalid" in low):
                message = _openai_chat_tools(url, key, self.model, messages, tools, max_tokens,
                                             temperature, tool_choice)
            else:
                raise
        return _normalize_openai_message(message)


class GeminiProvider(_BaseProvider):
    id = "gemini"
    label = "Google Gemini"
    key_env = "GEMINI_API_KEY"
    default_model = "gemini-2.0-flash"

    @staticmethod
    def _to_gemini(messages):
        system = [m["content"] for m in messages if m["role"] == "system"]
        contents = []
        for m in messages:
            if m["role"] == "system":
                continue
            role = "user" if m["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})
        return system, contents

    def generate(self, messages, max_tokens, temperature):
        url = ("https://generativelanguage.googleapis.com/v1beta/models/"
               f"{urllib.parse.quote(self.model)}:generateContent"
               f"?key={urllib.parse.quote(os.environ.get('GEMINI_API_KEY', ''))}")
        system, contents = self._to_gemini(messages)
        payload = {
            "contents": contents,
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
        }
        if system:
            payload["system_instruction"] = {"parts": [{"text": "\n".join(system)}]}
        _, data = _http_json(url, {}, payload)
        candidates = data.get("candidates") or []
        if not candidates:
            raise ProviderError(200, "Gemini : aucune réponse")
        parts = (candidates[0].get("content") or {}).get("parts") or []
        return "".join(p.get("text", "") for p in parts)

    def stream(self, messages, max_tokens, temperature):
        full = self.generate(messages[:], max_tokens, temperature)  # pas de streaming natif : on bufferise
        yield from _chunk_text(full)

    @staticmethod
    def _to_gemini_tools(messages, tools, tool_choice):
        """Traduit les messages OpenAI (avec tool_calls et résultats de tools)
        vers le format Gemini (functionCall / functionResponse)."""
        system = [m.get("content") for m in messages if m["role"] == "system"]
        contents = []
        for m in messages:
            role = m.get("role")
            if role == "system":
                continue
            if role == "user":
                contents.append({"role": "user", "parts": [{"text": m.get("content") or ""}]})
            elif role == "assistant":
                parts = []
                if m.get("content"):
                    parts.append({"text": m["content"]})
                for tc in (m.get("tool_calls") or []):
                    fn = tc.get("function") or {}
                    args = fn.get("arguments")
                    if isinstance(args, str):
                        try:
                            args = json.loads(args or "{}")
                        except ValueError:
                            args = {}
                    parts.append({"functionCall": {
                        "name": fn.get("name") or "",
                        "args": args if isinstance(args, dict) else {},
                    }})
                if parts:
                    contents.append({"role": "model", "parts": parts})
            elif role == "tool":
                reponse = m.get("content")
                try:
                    reponse = json.loads(reponse) if isinstance(reponse, str) else reponse
                except ValueError:
                    pass
                part = {"functionResponse": {
                    "name": m.get("name") or "",
                    "response": {"result": reponse},
                }}
                # Gemini regroupe les résultats de tools parallèles dans un seul contenu
                precedente = contents[-1] if contents else None
                if (precedente and precedente["role"] == "user"
                        and precedente["parts"] and "functionResponse" in precedente["parts"][0]):
                    precedente["parts"].append(part)
                else:
                    contents.append({"role": "user", "parts": [part]})
        return system, contents

    def generate_tools(self, messages, tools, max_tokens, temperature, tool_choice="auto"):
        url = ("https://generativelanguage.googleapis.com/v1beta/models/"
               f"{urllib.parse.quote(self.model)}:generateContent"
               f"?key={urllib.parse.quote(os.environ.get('GEMINI_API_KEY', ''))}")
        system, contents = self._to_gemini_tools(messages, tools, tool_choice)
        payload = {
            "contents": contents,
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
        }
        if system:
            payload["system_instruction"] = {"parts": [{"text": "\n".join(system)}]}

        declarations = []
        for t in tools or []:
            fn = t.get("function") or {}
            params = dict(fn.get("parameters") or {"type": "object", "properties": {}})
            if not params.get("required"):
                params.pop("required", None)
            declarations.append({
                "name": fn.get("name"),
                "description": fn.get("description", ""),
                "parameters": params,
            })
        if declarations:
            payload["tools"] = [{"function_declarations": declarations}]
            mode = "ANY" if tool_choice in ("any", "required") else "AUTO"
            payload["tool_config"] = {"function_calling_config": {"mode": mode}}

        _, data = _http_json(url, {}, payload)
        candidates = data.get("candidates") or []
        if not candidates:
            raise ProviderError(200, "Gemini : aucune réponse")
        parts = (candidates[0].get("content") or {}).get("parts") or []

        text = "".join(p.get("text", "") for p in parts if p.get("text"))
        tool_calls = []
        for p in parts:
            fc = p.get("functionCall")
            if not fc:
                continue
            args = fc.get("args") or fc.get("arguments") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args or "{}")
                except ValueError:
                    args = {}
            tool_calls.append({
                "id": f"call_{len(tool_calls)}",
                "name": fc.get("name") or "",
                "arguments": args if isinstance(args, dict) else {},
            })
        return {"content": text, "tool_calls": tool_calls}


class OpenRouterProvider(_BaseProvider):
    id = "openrouter"
    label = "OpenRouter"
    key_env = "OPENROUTER_API_KEY"
    default_model = "qwen/qwen-2.5-72b-instruct:free"

    def _headers(self):
        return {"Authorization": f"Bearer {os.environ.get('OPENROUTER_API_KEY', '')}",
                "Content-Type": "application/json"}

    def generate(self, messages, max_tokens, temperature):
        url = "https://openrouter.ai/api/v1/chat/completions"
        return _openai_chat(url, os.environ.get("OPENROUTER_API_KEY", ""), self.model,
                            messages, max_tokens, temperature)

    def stream(self, messages, max_tokens, temperature):
        url = "https://openrouter.ai/api/v1/chat/completions"
        return _sse_stream(url, os.environ.get("OPENROUTER_API_KEY", ""), self.model,
                           messages, max_tokens, temperature)

    def generate_tools(self, messages, tools, max_tokens, temperature, tool_choice="auto"):
        url = "https://openrouter.ai/api/v1/chat/completions"
        message = _openai_chat_tools(url, os.environ.get("OPENROUTER_API_KEY", ""), self.model,
                                     messages, tools, max_tokens, temperature, tool_choice)
        return _normalize_openai_message(message)


class MistralProvider(_BaseProvider):
    id = "mistral"
    label = "Mistral AI"
    key_env = "MISTRAL_API_KEY"
    default_model = "open-mistral-nemo"

    def generate(self, messages, max_tokens, temperature):
        url = "https://api.mistral.ai/v1/chat/completions"
        return _openai_chat(url, os.environ.get("MISTRAL_API_KEY", ""), self.model,
                            messages, max_tokens, temperature)

    def stream(self, messages, max_tokens, temperature):
        url = "https://api.mistral.ai/v1/chat/completions"
        return _sse_stream(url, os.environ.get("MISTRAL_API_KEY", ""), self.model,
                           messages, max_tokens, temperature)

    def generate_tools(self, messages, tools, max_tokens, temperature, tool_choice="auto"):
        url = "https://api.mistral.ai/v1/chat/completions"
        message = _openai_chat_tools(url, os.environ.get("MISTRAL_API_KEY", ""), self.model,
                                     messages, tools, max_tokens, temperature, tool_choice)
        return _normalize_openai_message(message)


PROVIDERS = {
    p.id: p for p in (
        GroqProvider(), GeminiProvider(), MistralProvider(), OpenRouterProvider(),
    )
}


def _chunk_text(text, size=40):
    """Découpe un texte en morceaux ~size chars (aux frontières de mots)."""
    words = text.replace("\n", " \n ").split(" ")
    buf = ""
    for w in words:
        if len(buf) + len(w) + 1 > size and buf:
            yield buf + " "
            buf = w
        else:
            buf = (buf + " " + w).strip() if buf else w
    if buf:
        yield buf


# ── Gestion des erreurs ─────────────────────────────────────────────

def _failure_reason(err, provider=None):
    low = (err.message or "").lower()
    if "tokens per day" in low or " per day" in low or " tpd" in low:
        return "daily_limit"
    if "tokens per minute" in low or " per minute" in low or "too large" in low or "otpm" in low:
        return "per_minute"
    if err.status in (401, 403):
        return "invalid_key"
    if err.status == 429:
        return "rate_limit"
    if err.status == 404:
        return "model_not_found"
    if err.status >= 500 or err.status == 0:
        return "server_error"
    if err.status == 400:
        return "bad_request"
    return "unknown"


def _handle_failure(provider_id, err):
    reason = _failure_reason(err)
    logger.warning(f"Fournisseur {provider_id} en échec ({reason}): {err.message[:160]}")
    if reason == "daily_limit":
        quota_tracker.disable_provider(provider_id, "daily_limit")
    elif reason == "invalid_key":
        quota_tracker.disable_provider(provider_id, "invalid_key")
    elif reason in ("rate_limit", "per_minute"):
        quota_tracker.set_provider_cooldown(provider_id, 75)
    # server_error / bad_request / model_not_found : transitoire, on passe au suivant
    return reason


def provider_order():
    raw = os.environ.get("AI_PROVIDER_ORDER", ",".join(DEFAULT_ORDER))
    order = [pid.strip() for pid in raw.split(",") if pid.strip() in PROVIDERS]
    # Complète l'ordre avec les fournisseurs configurés absents
    for pid in PROVIDERS:
        if pid not in order and PROVIDERS[pid].configured:
            order.append(pid)
    return order or ["groq"]


def available_provider():
    """Retourne (provider_id, provider, reason_si_bloqué)."""
    for pid in provider_order():
        p = PROVIDERS[pid]
        if not p.configured:
            continue
        ok, reason = quota_tracker.can_use_provider(pid)
        if not ok:
            logger.info(f"Fournisseur {pid} indisponible ({reason})")
            continue
        return pid, p, None
    return None, None, "none_available"


def generate_text(messages, max_tokens=2048, temperature=0.7):
    """Génère un texte en testant chaque fournisseur configuré (failover).

    Retourne (text, info) avec info = {provider, label, model} en cas de succès,
    ou (None, info) où info["reason"] explique l'échec global.
    """
    attempts = []
    for pid in provider_order():
        p = PROVIDERS[pid]
        if not p.configured:
            attempts.append({"provider": pid, "ok": False, "reason": "not_configured"})
            continue
        ok, reason = quota_tracker.can_use_provider(pid)
        if not ok:
            attempts.append({"provider": pid, "ok": False, "reason": reason})
            continue
        try:
            text = p.generate(messages, max_tokens, temperature)
            quota_tracker.record_provider_usage(pid)
            return text, {"provider": pid, "label": p.label, "model": p.model}
        except ProviderError as e:
            reason = _handle_failure(pid, e)
            attempts.append({"provider": pid, "ok": False, "reason": reason})
            continue
    last = attempts[-1] if attempts else {}
    return None, {"reason": last.get("reason", "none_available"), "attempts": attempts}


def generate_with_tools(messages, tools, max_tokens=2048, temperature=0.7, tool_choice="auto"):
    """Function calling avec failover (utilisé par l'agent IRONPULSE).

    Les fournisseurs OpenAI-compatible reçoivent les tools telles quelles ;
    Gemini est traduit (functionCall / functionResponse). Tous renvoient le MÊME
    format normalisé, ce qui rend l'agent indépendant du fournisseur :
        {"content": str, "tool_calls": [{"id", "name", "arguments": dict}, ...]}

    Retourne (résultat, info) avec info = {provider, label, model} en cas de
    succès, ou (None, info) où info["reason"] explique l'échec global.
    """
    attempts = []
    for pid in provider_order():
        p = PROVIDERS[pid]
        if not p.configured:
            attempts.append({"provider": pid, "ok": False, "reason": "not_configured"})
            continue
        ok, reason = quota_tracker.can_use_provider(pid)
        if not ok:
            attempts.append({"provider": pid, "ok": False, "reason": reason})
            continue
        try:
            resultat = p.generate_tools(messages, tools, max_tokens, temperature, tool_choice)
            quota_tracker.record_provider_usage(pid)
            return resultat, {"provider": pid, "label": p.label, "model": p.model}
        except ProviderError as e:
            reason = _handle_failure(pid, e)
            attempts.append({"provider": pid, "ok": False, "reason": reason})
            continue
    last = attempts[-1] if attempts else {}
    return None, {"reason": last.get("reason", "none_available"), "attempts": attempts}


def _prepend(first, rest):
    """Ré-émet un premier morceau déjà consommé puis itère la suite."""
    if first:
        yield first
    yield from rest


def stream_text(messages, max_tokens=2048, temperature=0.7):
    """Démarre un stream chez le premier fournisseur disponible (avec failover).

    Les générateurs (SSE…) sont paresseux : on consomme le premier morceau de
    façon contrôlée ici pour valider la connexion. Si le fournisseur échoue
    avant d'avoir produit un token, on essaie le suivant. Retourne
    (generator, info) ou (None, info) si rien ne peut démarrer.
    """
    for pid in provider_order():
        p = PROVIDERS[pid]
        if not p.configured:
            continue
        ok, reason = quota_tracker.can_use_provider(pid)
        if not ok:
            continue
        try:
            it = iter(p.stream(messages, max_tokens, temperature))
            first = next(it)
            quota_tracker.record_provider_usage(pid)
            return _prepend(first, it), {"provider": pid, "label": p.label, "model": p.model}
        except StopIteration:
            continue  # rien produit : on passe au suivant
        except ProviderError as e:
            _handle_failure(pid, e)
            continue
        except Exception as e:
            logger.warning(f"Fournisseur {pid} : échec au démarrage du stream : {e}")
            quota_tracker.set_provider_cooldown(pid, 30)
            continue
    return None, {"reason": "none_available"}


def active_provider_id():
    """Premier fournisseur configuré ET actuellement utilisable (pour l'UI)."""
    pid, _, _ = available_provider()
    return pid