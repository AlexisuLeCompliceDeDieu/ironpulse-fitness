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

  useEffect(() => {
    api.get("/training/program/current").then((res) => setProgram(res.data.program)).catch(() => setProgram(null));
    api.get("/progress/stats").then((res) => setStats(res.data)).catch(() => setStats(null));
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
    </div>
  );
}
