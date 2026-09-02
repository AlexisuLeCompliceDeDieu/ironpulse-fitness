import { useState } from "react";
import api from "../api.js";
import PageHero, { FIT_IMAGES } from "../components/PageHero.jsx";

const GOALS = [
  { value: "prise_masse", label: "💪 Prise de masse" },
  { value: "perte_poids", label: "🔥 Perte de poids" },
  { value: "force", label: "🏋️ Développement de la force" },
  { value: "endurance", label: "🏃 Amélioration de l'endurance" },
];

const LEVELS = [
  { value: "debutant", label: "Débutant" },
  { value: "intermediaire", label: "Intermédiaire" },
  { value: "avance", label: "Avancé" },
];

const SPLITS = [
  { value: "", label: "Automatique (selon l'objectif)" },
  { value: "full_body", label: "🧘 Full Body" },
  { value: "upper_lower", label: "🍗 Upper / Lower" },
  { value: "push_pull_legs", label: "🏋️ Push / Pull / Legs" },
  { value: "upper_lower_push_pull", label: "⚡ U/L + Push/Pull (4 j)" },
  { value: "bro_split", label: "💪 Split par muscle (5 j)" },
];

const WEEK_OPTIONS = [
  { value: "", label: "Automatique (selon le split)" },
  { value: "2", label: "2 séances / semaine" },
  { value: "3", label: "3 séances / semaine" },
  { value: "4", label: "4 séances / semaine" },
  { value: "5", label: "5 séances / semaine" },
  { value: "6", label: "6 séances / semaine" },
];

const EQUIPMENT = [
  { value: "barre", label: "Barre et poids" },
  { value: "haltères", label: "Haltères" },
  { value: "machine", label: "Machines guidées" },
  { value: "barre_fixe", label: "Barre de traction" },
  { value: "barres_parallèles", label: "Barres parallèles (dips)" },
  { value: "vélo", label: "Vélo" },
  { value: "corde", label: "Corde à sauter" },
];

const DIETARY = [
  { value: "vegetarien", label: "Végétarien" },
  { value: "vegan", label: "Végan" },
  { value: "sans_lactose", label: "Sans lactose" },
  { value: "sans_gluten", label: "Sans gluten" },
  { value: "sans_noix", label: "Sans noix" },
];

/* Petit message de confirmation affiché juste sous un bouton Enregistrer */
function SaveMessage({ text, ok }) {
  if (!text) return null;
  const isError = ok === false;
  return (
    <div
      className={isError ? "save-msg save-msg-err" : "save-msg save-msg-ok"}
      role="status"
    >
      {isError ? "⚠️ " + text : "✅ " + text}
    </div>
  );
}

/* Modale de confirmation (remplacement du poids du jour) */
function ConfirmModal({ open, onConfirm, onCancel, message }) {
  if (!open) return null;
  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-card confirm-modal" onClick={(e) => e.stopPropagation()}>
        <h3 style={{ marginTop: 0 }}>⚖️ Changer le poids du jour ?</h3>
        <p className="muted" style={{ marginTop: 0 }}>{message}</p>
        <div style={{ display: "flex", gap: "0.6rem", justifyContent: "flex-end", flexWrap: "wrap" }}>
          <button className="btn btn-secondary" onClick={onCancel}>Annuler</button>
          <button className="btn" onClick={onConfirm}>Oui, remplacer</button>
        </div>
      </div>
    </div>
  );
}

