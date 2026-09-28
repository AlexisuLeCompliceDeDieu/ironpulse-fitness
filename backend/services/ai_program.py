"""Génération de programmes d'entraînement par IA, avec repli algorithmique.

Le modèle reçoit le profil de l'utilisateur, son matériel disponible, le catalogue
d'exercices, la structure du split et ses dernières performances, puis renvoie un
programme au format JSON strict. La réponse est validée et réparée avant écriture
(ids d'exercices inconnus, matériel indisponible, séries/répétitions aberrantes,
jour vide) : l'IA propose, le code valide.

La régénération est le même chemin avec deux ajouts : la consigne libre de
l'utilisateur et la liste des exercices déjà faits, pour proposer une variation
qui progressed au lieu de recommencer à zéro. L'historique des séances réalisées
n'est jamais touché (l'ancien programme est simplement désactivé).
"""

import json
import re

from services import ai_providers
from services import program_generator

TEMPERATURE = 0.7
MAX_TOKENS = 2400
MAX_EXOS_JOUR = 8
SETS_MIN, SETS_MAX = 1, 8
REPS_MIN, REPS_MAX = 3, 30
REST_MIN, REST_MAX = 30, 300
MAX_PROGRESSION_LIGNES = 18
MAX_CONSIGNE = 300

SYSTEM_PROMPT = """Tu es le coach d'entraînement d'IRONPULSE, une application de suivi sportif.

Tu conçois un programme de musculation personnalisé à partir du profil, du matériel
disponible et du catalogue d'exercices fournis.

RÈGLES ABSOLUES :
- Tu réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ni après, sans
  commentaire markdown.
- Chaque exercice doit provenir du catalogue fourni, avec son "id" exact.
- N'utilise jamais un exercice nécessitant un matériel absent de la liste.
- Le volume (séries × répétitions) doit correspondre au niveau de l'utilisateur.
- Les jours doivent suivre la structure demandée (nombre de jours et noms de séances).
- Un jour contient 3 à 6 exercices, du plus complexe au plus simple.
- Si l'utilisateur demande une variante, change réellement la sélection d'exercices
  et ajuste les charges, sans dénaturer l'objectif initial.

FORMAT ATTENDU :
{"resume": "une phrase de présentation du plan",
 "jours": [{"nom": "Nom de la séance",
            "exercices": [{"exercise_id": 12, "series": 4, "reps": 8,
                           "repos_secondes": 150, "charge_kg": 60}]}]}"""


class ErreurIAProgram(Exception):
    """Repli sur l'algorithme : l'IA n'a pas pu produire de programme exploitable."""

    def __init__(self, raison, details=""):
        super().__init__(raison)
        self.raison = raison
        self.details = details


# ── Contexte envoyé au modèle ───────────────────────────────────────

