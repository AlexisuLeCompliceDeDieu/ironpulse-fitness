import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api.js";

const GOALS = {
  prise_masse: "Prise de masse",
  perte_poids: "Perte de poids",
  force: "Développement de la force",
  endurance: "Amélioration de l'endurance",
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

  return (
    <div className="container">
      <h1 className="page-title">Bonjour {user.username} !</h1>

      <div className="grid grid-3">
        <div className="card">
          <h3>Objectif</h3>
          <p className="muted">{GOALS[user.goal] || user.goal}</p>
          <p className="muted">Niveau : {user.level}</p>
          <Link className="btn btn-outline" to="/profile">Modifier</Link>
        </div>
        <div className="card">
          <h3>Statistiques</h3>
          {stats ? (
            <>
              <p>Séances : <strong>{stats.total_sessions}</strong></p>
              <p>Volume total : <strong>{stats.total_volume} kg</strong></p>
              <p>Ressenti moyen : <strong>{stats.avg_feeling}/5</strong></p>
            </>
          ) : (
            <p className="muted">Pas encore de statistiques.</p>
          )}
        </div>
        <div className="card">
          <h3>Progression</h3>
          <p className="muted">Poids actuel : <strong>{user.weight} kg</strong></p>
          <p className="muted">Poids cible : <strong>{user.target_weight} kg</strong></p>
          <Link className="btn btn-outline" to="/progress">Voir les graphiques</Link>
        </div>
      </div>

      <div className="card">
        <h3>Programme de la semaine</h3>
        {todayDay ? (
          <>
            <p><strong>Jour {todayDay.day_number} : {todayDay.name}</strong></p>
            <p className="muted">{todayDay.exercises.length} exercices à réaliser</p>
            <Link className="btn" to="/training">Voir le programme</Link>
          </>
        ) : (
          <>
            <p className="muted">Aucun programme actif pour aujourd'hui.</p>
            <Link className="btn" to="/training">Générer un programme</Link>
          </>
        )}
      </div>

      {advice.length > 0 && (
        <div className="card">
          <h3>💡 Recommandations personnalisées</h3>
          {advice.map((a, i) => (
            <div
              key={i}
              style={{
                padding: "0.6rem 0.8rem",
                marginBottom: "0.5rem",
                borderRadius: "8px",
                borderLeft: "4px solid",
                borderColor:
                  a.type === "warning" ? "var(--danger)"
                  : a.type === "success" ? "var(--success)"
                  : "var(--primary)",
                background: "var(--bg)",
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
                padding: "0.6rem 0.8rem",
                marginBottom: "0.5rem",
                borderRadius: "8px",
                borderLeft: "4px solid",
                borderColor:
                  a.type === "warning" ? "var(--danger)"
                  : a.type === "success" ? "var(--success)"
                  : "var(--primary)",
                background: "var(--bg)",
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
