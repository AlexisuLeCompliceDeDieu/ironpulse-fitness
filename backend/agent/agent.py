"""Boucle agentique IRONPULSE.

C'est ici que vit la boucle du cahier des charges (diapos 3 et 9) :
  perception → raisonnement → action (tool) → observation → décision

  [1] Perception    la demande utilisateur + le prompt système
  [2] Raisonnement  le LLM choisit un tool (ou décide de répondre)
  [3] Action        votre code Python exécute le tool (le LLM n'exécute rien)
  [4] Observation    le résultat est renvoyé au LLM (role: "tool")
  [5] Décision       objectif atteint ? sinon → nouveau tour de boucle

Garde-fous :
  - max_tours limite le nombre de tours (anti-boucle infinie, diapo 9) ;
  - quota_tracker borne la consommation Groq (diapo 18 : contrôle des coûts) ;
  - actions sensibles (écriture en base) soumises à validation humaine (diapo 18).

Toute demande et chaque étape de la boucle sont tracées en base (tables
demandes / resultats, `outil_utilise` rend le raisonnement auditable).
"""

import inspect
import json
import logging

from models import db, Demande, Resultat

from services.groq_config import get_client, GROQ_MODEL
from services import quota_tracker

from agent.tools import TOOLS_IMPL, TOOL_SCHEMAS, SENSITIVE_TOOLS

logger = logging.getLogger(__name__)

MAX_TOURS = int(__import__("os").environ.get("AGENT_MAX_TOURS", "5"))
TEMPERATURE = 0.4


SYSTEM_PROMPT = """Tu es « IRONPULSE Coach », un coach sportif et nutritionniste.
Tu es un assistant AGENTIQUE : pour répondre avec des données réelles, tu appelles des outils (function calling) au lieu d'inventer des chiffres.

RÈGLES STRICTES :
1. Pour parler du profil d'un utilisateur, appelle consulter_profil.
2. Pour parler de sa progression ou de ses dernières séances, appelle consulter_progression.
3. Pour tout calcul de macros ou de répartition calorique, appelle calculer_macros (jamais de calcul à la main).
4. Pour recommander la prochaine séance, appelle proposer_seance.
5. Pour enregistrer une séance réalisée, appelle enregistrer_seance : l'action sera soumise à la validation de l'utilisateur.
6. Si la demande est ambiguë ou incomplète, demande une précision au lieu de deviner.
7. Si les données indiquent un problème (ressenti très bas, stagnation), signale-le et propose une action adaptée.
8. Réponds TOUJOURS en français, de façon concise (5 à 10 phrases maximum), pratique et encourageante.
9. Cite brièvement les données réelles que tu as obtenues par les outils (poids, volume, ressenti...) pour montrer que ta réponse s'appuie sur la base."""


def _get_client():
    """Retourne le client Groq (factorisé pour être facilement mocké en test)."""
    return get_client()


def _create_completion(client, messages, max_tokens=900):
    """Appel LLM avec tools ; réessaie sans `reasoning_effort` si le modèle le refuse."""
    try:
        return client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
            temperature=TEMPERATURE,
            max_tokens=max_tokens,
            reasoning_effort="none",
        )
    except Exception as e:  # noqa: BLE001
        msg = str(e).lower()
        if "reasoning" in msg or "400" in msg or "invalid" in msg or "unsupported" in msg:
            return client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
                temperature=TEMPERATURE,
                max_tokens=max_tokens,
            )
        raise


def _save_resultat(demande_id, etape, outil, arguments, reponse):
    """Enregistre une étape de boucle dans la table de trace resultats."""
    db.session.add(Resultat(
        demande_id=demande_id,
        etape=etape,
        outil_utilise=outil,
        arguments=json.dumps(arguments, ensure_ascii=False) if arguments is not None else "",
        reponse=json.dumps(reponse, ensure_ascii=False, default=str) if not isinstance(reponse, str) else reponse,
    ))
    db.session.flush()


def _execute_tool(nom, arguments):
    """Exécute un tool par son nom. Ne doit jamais lever : renvoie un dict d'erreur.

    Seuls les paramètres déclarés par le tool sont transmis (calculer_macros,
    par exemple, est pur et ignore `utilisateur_id`).
    """
    fonction = TOOLS_IMPL.get(nom)
    if fonction is None:
        return {"error": f"Tool inconnu : {nom}"}
    try:
        acceptes = set(inspect.signature(fonction).parameters)
        args_filtres = {k: v for k, v in arguments.items() if k in acceptes}
        return fonction(**args_filtres)
    except Exception as e:  # noqa: BLE001
        logger.error(f"Tool {nom} en échec : {e!r}")
        return {"error": f"Échec du tool {nom} : {type(e).__name__}: {str(e)[:300]}"}


def _questions_sensibles(utilisateur, nom, arguments):
    """Message de demande de validation humaine pour un tool d'écriture."""
    if nom == "enregistrer_seance":
        date = arguments.get("date") or "aujourd'hui"
        ressenti = arguments.get("ressenti", "?")
        return (
            f"Confirmer l'enregistrement de la séance du {date} "
            f"avec un ressenti de {ressenti}/5 ?"
        )
    return f"Confirmer l'exécution de l'action « {nom} » ?"