def _normaliser(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def _catalogue(user, available_equipment):
    """Exercices utilisables (matériel compatible), triés par catégorie."""
    from models import Exercise

    exercices = Exercise.query.order_by(Exercise.category, Exercise.id).all()

    def compatible(ex):
        if not available_equipment:
            return True
        if ex.equipment_needed == "aucun":
            return True
        return ex.equipment_needed in available_equipment

    return [ex for ex in exercices if compatible(ex)]


def _catalogue_texte(catalogue):
    lignes = []
    for ex in catalogue:
        lignes.append(
            f"{ex.id} | {ex.name} | {ex.category} | {ex.equipment_needed} | "
            f"{'polyarticulaire' if ex.is_compound else 'isolation'}"
        )
    return "\n".join(lignes)


def _jours_texte(day_specs):
    return "\n".join(
        f"{i + 1}. {spec['name']} — groupes travaillés : {', '.join(spec['categories'])}"
        for i, spec in enumerate(day_specs)
    )


def _progression_texte(user):
    """Dernières séries réalisées : sert à proposer des charges cohérentes."""
    from models import Exercise, Session, db

    sessions = (
        Session.query.filter_by(user_id=user.id)
        .order_by(Session.date.desc(), Session.id.desc())
        .limit(8)
        .all()
    )
    lignes = []
    for s in sessions:
        for ss in s.sets:
            ex = db.session.get(Exercise, ss.exercise_id)
            if ex is None:
                continue
            lignes.append(f"- {ex.name} : {ss.weight} kg × {ss.reps} reps le {s.date.isoformat()}")
    if not lignes:
        return "Aucune séance enregistrée pour l'instant : propose des charges de départ prudentes."
    return "\n".join(lignes[:MAX_PROGRESSION_LIGNES])


def _deja_faits_texte(programme_actif):
    if not programme_actif:
        return ""
    noms = []
    for day in programme_actif.days:
        for pe in day.exercises:
            if pe.exercise and pe.exercise.name not in noms:
                noms.append(pe.exercise.name)
    if not noms:
        return ""
    return (
        "EXERCICES DÉJÀ PRÉVUS (privilégie d'autres exercices pour la variante) :\n"
        + "\n".join(f"- {n}" for n in noms)
    )


def _profil_texte(user, ctx, day_specs, materiel):
    return (
        f"PROFIL : {user.age} ans, {user.height} cm, {user.weight} kg "
        f"(objectif {user.target_weight} kg), niveau {user.level}, objectif {ctx['goal']}.\n"
        f"MATÉRIEL DISPONIBLE : {', '.join(materiel) if materiel else 'aucun (poids du corps uniquement)'}\n"
        f"SÉANCES PAR SEMAINE : {len(day_specs)}\n"
        f"STRUCTURE DES JOURS :\n{_jours_texte(day_specs)}\n"
    )


def _construire_messages(user, ctx, day_specs, catalogue, materiel,
                          programme_actif, consigne, variation):
    blocs = [_profil_texte(user, ctx, day_specs, materiel)]
    if variation > 0:
        blocs.append(
            f"VARIANTE {variation} : c'est une REGÉNÉRATION d'un programme déjà "
            "commencé. Propose une vraie alternative (autres exercices, charges "
            "ajustées) en gardant la même structure de séances."
        )
    deja = _deja_faits_texte(programme_actif)
    if deja:
        blocs.append(deja)
    blocs.append(f"DERNIÈRES PERFORMANCES :\n{_progression_texte(user)}")
    if consigne:
        blocs.append(f"CONSIGNE DE L'UTILISATEUR (prioritaire) : {consigne[:MAX_CONSIGNE]}")
    blocs.append(
        "CATALOGUE D'EXERCICES AUTORISÉS (id | nom | catégorie | matériel | type) :\n"
        + _catalogue_texte(catalogue)
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "\n\n".join(blocs)},
    ]


# ── Lecture robuste de la réponse IA ────────────────────────────────

def _parse_reponse(content):
    """Extrait l'objet JSON du programme, même s'il est entouré de texte.

    Certains modèles sortent plusieurs objets JSON ou wrappent la réponse dans des
    balises markdown : on nettoie, puis on ramasse le premier objet contenant
    une liste de jours.
    """
    raw = (content or "").strip()
    if " thinking" in raw:
        raw = re.sub(r" thinking.*? response", "", raw, flags=re.DOTALL).strip()
    if raw.startswith("```"):
        raw = "\n".join(l for l in raw.split("\n") if not l.strip().startswith("```")).strip()
    raw = re.sub(r",\s*([\]}])", r"\1", raw)

    decoder = json.JSONDecoder()
    i = 0
    while i < len(raw):
        ch = raw[i]
        if ch in "{[":
            try:
                obj, fin = decoder.raw_decode(raw, i)
            except json.JSONDecodeError:
                i += 1
                continue
            if isinstance(obj, dict) and isinstance(obj.get("jours"), list):
                return obj
            if isinstance(obj, list) and obj and isinstance(obj[0], dict):
                return {"jours": obj}
            i = fin
        else:
            i += 1
    raise ValueError("Aucun objet JSON de programme trouvé")


# ── Validation et réparation ────────────────────────────────────────

def _borne(valeur, mini, maxi, defaut):
    try:
        v = int(round(float(valeur)))
    except (TypeError, ValueError):
        return defaut
    return max(mini, min(maxi, v))


