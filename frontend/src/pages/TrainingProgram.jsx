import { useState, useEffect } from "react";
import api from "../api.js";

export default function TrainingProgram({ user }) {
  const [program, setProgram] = useState(null);
  const [presets, setPresets] = useState([]);
  const [selectedGoal, setSelectedGoal] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    api.get("/training/presets")
      .then((res) => setPresets(res.data.presets || []))
      .catch(() => setPresets([]));
  }, []);

  const loadProgram = async () => {
    setLoading(true);
    setMessage("");
    try {
      const res = await api.get("/training/program/current");
      setProgram(res.data.program);
    } catch {
      setProgram(null);
    } finally {
      setLoading(false);
    }
  };

  const generate = async (goal) => {
    setLoading(true);
    setMessage("");
    try {
      const res = await api.post("/training/program/generate", { goal });
      setMessage(res.data.message);
      setProgram(res.data.program);
    } catch (e) {
      setMessage(e.response?.data?.error || "Erreur");
    } finally {
      setLoading(false);
    }
  };

  if (!program && !loading) {
    return (
      <div className="container">
        <h1 className="page-title">Programme d'entraînement</h1>

        <div className="card">
          <h3>Choisissez votre objectif</h3>
          <p className="muted">
            L'agent génère un programme mensuel personnalisé selon votre objectif (niveau : {user.level}).
          </p>
          <div className="grid grid-2">
            {presets.map((p) => (
              <div
                key={p.goal}
                className="card"
                style={{
                  margin: 0,
                  cursor: "pointer",
                  borderColor: selectedGoal === p.goal ? "var(--primary)" : "var(--border)",
                }}
                onClick={() => setSelectedGoal(p.goal)}
              >
                <h4 style={{ marginTop: 0 }}>{p.label}</h4>
                <p className="muted" style={{ margin: "0.25rem 0" }}>
                  {p.days_per_week} séances/semaine
                </p>
                <div style={{ fontSize: "0.85rem" }}>
                  {p.days.map((d) => (
                    <span key={d} className="badge">{d}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
          <button
            className="btn"
            style={{ marginTop: "1rem" }}
            disabled={!selectedGoal}
            onClick={() => generate(selectedGoal)}
          >
            {loading ? "Génération..." : "Générer mon programme"}
          </button>
          {message && <p style={{ marginTop: "0.75rem" }}>{message}</p>}
        </div>
      </div>
    );
  }

  if (loading) {
    return <div className="center-page">Chargement du programme...</div>;
  }

  return (
    <div className="container">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1 className="page-title">Programme : {goalLabel(program.goal)}</h1>
        <button className="btn btn-secondary" onClick={loadProgram}>Rafraîchir</button>
      </div>
      <p className="muted">
        Du {program.start_date} au {program.end_date} · {program.days.length} séances/semaine
      </p>
      {program.days.map((day) => (
        <div className="card day-card" key={day.id}>
          <h3 style={{ marginTop: 0 }}>Jour {day.day_number} : {day.name}</h3>
          {day.exercises.map((pe) => (
            <div className="exercise-row" key={pe.id}>
              <div>
                <strong>{pe.exercise.name}</strong>
                <div className="muted" style={{ fontSize: "0.85rem" }}>
                  {pe.sets} séries × {pe.reps} reps · repos {pe.rest_seconds}s ·{" "}
                  matériel : {pe.exercise.equipment_needed}
                </div>
              </div>
              <div>
                <span className="badge">{pe.target_weight > 0 ? `${pe.target_weight} kg` : "Poids libre"}</span>
              </div>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

const GOAL_LABELS = {
  prise_masse: "Prise de masse",
  perte_poids: "Perte de poids",
  force: "Développement de la force",
  endurance: "Amélioration de l'endurance",
};

function goalLabel(goal) {
  return GOAL_LABELS[goal] || goal;
}
