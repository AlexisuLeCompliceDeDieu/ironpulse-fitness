import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api.js";
import PageHero, { FIT_IMAGES } from "../components/PageHero.jsx";

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

const WEEKDAYS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"];

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
      <PageHero
        title={`Bonjour ${user.username} 👋`}
        subtitle={`Objectif : ${goal.label} · Niveau : ${LEVELS[user.level] || user.level}`}
        image={FIT_IMAGES.hero}
        tags={[`${goal.icon} ${goal.label}`, `🎚️ ${LEVELS[user.level] || user.level}`]}
      />

      <div className="feat-strip">
        <div className="feat-tile">
          <div className="feat-ico">🎯</div>
          <h4>{goal.icon} Objectif</h4>
          <p>{goal.label}</p>
          <Link to="/profile" className="btn btn-ghost btn-sm" style={{ marginTop: "0.6rem" }}>Modifier</Link>
        </div>
        <div className="feat-tile">
          <div className="feat-ico">📊</div>
          <h4>Séances réalisées</h4>
          <p style={{ fontSize: "1.6rem", fontWeight: 800, color: "var(--primary)", margin: "0.2rem 0" }}>
            {stats ? stats.total_sessions : 0}
          </p>
          <p className="muted" style={{ fontSize: "0.8rem" }}>
            {stats ? `${stats.total_volume} kg · ressenti ${stats.avg_feeling}/5` : "Commencez à vous entraîner"}
          </p>
        </div>
        <div className="feat-tile">
          <div className="feat-ico">⚖️</div>
          <h4>Poids</h4>
          <p style={{ fontSize: "1.6rem", fontWeight: 800, color: "var(--accent-dark)", margin: "0.2rem 0" }}>
            {user.weight} <span style={{ fontSize: "1rem" }}>kg</span>
          </p>
          <p className="muted" style={{ fontSize: "0.8rem" }}>
            Objectif : <span className="text-success">{user.target_weight} kg</span>
          </p>
        </div>
      </div>

      <div className="gradient-card card" data-tour="today">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.8rem" }}>
          <div>
            <h3 style={{ margin: "0 0 0.3rem 0" }}>
              {todayDay ? `📅 Aujourd'hui — ${todayDay.name}` : "📅 Programme de la semaine"}
            </h3>
            {todayDay ? (
              <p style={{ margin: 0 }}>
                {WEEKDAYS[todayIndex]} · {todayDay.exercises.length} exercices
                {todayDay.estimated_minutes ? ` · ⏱ ~${todayDay.estimated_minutes} min` : ""}
              </p>
            ) : (
              <p style={{ margin: 0 }}>Générez votre programme personnalisé dès maintenant.</p>
            )}
          </div>
          <Link to="/training" className="btn">
            {todayDay ? "Voir le programme" : "⚡ Générer un programme"}
          </Link>
        </div>
      </div>

      {advice.length > 0 && (
        <div className="card hoverable">
          <h3 style={{ marginTop: 0 }}>💡 Recommandations personnalisées</h3>
          {advice.map((a, i) => (
            <div
              key={i}
              className="rec-card"
              style={{
                borderColor:
                  a.type === "warning" ? "var(--warning)"
                  : a.type === "success" ? "var(--success)"
                  : "var(--primary)",
              }}
            >
              {a.text}
            </div>
          ))}
        </div>
      )}

      {adaptation.length > 0 && (
        <div className="card hoverable">
          <h3 style={{ marginTop: 0 }}>📈 Ajustement de la prochaine séance</h3>
          {adaptation.map((a, i) => (
            <div
              key={i}
              className="rec-card"
              style={{
                borderColor:
                  a.type === "warning" ? "var(--warning)"
                  : a.type === "success" ? "var(--success)"
                  : "var(--accent)",
              }}
            >
              {a.text}
            </div>
          ))}
        </div>
      )}

      {!program && (
        <div className="empty-state">
          <div className="empty-ico">🗓️</div>
          <h3>Aucun programme actif</h3>
          <p>Générez votre programme personnalisé et commencez votre transformation.</p>
          <Link to="/training" className="btn" style={{ marginTop: "0.5rem" }}>Commencer</Link>
        </div>
      )}
    </div>
  );
}