def _texte(valeur, defaut="", maxi=300):
    """Texte court et sûr : le modèle peut renvoyer un nombre, une liste, un dict."""
    if valeur is None:
        return defaut
    if not isinstance(valeur, str):
        try:
            valeur = json.dumps(valeur, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            valeur = str(valeur)
    return valeur.strip()[:maxi] or defaut


def _charge(user, ex, prescription, valeur):
    """Charge cible : celle de l'IA si plausible, sinon estimation par niveau."""
    try:
        v = float(valeur)
    except (TypeError, ValueError):
        return program_generator.estimate_weight(user, ex, prescription)
    if v <= 0:
        return program_generator.estimate_weight(user, ex, prescription)
    plafond = (user.weight or 70.0) * (1.5 if ex.is_compound else 0.8)
    return round(min(v, plafond), 1)


def _resoudre_exercice(item, par_id, par_nom):
    """Retrouve l'exercice demandé (par id, ou par nom si le modèle s'est trompé)."""
    if not isinstance(item, dict):
        return None
    brut = item.get("exercise_id", item.get("id", item.get("exercise")))
    if brut is not None:
        try:
            ex = par_id.get(int(brut))
        except (TypeError, ValueError):
            ex = None
        if ex is not None:
            return ex
    nom = _normaliser(item.get("nom") or item.get("name") or (brut if isinstance(brut, str) else ""))
    return par_nom.get(nom)


def _valider(jours_bruts, catalogue, day_specs, user, prescription):
    """Aligne la réponse IA sur la structure attendue, exercice par exercice.

    Retourne (jours, avertissements). Chaque écart est signalé (exercice ignoré,
    jour vide, série clampée) pour être affiché à l'utilisateur.
    """
    par_id = {ex.id: ex for ex in catalogue}
    par_nom = {_normaliser(ex.name): ex for ex in catalogue}
    par_cat = {}
    for ex in catalogue:
        par_cat.setdefault(ex.category, []).append(ex)
    prescription_sets = prescription["sets"]
    prescription_reps = prescription["reps"]
    alertes = []

    def complet(category):
        """Exercice de complétion pris dans le catalogue filtré (matériel respecté)."""
        for ex in par_cat.get(category, [])[:1]:
            return {
                "exercise": ex,
                "sets": prescription_sets,
                "reps": prescription_reps,
                "rest_seconds": 150 if ex.is_compound else 90,
                "target_weight": program_generator.estimate_weight(user, ex, prescription),
            }
        return None

    jours = []
    for i, spec in enumerate(day_specs):
        brut = jours_bruts[i] if i < len(jours_bruts) else None
        brut = brut if isinstance(brut, dict) else {}
        nom = _texte(brut.get("nom") or brut.get("name"), spec["name"], 50)

        bruts = brut.get("exercices")
        if bruts is None:
            bruts = brut.get("exercises")
        if not isinstance(bruts, list):
            bruts = []

        exercices = []
        vus = set()
        for item in bruts[:MAX_EXOS_JOUR]:
            ex = _resoudre_exercice(item, par_id, par_nom)
            if ex is None:
                continue
            if ex.id in vus:
                continue
            vus.add(ex.id)
            exercices.append({
                "exercise": ex,
                "sets": _borne(item.get("series", item.get("sets", prescription_sets)), SETS_MIN, SETS_MAX, prescription_sets),
                "reps": _borne(item.get("reps", item.get("repetitions", prescription_reps)), REPS_MIN, REPS_MAX, prescription_reps),
                "rest_seconds": _borne(item.get("repos_secondes", item.get("rest_seconds", 90)), REST_MIN, REST_MAX, 90),
                "target_weight": _charge(user, ex, prescription, item.get("charge_kg", item.get("target_weight"))),
            })

        if not exercices:
            alertes.append(f"{nom} : sélection IA inutilisable, complétée par l'algorithme")
            for category in spec["categories"]:
                exo = complet(category)
                if exo:
                    exercices.append(exo)
        elif len(exercices) < 3:
            for category in spec["categories"]:
                if len(exercices) >= 3:
                    break
                exo = complet(category)
                if exo and exo["exercise"].id not in vus:
                    vus.add(exo["exercise"].id)
                    exercices.append(exo)
            if len(exercices) < 3:
                alertes.append(f"{nom} : complété à {len(exercices)} exercices")

        jours.append({"name": nom, "exercises": exercices})

    return jours, alertes


# ── Point d'entrée ──────────────────────────────────────────────────

def _programme_actif(user):
    from models import TrainingProgram
    return TrainingProgram.query.filter_by(user_id=user.id, is_active=True).order_by(TrainingProgram.id.desc()).first()


def _nb_programmes(user):
    from models import TrainingProgram
    return TrainingProgram.query.filter_by(user_id=user.id).count()


def generer_programme_ia(user, available_equipment=None, goal=None, split_type=None,
                         days_per_week=None, consigne=None, variation=None, provider_pref=None):
    """Programme proposé par l'IA, avec failover multi-fournisseurs.

    `provider_pref` : fournisseur choisi par l'utilisateur, essayé en premier.
    Lève `ErreurIAProgram` si aucun fournisseur n'est disponible ou si la réponse
    est inexploitable : l'appelant bascule alors sur l'algorithme.
    """
    ctx = program_generator.resoudre_split(user, goal, split_type, days_per_week)
    day_specs = program_generator.build_days(ctx["templates"], ctx["days_count"])
    catalogue = _catalogue(user, available_equipment or [])
    if not catalogue:
        raise ErreurIAProgram("catalogue_vide")

    programme_actif = _programme_actif(user)
    if variation is None:
        variation = _nb_programmes(user)

    messages = _construire_messages(
        user, ctx, day_specs, catalogue, available_equipment or [],
        programme_actif, consigne, variation,
    )
    texte, info = ai_providers.generate_text(
        messages, max_tokens=MAX_TOKENS, temperature=TEMPERATURE, provider_pref=provider_pref
    )
    if texte is None:
        raise ErreurIAProgram(info.get("reason", "ia_indisponible"))

    try:
        data = _parse_reponse(texte)
    except ValueError as e:
        raise ErreurIAProgram("reponse_invalide", str(e)) from e

    prescription = program_generator.LEVEL_PRESCRIPTIONS.get(
        user.level, program_generator.LEVEL_PRESCRIPTIONS["debutant"])
    jours_bruts = data.get("jours")
    if not isinstance(jours_bruts, list):
        jours_bruts = []
    jours, alertes = _valider(jours_bruts, catalogue, day_specs, user, prescription)
    if not any(j["exercises"] for j in jours):
        raise ErreurIAProgram("aucun_exercice")

    program = program_generator.creer_programme(
        user, ctx["goal"], jours, source="ia", variation=variation)
    return program, {
        "source": "ia",
        "fournisseur": info.get("label"),
        "model": info.get("model"),
        "provider": info.get("provider"),
        "variation": variation,
        "regenere": programme_actif is not None,
        "resume": _texte(data.get("resume"), "", MAX_CONSIGNE),
        "avertissements": alertes,
        "raison": None,
    }


def raison_lisible(raison):
    """Raison technique du routeur → phrase française pour l'utilisateur."""
    from services import quota_tracker
    return quota_tracker.explain(raison)


def generer_programme(user, available_equipment=None, goal=None, split_type=None,
                      days_per_week=None, consigne=None, source="auto", provider_pref=None):
    """Point d'entrée unique : IA si possible et si demandée, sinon algorithme.

    `source` : "auto" (IA avec repli), "ia" (IA obligatoire), "algorithme" (historique).
    `provider_pref` : fournisseur IA choisi par l'utilisateur (prioritaire).
    """
    if source not in ("auto", "ia", "algorithme"):
        source = "auto"

    if source in ("auto", "ia"):
        try:
            return generer_programme_ia(
                user, available_equipment, goal, split_type, days_per_week, consigne,
                provider_pref=provider_pref)
        except ErreurIAProgram as e:
            if source == "ia":
                raise
            raison_code = e.raison
            motif = f"IA indisponible ({raison_lisible(e.raison)}), programme algorithmique utilisé"
            if e.details:
                motif += f" : {e.details}"
        except Exception:  # noqa: BLE001
            if source == "ia":
                raise
            raison_code = "erreur_inattendue"
            motif = "IA indisponible (erreur inattendue), programme algorithmique utilisé"
    else:
        motif = None
        raison_code = None

    programme_actif = _programme_actif(user)
    nb_avant = _nb_programmes(user)
    program = program_generator.generate_program(
        user, available_equipment, goal=goal, split_type=split_type, days_per_week=days_per_week)
    return program, {
        "source": "algorithme",
        "fournisseur": None,
        "model": None,
        "provider": None,
        "variation": nb_avant,
        "regenere": programme_actif is not None,
        "resume": "",
        "avertissements": [],
        "raison": motif,
        "raison_code": raison_code,
    }
