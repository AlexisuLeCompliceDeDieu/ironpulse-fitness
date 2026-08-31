import { useState } from "react";
import api from "../api.js";

export default function TrainingProgram({ user }) {
  const [program, setProgram] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

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

  if (!program && !loading) {
    return (
      <div className="container">
        <h1 className="page-title">Programme d'entraînement</h1>
        <div className="card">
          <p className="muted">
            Générer un programme personnalisé sur un mois selon votre objectif ({user.goal}) et votre niveau ({user.level}).
          </p>
          <button className="btn" onClick={async () => {
            setLoading(true);
            try {
              const res = await api.post("/training/program/generate");
              setMessage(res.data.message);
              setProgram(res.data.program);
            } catch (e) {
              setMessage(e.response?.data?.error || "Erreur");
            } finally {
              setLoading(false);
            }
          }}>
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
        <h1 className="page-title">Programme : {program.goal}</h1>
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
