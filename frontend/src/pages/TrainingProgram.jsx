import { useState, useEffect } from "react";
import api from "../api.js";
import PageHero, { FIT_IMAGES } from "../components/PageHero.jsx";

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

const GOAL_COLORS = {
  prise_masse: { bg: "rgba(14,165,233,.14)", color: "#0284c7" },
  perte_poids: { bg: "rgba(236,72,153,.14)", color: "#db2777" },
  force: { bg: "rgba(139,92,246,.14)", color: "#7c3aed" },
  endurance: { bg: "rgba(34,211,238,.18)", color: "#0e7490" },
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
    api.get("/training/program/current")
      .then((res) => setProgram(res.data.program))
      .catch(() => setProgram(null));
  }, []);

  const generate = async (goal) => {
    setLoading(true);
    setMessage("");
    try {
      const res = await api.post("/training/program/generate", { goal });
      setMessage(res.data.message);
      setProgram(res.data.program);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (e) {
      setMessage(e.response?.data?.error || "Erreur");
    } finally {
      setLoading(false);
    }
  };

  if (!program) {
    return (
      <div className="container">
        <PageHero
          title="🏋️ Créez votre programme"
          subtitle="Choisissez un objectif pour générer un programme mensuel personnalisé selon votre niveau."
          image={FIT_IMAGES.training}
          tags={[`🎚️ Niveau : ${user.level}`, `💡 ${presets.length} programmes disponibles`]}
        />

        <div className="section-title">🎯 Quel est votre objectif ?</div>
        <div className="grid grid-2">
          {presets.map((p) => {
            const meta = GOAL_META[p.goal] || { label: p.label, icon: "🎯", desc: "" };
            const color = GOAL_COLORS[p.goal] || {};
            return (
              <div
                key={p.goal}
                className={"goal-card" + (selectedGoal === p.goal ? " selected" : "")}
                onClick={() => setSelectedGoal(p.goal)}
              >
                <div className="goal-ico" style={{ background: color.bg || "var(--grad-soft)" }}>
                  {meta.icon}
                </div>
                <h4 style={{ margin: "0 0 0.2rem 0", fontSize: "1.1rem" }}>{meta.label}</h4>
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
          className="btn btn-lg"
          style={{ marginTop: "1.5rem" }}
          disabled={!selectedGoal || loading}
          onClick={() => generate(selectedGoal)}
        >
          {loading ? "⏳ Génération..." : "⚡ Générer mon programme"}
        </button>
        {message && <p style={{ marginTop: "0.8rem", color: "var(--success)", fontWeight: 700 }}>{message}</p>}
      </div>
    );
  }

  return (
    <div className="container">
      <PageHero
        title={`🗓️ Programme : ${goalLabel(program.goal)}`}
        subtitle={`Du ${program.start_date} au ${program.end_date} · ${program.days.length} séances/semaine`}
        image={FIT_IMAGES.training}
        tags={[`📆 ${program.days.length} séances/semaine`, `💪 ${program.days.length} jours`]}
      />

      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: "1rem" }}>
        <button className="btn btn-ghost" onClick={() => setProgram(null)}>
          ⚡ Régénérer un programme
        </button>
      </div>

      {program.days.map((day) => (
        <div className="card day-card" key={day.id}>
          <div className="day-card-header">
            <h3 style={{ margin: 0, display: "flex", alignItems: "center", gap: "0.6rem" }}>
              <span className="drop-icon" style={{ fontSize: "1.3rem" }}>{goalIcon(program.goal)}</span>
              Jour {day.day_number} : {day.name}
            </h3>
            <div>
              <span className="badge badge-warn">⏱ {formatDuration(day.estimated_minutes)}</span>
              <span className="badge badge-cyan">{day.exercises.length} exercices</span>
            </div>
          </div>
          <div>
            {day.exercises.map((pe) => (
              <div className="exercise-row" key={pe.id}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.8rem" }}>
                  <span className="exercise-ico">
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
                  <span className="badge badge-pink">
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

function goalIcon(goal) {
  return (GOAL_META[goal] || {}).icon || "🏋️";
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
