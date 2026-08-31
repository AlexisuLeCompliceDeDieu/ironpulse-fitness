import { useState, useEffect } from "react";
import api from "../api.js";

const GOAL_META = {
  prise_masse: { label: "Prise de masse", icon: "💪", desc: "Volume et calories pour prendre du muscle" },
  perte_poids: { label: "Perte de poids", icon: "🔥", desc: "Dépense calorique et endurance" },
  force: { label: "Développement de la force", icon: "🏋️", desc: "Charges lourdes, faible nombre de répétitions" },
  endurance: { label: "Amélioration de l'endurance", icon: "🏃", desc: "Meilleure condition physique globale" },
};

const MUSCLE_ICON = {
  pectoraux: "🫀",
  epaule: "💪",
  triceps: "💪",
  dos: "🔙",
  biceps: "💪",
  quadriceps: "🦵",
  ischio: "🦵",
  fessiers: "🍑",
  cardio: "🏃",
  core: "🧘",
};

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
        <div className="hero">
          <h1>🏋️ Votre programme</h1>
          <p>Choisissez un objectif pour générer un programme mensuel personnalisé selon votre niveau.</p>
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0 }}>Quel est votre objectif ?</h3>
          <p className="muted" style={{ marginTop: 0 }}>
            Niveau : {user.level} · {presets.length} séances prédéfinies disponibles
          </p>
          <div className="grid grid-2">
            {presets.map((p) => {
              const meta = GOAL_META[p.goal] || { label: p.label, icon: "🎯", desc: "" };
              return (
                <div
                  key={p.goal}
                  className={"goal-card" + (selectedGoal === p.goal ? " selected" : "")}
                  onClick={() => setSelectedGoal(p.goal)}
                >
                  <div className="goal-ico">{meta.icon}</div>
                  <h4 style={{ margin: "0 0 0.2rem 0" }}>{meta.label}</h4>
                  <p className="muted" style={{ margin: "0 0 0.6rem 0", fontSize: "0.85rem" }}>{meta.desc}</p>
                  <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
                    {p.days.map((d) => (
                      <span key={d} className="badge">{d}</span>
                    ))}
                  </div>
                  <p className="muted" style={{ margin: "0.6rem 0 0 0", fontSize: "0.8rem" }}>
                    {p.days_per_week} séances / semaine
                  </p>
                </div>
              );
            })}
          </div>
          <button
            className="btn"
            style={{ marginTop: "1.2rem" }}
            disabled={!selectedGoal}
            onClick={() => generate(selectedGoal)}
          >
            {loading ? "Génération..." : "⚡ Générer mon programme"}
          </button>
          {message && <p style={{ marginTop: "0.75rem", color: "var(--success)" }}>{message}</p>}
        </div>
      </div>
    );
  }

  if (loading) {
    return <div className="center-page">Chargement du programme...</div>;
  }

  return (
    <div className="container">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.5rem" }}>
        <h1 className="page-title">🗓️ Programme : {goalLabel(program.goal)}</h1>
        <button className="btn btn-secondary" onClick={loadProgram}>Rafraîchir</button>
      </div>
      <p className="muted">
        Du {program.start_date} au {program.end_date} · {program.days.length} séances/semaine
      </p>

      {program.days.map((day) => (
        <div className="card day-card" key={day.id}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.5rem" }}>
            <h3 style={{ margin: 0 }}>
              Jour {day.day_number} : {day.name}
            </h3>
            <div>
              <span className="badge badge-warn">⏱ {formatDuration(day.estimated_minutes)}</span>
              <span className="badge">{day.exercises.length} exercices</span>
            </div>
          </div>
          <div style={{ marginTop: "0.6rem" }}>
            {day.exercises.map((pe) => (
              <div className="exercise-row" key={pe.id}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.7rem" }}>
                  <span style={{ fontSize: "1.3rem" }}>
                    {MUSCLE_ICON[pe.exercise.category] || "🏋️"}
                  </span>
                  <div>
                    <strong>{pe.exercise.name}</strong>
                    <div className="muted" style={{ fontSize: "0.85rem" }}>
                      {pe.sets} séries × {pe.reps} reps · repos {pe.rest_seconds}s ·{" "}
                      matériel : {pe.exercise.equipment_needed} · ⏱ {formatDuration(exerciseMinutes(pe))}
                    </div>
                  </div>
                </div>
                <div>
                  <span className="badge badge-accent">
                    {pe.target_weight > 0 ? `${pe.target_weight} kg` : "Poids libre"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

const EFFORT_SEC_PER_REP = 3;

function exerciseMinutes(pe) {
  const effortMin = (pe.reps * EFFORT_SEC_PER_REP * pe.sets) / 60;
  const restMin = (pe.sets - 1) * (pe.rest_seconds / 60);
  return Math.max(1, effortMin + restMin);
}

function formatDuration(min) {
  const m = Math.round(min || 0);
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  const rest = m % 60;
  return rest > 0 ? `${h}h${rest}` : `${h}h`;
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
