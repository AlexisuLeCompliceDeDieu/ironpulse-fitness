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
  - le routeur multi-fournisseurs (Groq → Gemini → Mistral → OpenRouter) gère
    les limites de débit et bascule automatiquement en cas d'échec (diapo 18) ;
  - actions sensibles (écriture en base) soumises à validation humaine (diapo 18).

Toute demande et chaque étape de la boucle sont tracées en base (tables
demandes / resultats, `outil_utilise` rend le raisonnement auditable).

`executer_iter` est un GÉNÉRATEUR : il yield un événement à chaque étape de la
boucle (tour, appel de tool, observation, confirmation, réponse finale). C'est
ce qui permet à l'interface de montrer les tools en direct. `executer` est le
même parcours en version synchrone (utilisée par les tests et l'API classique).
"""

import inspect
import json
import logging
import time

from models import db, Demande, Resultat

from services import ai_providers

from agent.tools import TOOLS_IMPL, TOOL_SCHEMAS, SENSITIVE_TOOLS, meta_tool

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


def _completion(messages, max_tokens=900):
    """Appel LLM avec function calling via le routeur multi-fournisseurs.

    Factorisé pour être facilement mocké en test. Lève si aucun fournisseur
    n'a pu répondre (le routeur a déjà tenté tous les fournisseurs disponibles).
    """
    resultat, info = ai_providers.generate_with_tools(
        messages,
        TOOL_SCHEMAS,
        max_tokens=max_tokens,
        temperature=TEMPERATURE,
    )
    if resultat is None:
        raise RuntimeError(f"Aucun fournisseur IA n'a pu répondre ({info.get('reason')})")
    return resultat, info


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


def _args_affichage(args):
    """Arguments sans l'identifiant technique (injecté par le code, pas par le LLM)."""
    return {k: v for k, v in args.items() if k != "utilisateur_id"}


def executer_iter(utilisateur, demande, confirmation=None, demande_id=None):
    """Générateur de la boucle agent : yield un événement à chaque étape.

    Événements : debut, tour, tool_debut, tool_fin, confirmation, reponse,
    limite, quota, erreur. La valeur de retour (StopIteration.value) est le
    même dict que `executer` : {statut, reponse, etapes, ...}.
    """
    demande = (demande or "").strip()
    if not demande:
        yield {"type": "erreur", "reponse": "Demande vide."}
        return {"statut": "erreur", "reponse": "Demande vide.", "etapes": []}

    # ── Demande de trace : on réutilise la ligne existante si continuation ──
    if demande_id:
        demande_row = db.session.get(Demande, demande_id)
        if not demande_row or demande_row.utilisateur_id != utilisateur.id:
            yield {"type": "erreur", "reponse": "Demande de trace introuvable."}
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
    etapes = []

    # Tool d'écriture déjà validé par l'utilisateur (continuation de boucle)
    deja_valide = None
    if confirmation:
        nom_c = confirmation.get("tool")
        args_c = dict(confirmation.get("arguments") or {})
        args_c.setdefault("utilisateur_id", utilisateur.id)
        meta = meta_tool(nom_c)

        yield {"type": "tool_debut", "etape": etape, "outil": nom_c,
               "arguments": _args_affichage(args_c), **meta}
        t0 = time.perf_counter()
        resultat_c = _execute_tool(nom_c, args_c)
        duree_ms = int((time.perf_counter() - t0) * 1000)
        _save_resultat(demande_row.id, etape, nom_c, args_c, resultat_c)
        etapes.append({"etape": etape, "outil": nom_c, "arguments": _args_affichage(args_c),
                       "resultat": resultat_c, "resume": resultat_c.get("resume"), "duree_ms": duree_ms, **meta})
        yield {"type": "tool_fin", "etape": etape, "outil": nom_c, "resultat": resultat_c,
               "resume": resultat_c.get("resume"), "duree_ms": duree_ms, **meta}

        observation = json.dumps(resultat_c, ensure_ascii=False, default=str)
        messages.append({
            "role": "user",
            "content": (
                f"L'utilisateur a VALIDÉ l'exécution de {nom_c}. "
                f"Résultat obtenu : {observation}. Tu peux conclure ta réponse."
            ),
        })
        deja_valide = (nom_c, json.dumps(_args_affichage(args_c), sort_keys=True))
        etape += 1

    yield {"type": "debut", "demande_id": demande_row.id, "max_tours": MAX_TOURS}

    for tour in range(MAX_TOURS):
        # Garde-fou coûts : au moins un fournisseur doit être utilisable
        provider_id, provider, raison = ai_providers.available_provider()
        if provider_id is None:
            _save_resultat(demande_row.id, etape, None, None, "Aucun fournisseur IA disponible.")
            db.session.commit()
            res = {"statut": "quota",
                   "reponse": f"Aucun fournisseur IA disponible ({raison}) : clé API manquante ou quota épuisé. Réessaye plus tard.",
                   "etapes": etapes, "demande_id": demande_row.id}
            yield {"type": "quota", "reponse": res["reponse"], "etapes": etapes, "demande_id": demande_row.id}
            return res

        yield {"type": "tour", "tour": tour + 1, "max_tours": MAX_TOURS,
               "fournisseur": provider.label, "provider": provider_id}

        try:
            reponse_llm, info = _completion(messages)
        except Exception as e:  # noqa: BLE001
            logger.error(f"Appel LLM de l'agent en échec : {e}")
            db.session.commit()
            res = {"statut": "erreur", "reponse": f"Erreur d'appel IA : {str(e)[:200]}", "etapes": etapes}
            yield {"type": "erreur", "reponse": res["reponse"]}
            return res

        content = reponse_llm.get("content") or ""
        appels = reponse_llm.get("tool_calls") or []

        # Message assistant normalisé (dicts) : compatible tous fournisseurs
        messages.append({
            "role": "assistant",
            "content": content or None,
            "tool_calls": [{
                "id": tc.get("id"),
                "type": "function",
                "function": {"name": tc.get("name"), "arguments": json.dumps(tc.get("arguments") or {}, ensure_ascii=False)},
            } for tc in appels] or None,
        })

        if not appels:
            # Décision : objectif atteint, on répond
            conclusion = (content or "").strip() or "Terminé."
            _save_resultat(demande_row.id, etape, None, None, conclusion)
            db.session.commit()
            res = {"statut": "reponse", "reponse": conclusion, "etapes": etapes,
                   "demande_id": demande_row.id, "fournisseur": info.get("label"), "model": info.get("model")}
            yield {"type": "reponse", "reponse": conclusion, "etapes": etapes, "demande_id": demande_row.id,
                   "fournisseur": info.get("label"), "model": info.get("model")}
            return res

        for appel in appels:
            nom = (appel.get("name") or "").strip()
            args = appel.get("arguments") or {}
            if not isinstance(args, dict):
                args = {}
            args.setdefault("utilisateur_id", utilisateur.id)
            meta = meta_tool(nom)

            # Action sensible sans validation préalable → pause, on demande confirmation
            if nom in SENSITIVE_TOOLS and (nom, json.dumps(_args_affichage(args), sort_keys=True)) != deja_valide:
                db.session.commit()
                confirmation_data = {"tool": nom, "arguments": _args_affichage(args)}
                question = _questions_sensibles(utilisateur, nom, args)
                res = {"statut": "confirmation_requise", "reponse": question,
                       "confirmation": confirmation_data, "demande_id": demande_row.id, "etapes": etapes}
                yield {"type": "confirmation", "reponse": question, "confirmation": confirmation_data,
                       "demande_id": demande_row.id, "etapes": etapes, **meta}
                return res

            yield {"type": "tool_debut", "etape": etape, "outil": nom,
                   "arguments": _args_affichage(args), **meta}
            t0 = time.perf_counter()
            resultat = _execute_tool(nom, args)
            duree_ms = int((time.perf_counter() - t0) * 1000)
            observation = json.dumps(resultat, ensure_ascii=False, default=str)
            _save_resultat(demande_row.id, etape, nom, args, resultat)
            etapes.append({"etape": etape, "outil": nom, "arguments": _args_affichage(args),
                           "resultat": resultat, "resume": resultat.get("resume"), "duree_ms": duree_ms, **meta})
            yield {"type": "tool_fin", "etape": etape, "outil": nom, "resultat": resultat,
                   "resume": resultat.get("resume"), "duree_ms": duree_ms, **meta}
            etape += 1

            messages.append({
                "role": "tool",
                "tool_call_id": appel.get("id") or f"call_{tour}_{nom}",
                "name": nom,
                "content": observation,
            })

        # → fin du tour : le résultat revient au LLM pour la suite du raisonnement

    _save_resultat(demande_row.id, etape, None, None, "Nombre maximal d'étapes atteint.")
    db.session.commit()
    res = {"statut": "limite", "reponse": "Je n'ai pas abouti dans le nombre d'étapes autorisé (garde-fou anti-boucle).",
           "etapes": etapes, "demande_id": demande_row.id}
    yield {"type": "limite", "reponse": res["reponse"], "etapes": etapes, "demande_id": demande_row.id}
    return res


def executer(utilisateur, demande, confirmation=None, demande_id=None):
    """Version synchrone de la boucle : consomme `executer_iter` et renvoie le résultat.

    Retourne un dict :
      statut  : "reponse" | "confirmation_requise" | "limite" | "quota" | "erreur"
      reponse : texte final (si statut = reponse)
      etapes  : liste des étapes exécutées {etape, outil, arguments, resultat, resume}
    """
    generateur = executer_iter(utilisateur, demande, confirmation=confirmation, demande_id=demande_id)
    try:
        while True:
            next(generateur)
    except StopIteration as stop:
        return stop.value