export default function Profile({ user, onUpdate }) {
  const [form, setForm] = useState({
    goal: user.goal,
    level: user.level,
    weight: user.weight,
    target_weight: user.target_weight,
    height: user.height,
    age: user.age,
    daily_calories: user.daily_calories,
    split_type: user.split_type || "",
    sessions_per_week: (user.sessions_per_week || "").toString(),
    available_equipment: user.available_equipment || [],
    dietary_preferences: user.dietary_preferences || [],
  });
  const [weightEntry, setWeightEntry] = useState("");
  const [objMsg, setObjMsg] = useState("");
  const [objOk, setObjOk] = useState(true);
  const [eqMsg, setEqMsg] = useState("");
  const [eqOk, setEqOk] = useState(true);
  const [dietMsg, setDietMsg] = useState("");
  const [dietOk, setDietOk] = useState(true);
  const [weightMsg, setWeightMsg] = useState("");
  const [weightMsgOk, setWeightMsgOk] = useState(true);
  const [confirm, setConfirm] = useState(null);

  const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const toggleEquipment = (value) => {
    const list = form.available_equipment.includes(value)
      ? form.available_equipment.filter((v) => v !== value)
      : [...form.available_equipment, value];
    setForm({ ...form, available_equipment: list });
  };

  const toggleDietary = (value) => {
    const list = form.dietary_preferences.includes(value)
      ? form.dietary_preferences.filter((v) => v !== value)
      : [...form.dietary_preferences, value];
    setForm({ ...form, dietary_preferences: list });
  };

  const save = async (section = "obj") => {
    const setMsg = (t, ok) => {
      if (section === "obj") { setObjMsg(t); setObjOk(ok); }
      else if (section === "eq") { setEqMsg(t); setEqOk(ok); }
      else { setDietMsg(t); setDietOk(ok); }
    };
    try {
      const numeric = {};
      for (const k of ["weight", "target_weight", "height", "age", "daily_calories"]) {
        numeric[k] = Number(form[k]);
      }
      const payload = { ...form, ...numeric };
      payload.split_type = form.split_type || null;
      payload.sessions_per_week = form.sessions_per_week ? Number(form.sessions_per_week) : null;
      const res = await api.put("/profile/", payload);
      onUpdate(res.data.user);
      setMsg("Profil mis à jour !", true);
      window.setTimeout(() => setMsg("", true), 3200);
    } catch (err) {
      setMsg(err.response?.data?.error || "Erreur", false);
    }
  };

  const doAddWeight = async (replacing) => {
    setConfirm(null);
    try {
      const res = await api.post("/profile/weight", { weight: Number(weightEntry) });
      setWeightEntry("");
      const action = res.data?.action;
      if (action === "replaced") {
        setWeightMsg("Poids du jour mis à jour (valeur précédente remplacée)", true);
      } else {
        setWeightMsg("Poids du jour enregistré !", true);
      }
      setWeightMsgOk(true);
      window.setTimeout(() => setWeightMsg(""), 3200);
    } catch (err) {
      setWeightMsgOk(false);
      setWeightMsg(err.response?.data?.error || "Erreur", false);
    }
  };

  const handleAddWeight = async () => {
    if (!weightEntry) return;
    setWeightMsg("");
    try {
      // Vérifier s'il existe déjà un poids aujourd'hui
      const res = await api.get("/profile/weight");
      const today = new Date().toISOString().slice(0, 10);
      const existing = (res.data.entries || []).find(
        (e) => e.date && e.date.slice(0, 10) === today
      );
      if (existing) {
        setConfirm(`Vous avez déjà enregistré ${existing.weight} kg aujourd'hui. Souhaitez-vous le remplacer par ${weightEntry} kg ?`);
        return;
      }
      await doAddWeight(false);
    } catch (err) {
      setWeightMsgOk(false);
      setWeightMsg("Impossible de vérifier le poids du jour", false);
    }
  };

  const exportData = async () => {
    try {
      const res = await api.get("/profile/export");
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "mes-donnees-fitness.json";
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setWeightMsgOk(false);
      setWeightMsg("Erreur lors de l'export", false);
    }
  };

  const deleteAccount = async () => {
    const ok = window.confirm(
      "Supprimer définitivement votre compte et toutes vos données ? Cette action est irréversible."
    );
    if (!ok) return;
    try {
      await api.delete("/profile/account");
      window.location.href = "/";
    } catch (err) {
      setWeightMsgOk(false);
      setWeightMsg("Erreur lors de la suppression", false);
    }
  };

  return (
    <div className="container">
      <PageHero
        title="👤 Votre profil"
        subtitle="Gérez vos objectifs, vos données personnelles et vos préférences."
        image={FIT_IMAGES.profile}
        tags={[`👋 ${user.username}`, `🎚️ ${form.level}`, `🎯 ${(GOALS.find(g => g.value === form.goal) || {}).label || form.goal}`]}
      />

      <div className="card">
        <h3 style={{ marginTop: 0 }}>🎯 Objectifs personnels</h3>
        <div className="grid grid-2">
          <div className="form-group">
            <label>Objectif</label>
            <select name="goal" value={form.goal} onChange={onChange}>
              {GOALS.map((g) => <option key={g.value} value={g.value}>{g.label}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Niveau sportif</label>
            <select name="level" value={form.level} onChange={onChange}>
              {LEVELS.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Poids actuel (kg)</label>
            <input name="weight" type="number" value={form.weight} onChange={onChange} />
          </div>
          <div className="form-group">
            <label>Poids cible (kg)</label>
            <input name="target_weight" type="number" value={form.target_weight} onChange={onChange} />
          </div>
          <div className="form-group">
            <label>Taille (cm)</label>
            <input name="height" type="number" value={form.height} onChange={onChange} />
          </div>
          <div className="form-group">
            <label>Âge</label>
            <input name="age" type="number" value={form.age} onChange={onChange} />
          </div>
          <div className="form-group">
            <label>Calories quotidiennes (kcal)</label>
            <input name="daily_calories" type="number" value={form.daily_calories} onChange={onChange} />
          </div>
          <div className="form-group">
            <label>Séances par semaine</label>
            <select name="sessions_per_week" value={form.sessions_per_week} onChange={onChange}>
              {WEEK_OPTIONS.map((w) => <option key={w.value || "auto"} value={w.value}>{w.label}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Type de séance (split)</label>
            <select name="split_type" value={form.split_type} onChange={onChange}>
              {SPLITS.map((s) => <option key={s.value || "auto"} value={s.value}>{s.label}</option>)}
            </select>
          </div>
        </div>
        <button className="btn" onClick={() => save("obj")}>💾 Enregistrer</button>
        <SaveMessage text={objMsg} ok={objOk} />
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>🧰 Matériel disponible à votre salle</h3>
        <p className="muted" style={{ fontSize: "0.85rem", margin: "0 0 0.8rem 0" }}>
          Le programme n'inclura que les exercices réalisables avec ce matériel.
        </p>
        <div className="grid grid-2">
          {EQUIPMENT.map((eq) => (
            <label key={eq.value} className="soft-card" style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontWeight: 600, padding: "0.7rem 0.9rem", borderRadius: "10px", cursor: "pointer" }}>
              <input
                type="checkbox"
                style={{ width: "20px", height: "20px", margin: 0, accentColor: "var(--primary)" }}
                checked={form.available_equipment.includes(eq.value)}
                onChange={() => toggleEquipment(eq.value)}
              />
              {eq.label}
            </label>
          ))}
        </div>
        <button className="btn btn-secondary" style={{ marginTop: "0.8rem" }} onClick={() => save("eq")}>💾 Enregistrer</button>
        <SaveMessage text={eqMsg} ok={eqOk} />
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>🥗 Préférences alimentaires</h3>
        <p className="muted" style={{ fontSize: "0.85rem", margin: "0 0 0.8rem 0" }}>
          Les repas générés excluront les aliments incompatibles.
        </p>
        <div className="grid grid-2">
          {DIETARY.map((d) => (
            <label key={d.value} className="soft-card" style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontWeight: 600, padding: "0.7rem 0.9rem", borderRadius: "10px", cursor: "pointer" }}>
              <input
                type="checkbox"
                style={{ width: "20px", height: "20px", margin: 0, accentColor: "var(--accent)" }}
                checked={form.dietary_preferences.includes(d.value)}
                onChange={() => toggleDietary(d.value)}
              />
              {d.label}
            </label>
          ))}
        </div>
        <button className="btn btn-secondary" style={{ marginTop: "0.8rem" }} onClick={() => save("diet")}>💾 Enregistrer</button>
        <SaveMessage text={dietMsg} ok={dietOk} />
      </div>

      <div className="card soft-card" data-tour="weight">
        <h3 style={{ marginTop: 0 }}>⚖️ Enregistrer mon poids du jour</h3>
        <p className="muted" style={{ fontSize: "0.85rem", margin: "0 0 0.8rem 0" }}>
          Un seul poids par jour : si vous vous êtes trompé, entrez la nouvelle valeur et elle remplacera la précédente.
        </p>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <input type="number" placeholder="Poids (kg)" value={weightEntry} onChange={(e) => setWeightEntry(e.target.value)} />
          <button className="btn btn-secondary" onClick={handleAddWeight}>Ajouter</button>
        </div>
        <SaveMessage text={weightMsg} ok={weightMsgOk} />
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>🛡️ Vos données (RGPD)</h3>
        <p className="muted" style={{ fontSize: "0.9rem" }}>
          Conformément au RGPD, vous pouvez exporter l'ensemble de vos données personnelles ou supprimer
          définitivement votre compte.
        </p>
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          <button className="btn btn-secondary" onClick={exportData}>📤 Exporter mes données</button>
          <button className="btn btn-danger" onClick={deleteAccount}>🗑️ Supprimer mon compte</button>
        </div>
      </div>

      <ConfirmModal
        open={!!confirm}
        message={confirm || ""}
        onConfirm={() => doAddWeight(true)}
        onCancel={() => setConfirm(null)}
      />
    </div>
  );
}
