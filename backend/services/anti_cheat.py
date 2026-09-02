"""Anti-triche du classement entre amis.

Règles simples mais efficaces pour un projet étudiant :
- Les séances datées dans le futur sont impossibles.
- Un poids de charge déraisonnable (dépassant largement le poids de corps)
  ou brutalement au-dessus de la moyenne du joueur est suspect.
- Un pic de volume > 3x la moyenne du joueur signale une fraude.
- Des séries incomplètes (reps = 0 ou non cochées) ne comptent pas dans le volume.
- Le volume est calculé en tonnes soulevées (poids x reps) pour rester simple.

Une séance "flagged" est exclue (ou marquée) dans le classement.
"""

from datetime import date

VOLUME_SPIKE_RATIO = 3.0
MAX_WEIGHT_KG = 250.0
WEIGHT_FACTOR = 2.0  # charge maximale plausible = poids de corps x ce facteur


def _raw_volume(raw_sets):
    """Volume depuis la liste brute (dicts envoyés par le client)."""
    total = 0.0
    for s in raw_sets:
        if s.get("completed", True) and (s.get("reps") or 0) > 0:
            total += (s.get("weight") or 0.0) * (s.get("reps") or 0)
    return total


def session_volume(session_obj):
    """Tonnes soulevées totales de la séance (poids x reps) — pour les séances déjà en BDD."""
    total = 0.0
    for s in session_obj.sets:
        if s.completed and s.reps and s.reps > 0:
            total += (s.weight or 0.0) * s.reps
    return total


def average_volume(user_id):
    """Volume moyen des séances précédentes (hors séance courante)."""
    from models import Session
    sessions = (
        Session.query.filter_by(user_id=user_id)
        .order_by(Session.id.desc())
        .limit(10)
        .all()
    )
    volumes = []
    for s in sessions:
        if s.id and s.date:
            volumes.append(session_volume(s))
    if not volumes:
        return 0.0
    return sum(volumes) / len(volumes)


def flag_suspicious(user, session_obj, raw_data):
    """Retourne True si la séance paraît frauduleuse.

    Utilise raw_data (dict JSON) au lieu de session_obj.sets pour éviter
    les autoflush prématurés pendant la création de séance.
    """
    # 1. Date dans le futur
    try:
        if session_obj.date and session_obj.date > date.today():
            return True
    except TypeError:
        return True

    raw_sets = raw_data.get("sets", [])
    if not raw_sets:
        return True

    # 2. Charge déraisonnable
    body_weight = user.weight or 70.0
    plausible_max = max(body_weight * WEIGHT_FACTOR, 40.0)
    for s in raw_sets:
        w = s.get("weight") or 0.0
        if w > MAX_WEIGHT_KG or w > plausible_max * 1.2:
            return True

    # 3. Pic de volume par rapport à la moyenne
    avg = average_volume(user.id)
    if avg > 0:
        vol = _raw_volume(raw_sets)
        if vol > avg * VOLUME_SPIKE_RATIO:
            return True

    # 4. Trop de séances le même jour (rythme impossible)
    from models import Session
    same_day = Session.query.filter_by(user_id=user.id, date=session_obj.date).count()
    if same_day >= 3:
        return True

    return False