def executer(utilisateur, demande, confirmation=None, demande_id=None):
    """Lance (ou poursuit) la boucle agent pour une demande utilisateur.

    Retourne un dict :
      statut  : "reponse" | "confirmation_requise" | "limite" | "quota" | "erreur"
      reponse : texte final (si statut = reponse)
      etapes  : liste des étapes exécutées {etape, outil, arguments, resultat}
    """
    demande = (demande or "").strip()
    if not demande:
        return {"statut": "erreur", "reponse": "Demande vide.", "etapes": []}

    # ── Demande de trace : on réutilise la ligne existante si continuation ──
    if demande_id:
        demande_row = db.session.get(Demande, demande_id)
        if not demande_row or demande_row.utilisateur_id != utilisateur.id:
            return {"statut": "erreur", "reponse": "Demande de trace introuvable.", "etapes": []}
    else:
        demande_row = Demande(utilisateur_id=utilisateur.id, texte=demande)
        db.session.add(demande_row)
        db.session.flush()

    etape = 1
    if demande_row.resultats:
        etape = max(r.etape for r in demande_row.resultats) + 1

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": demande},
    ]

    # Tool d'écriture déjà validé par l'utilisateur (continuation de boucle)
    deja_valide = None
    if confirmation:
        nom_c = confirmation.get("tool")
        args_c = dict(confirmation.get("arguments") or {})
        args_c.setdefault("utilisateur_id", utilisateur.id)
        resultat_c = _execute_tool(nom_c, args_c)
        observation = json.dumps(resultat_c, ensure_ascii=False, default=str)
        _save_resultat(demande_row.id, etape, nom_c, args_c, resultat_c)
        messages.append({
            "role": "user",
            "content": (
                f"L'utilisateur a VALIDÉ l'exécution de {nom_c}. "
                f"Résultat obtenu : {observation}. Tu peux conclure ta réponse."
            ),
        })
        deja_valide = (nom_c, json.dumps({k: v for k, v in args_c.items() if k != "utilisateur_id"}, sort_keys=True))
        etape += 1

    etapes = []
    client = _get_client()
    if client is None:
        if confirmation:
            db.session.commit()   # l'action validée a été exécutée et tracée : on garde
        else:
            db.session.rollback()  # rien d'utile à garder, on abandonne la trace vide
        return {"statut": "erreur", "reponse": "Agent non configuré (clé API manquante).", "etapes": []}

    for tour in range(MAX_TOURS):
        # Garde-fou coûts : quota avant chaque appel LLM
        allowed, quota_info = quota_tracker.check_quota()
        if not allowed:
            _save_resultat(demande_row.id, etape, None, None, "Quota IA épuisé, réponse interrompue.")
            db.session.commit()
            return {"statut": "quota", "reponse": "Quota IA temporairement épuisé. Réessaye un peu plus tard.", "etapes": etapes, "quota": quota_info}

        try:
            reponse_llm = _create_completion(client, messages)
            quota_tracker.record_usage()
        except Exception as e:  # noqa: BLE001
            logger.error(f"Appel LLM de l'agent en échec : {e}")
            db.session.commit()
            return {"statut": "erreur", "reponse": f"Erreur d'appel IA : {str(e)[:200]}", "etapes": etapes}

        message = reponse_llm.choices[0].message
        messages.append(message)

        appels = getattr(message, "tool_calls", None) or []
        if not appels:
            # Décision : objectif atteint, on répond
            conclusion = (message.content or "").strip() or "Terminé."
            _save_resultat(demande_row.id, etape, None, None, conclusion)
            db.session.commit()
            return {"statut": "reponse", "reponse": conclusion, "etapes": etapes, "demande_id": demande_row.id}

        for appel in appels:
            nom = (appel.function.name or "").strip()
            raw_args = appel.function.arguments or "{}"
            if isinstance(raw_args, str):
                try:
                    args = json.loads(raw_args)
                except json.JSONDecodeError:
                    args = {}
            else:
                args = raw_args
            if not isinstance(args, dict):
                args = {}
            args.setdefault("utilisateur_id", utilisateur.id)

            # Action sensible sans validation préalable → pause, on demande confirmation
            if nom in SENSITIVE_TOOLS and (nom, json.dumps({k: v for k, v in args.items() if k != "utilisateur_id"}, sort_keys=True)) != deja_valide:
                db.session.commit()
                return {
                    "statut": "confirmation_requise",
                    "reponse": _questions_sensibles(utilisateur, nom, args),
                    "confirmation": {"tool": nom, "arguments": {k: v for k, v in args.items() if k != "utilisateur_id"}},
                    "demande_id": demande_row.id,
                    "etapes": etapes,
                }

            etapes.append({"etape": len(etapes) + 1, "outil": nom, "arguments": args, "resultat": None})
            resultat = _execute_tool(nom, args)
            observation = json.dumps(resultat, ensure_ascii=False, default=str)
            etapes[-1]["resultat"] = resultat
            _save_resultat(demande_row.id, etape, nom, args, resultat)
            etape += 1

            messages.append({
                "role": "tool",
                "tool_call_id": getattr(appel, "id", None) or f"call_{tour}_{nom}",
                "name": nom,
                "content": observation,
            })

        # → fin du tour : le résultat revient au LLM pour la suite du raisonnement

    _save_resultat(demande_row.id, etape, None, None, "Nombre maximal d'étapes atteint.")
    db.session.commit()
    return {"statut": "limite", "reponse": "Je n'ai pas abouti dans le nombre d'étapes autorisé (garde-fou anti-boucle).", "etapes": etapes, "demande_id": demande_row.id}