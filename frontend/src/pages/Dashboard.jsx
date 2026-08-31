import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api.js";

const GOALS = {
  prise_masse: { label: "Prise de masse", icon: "💪" },
  perte_poids: { label: "Perte de poids", icon: "🔥" },
  force: { label: "Développement de la force", icon: "🏋️" },
  endurance: { label: "Amélioration de l'endurance", icon: "🏃" },
};

const LEVELS = {
  debutant: "Débutant",
  intermediaire: "Intermédiaire",
  avance: "Avancé",
};

export default function Dashboard({ user }) {
  const [program, setProgram] = useState(null);
  const [stats, setStats] = useState(null);
  const [advice, setAdvice] = useState([]);
  const [adaptation, setAdaptation] = useState([]);

  useEffect(() => {
    api.get("/training/program/current").then((res) => setProgram(res.data.program)).catch(() => setProgram(null));
    api.get("/progress/stats").then((res) => setStats(res.data)).catch(() => setStats(null));
    api.get("/progress/advice").then((res) => setAdvice(res.data.advice || [])).catch(() => setAdvice([]));
    api.get("/progress/adaptation").then((res) => setAdaptation(res.data.adaptation || [])).catch(() => setAdaptation([]));
  }, []);

  const today = new Date().getDay();
  const todayIndex = today === 0 ? 6 : today - 1;
  const todayDay = program ? program.days.find((d) => d.day_number === (todayIndex % program.days.length) + 1) : null;

  const goal = GOALS[user.goal] || { label: user.goal, icon: "🎯" };

  return (
    <div className="container">
      <div className="hero">
        <h1>Bonjour {user.username} 👋</h1>
        <p>
          Objectif : {goal.label} · Niveau : {LEVELS[user.level] || user.level}
        </p>
      </div>

      <div className="grid grid-3">
        <div className="stat-card">
          <div className="stat-ico" style={{ background: "rgba(255,92,26,.2)" }}>🎯</div>
          <div className="muted" style={{ fontSize: "0.85rem" }}>Objectif</div>
          <div className="stat-value" style={{ fontSize: "1.2rem", color: "var(--primary)" }}>
            {goal.icon} {goal.label}
          </div>
          <Link className="btn btn-secondary btn-sm" style={{ marginTop: "0.6rem" }} to="/profile">Modifier</Link>
        </div>

        <div className="stat-card">
          <div className="stat-ico" style={{ background: "rgba(56,189,248,.2)" }}>📊</div>
          <div className="muted" style={{ fontSize: "0.85rem" }}>Séances réalisées</div>
          <div className="stat-value">{stats ? stats.total_sessions : 0}</div>
          <div className="muted" style={{ fontSize: "0.85rem" }}>
            {stats ? `${stats.total_volume} kg · ressenti ${stats.avg_feeling}/5` : "Commencez à vous entraîner"}
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-ico" style={{ background: "rgba(34,197,94,.2)" }}>⚖️</div>
          <div className="muted" style={{ fontSize: "0.85rem" }}>Poids</div>
          <div className="stat-value">
            {user.weight}
            <span style={{ fontSize: "1rem", color: "var(--muted)" }}> kg</span>
          </div>
          <div className="muted" style={{ fontSize: "0.85rem" }}>
            Objectif : <span className="text-success">{user.target_weight} kg</span>
          </div>
          <Link className="btn btn-secondary btn-sm" style={{ marginTop: "0.6rem" }} to="/progress">Voir la progression</Link>
        </div>
      </div>

      <div className="gradient-card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.8rem" }}>
          <div>
            <h3 style={{ margin: "0 0 0.3rem 0" }}>
              {todayDay ? `📅 Aujourd'hui : ${todayDay.name}` : "📅 Programme de la semaine"}
            </h3>
            {todayDay ? (
              <p style={{ margin: 0 }}>
                Jour {todayDay.day_number} · {todayDay.exercises.length} exercices
                {todayDay.estimated_minutes ? ` · ⏱ ~${todayDay.estimated_minutes} min` : ""}
              </p>
            ) : (
              <p style={{ margin: 0 }}>Générez votre programme personnalisé dès maintenant.</p>
            )}
          </div>
          <Link to={todayDay ? "/training" : "/training"} className="btn btn-secondary">
            {todayDay ? "Voir le programme" : "Générer un programme"}
          </Link>
        </div>
      </div>

      {advice.length > 0 && (
        <div className="card">
          <h3>💡 Recommandations personnalisées</h3>
          {advice.map((a, i) => (
            <div
              key={i}
              style={{
                padding: "0.7rem 0.9rem",
                marginBottom: "0.5rem",
                borderRadius: "10px",
                borderLeft: "4px solid",
                borderColor:
                  a.type === "warning" ? "var(--warning)"
                  : a.type === "success" ? "var(--success)"
                  : "var(--accent-2)",
                background: "var(--card-2)",
                fontSize: "0.95rem",
              }}
            >
              {a.text}
            </div>
          ))}
        </div>
      )}

      {adaptation.length > 0 && (
        <div className="card">
          <h3>📈 Ajustement de la prochaine séance</h3>
          {adaptation.map((a, i) => (
            <div
              key={i}
              style={{
                padding: "0.7rem 0.9rem",
                marginBottom: "0.5rem",
                borderRadius: "10px",
                borderLeft: "4px solid",
                borderColor:
                  a.type === "warning" ? "var(--warning)"
                  : a.type === "success" ? "var(--success)"
                  : "var(--accent-2)",
                background: "var(--card-2)",
                fontSize: "0.95rem",
              }}
            >
              {a.text}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
