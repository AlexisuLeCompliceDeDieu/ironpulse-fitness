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

export default function Profile({ user, onUpdate }) {
  const [form, setForm] = useState({
    goal: user.goal,
    level: user.level,
    weight: user.weight,
    target_weight: user.target_weight,
    height: user.height,
    age: user.age,
    daily_calories: user.daily_calories,
    available_equipment: user.available_equipment || [],
    dietary_preferences: user.dietary_preferences || [],
  });
  const [weightEntry, setWeightEntry] = useState("");
  const [message, setMessage] = useState("");

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

  const save = async () => {
    try {
      const numeric = {};
      for (const k of ["weight", "target_weight", "height", "age", "daily_calories"]) {
        numeric[k] = Number(form[k]);
      }
      const res = await api.put("/profile/", { ...form, ...numeric });
      onUpdate(res.data.user);
      setMessage("✅ Profil mis à jour !");
    } catch (err) {
      setMessage(err.response?.data?.error || "Erreur");
    }
  };

  const addWeight = async () => {
    if (!weightEntry) return;
    try {
      await api.post("/profile/weight", { weight: Number(weightEntry) });
      setWeightEntry("");
      setMessage("✅ Poids enregistré !");
    } catch (err) {
      setMessage(err.response?.data?.error || "Erreur");
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
      setMessage(err.response?.data?.error || "Erreur lors de l'export");
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
      setMessage(err.response?.data?.error || "Erreur lors de la suppression");
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

      {message && <div className="success-msg">{message}</div>}

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
        </div>
        <button className="btn" onClick={save}>💾 Enregistrer</button>
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
        <button className="btn btn-secondary" style={{ marginTop: "0.8rem" }} onClick={save}>💾 Enregistrer</button>
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
        <button className="btn btn-secondary" style={{ marginTop: "0.8rem" }} onClick={save}>💾 Enregistrer</button>
      </div>

      <div className="card soft-card">
        <h3 style={{ marginTop: 0 }}>⚖️ Enregistrer mon poids du jour</h3>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <input type="number" placeholder="Poids (kg)" value={weightEntry} onChange={(e) => setWeightEntry(e.target.value)} />
          <button className="btn btn-secondary" onClick={addWeight}>Ajouter</button>
        </div>
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
    </div>
  );
}
