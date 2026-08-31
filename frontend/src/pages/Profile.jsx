import { useState } from "react";
import api from "../api.js";

const GOALS = [
  { value: "prise_masse", label: "Prise de masse" },
  { value: "perte_poids", label: "Perte de poids" },
  { value: "force", label: "Développement de la force" },
  { value: "endurance", label: "Amélioration de l'endurance" },
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

  const save = async () => {
    try {
      const numeric = {};
      for (const k of ["weight", "target_weight", "height", "age", "daily_calories"]) {
        numeric[k] = Number(form[k]);
      }
      const res = await api.put("/profile/", { ...form, ...numeric });
      onUpdate(res.data.user);
      setMessage("Profil mis à jour !");
    } catch (err) {
      setMessage(err.response?.data?.error || "Erreur");
    }
  };

  const addWeight = async () => {
    if (!weightEntry) return;
    try {
      await api.post("/profile/weight", { weight: Number(weightEntry) });
      setWeightEntry("");
      setMessage("Poids enregistré !");
    } catch (err) {
      setMessage(err.response?.data?.error || "Erreur");
    }
  };

  return (
    <div className="container">
      <h1 className="page-title">Profil</h1>
      {message && <div className="card">{message}</div>}

      <div className="card">
        <h3>Objectifs</h3>
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
        <div className="form-group">
          <label>Matériel disponible à votre salle</label>
          <p className="muted" style={{ fontSize: "0.85rem", margin: "0 0 0.5rem 0" }}>
            Le programme n'inclura que les exercices réalisables avec ce matériel.
          </p>
          <div className="grid grid-2">
            {EQUIPMENT.map((eq) => (
              <label key={eq.value} style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontWeight: 400 }}>
                <input
                  type="checkbox"
                  style={{ width: "auto", margin: 0 }}
                  checked={form.available_equipment.includes(eq.value)}
                  onChange={() => toggleEquipment(eq.value)}
                />
                {eq.label}
              </label>
            ))}
          </div>
        </div>
        <button className="btn" onClick={save}>Enregistrer</button>
      </div>

      <div className="card">
        <h3>Enregistrer mon poids du jour</h3>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <input type="number" placeholder="Poids (kg)" value={weightEntry} onChange={(e) => setWeightEntry(e.target.value)} />
          <button className="btn btn-secondary" onClick={addWeight}>Ajouter</button>
        </div>
      </div>
    </div>
  );
}
