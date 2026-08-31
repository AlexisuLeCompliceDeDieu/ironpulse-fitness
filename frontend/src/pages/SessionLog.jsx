import { useEffect, useState } from "react";
import api from "../api.js";

export default function SessionLog() {
  const [program, setProgram] = useState(null);
  const [selectedDay, setSelectedDay] = useState(null);
  const [feeling, setFeeling] = useState(3);
  const [notes, setNotes] = useState("");
  const [completedSets, setCompletedSets] = useState(null);
  const [message, setMessage] = useState("");
  const [history, setHistory] = useState([]);

  useEffect(() => {
    api.get("/training/program/current")
      .then((res) => setProgram(res.data.program))
      .catch(() => setProgram(null));
    api.get("/tracking/sessions").then((res) => setHistory(res.data.sessions)).catch(() => {});
  }, []);

  const startDay = (day) => {
    setSelectedDay(day);
    setCompletedSets(
      day.exercises.map((pe) => ({
        pe,
        sets: Array.from({ length: pe.sets }, () => ({ weight: pe.target_weight, reps: pe.reps, completed: true })),
      }))
    );
    setMessage("");
  };

  const updateSet = (exIdx, setIdx, field, value) => {
    const next = [...completedSets];
    next[exIdx].sets[setIdx][field] = Number(value);
    setCompletedSets(next);
  };

  const replaceExercise = async (exIdx) => {
    const grp = completedSets[exIdx];
    if (!grp) return;
    try {
      const res = await api.post(`/training/exercises/${grp.pe.exercise.id}/alternative`, {
        available_equipment: [],
      });
      const alternative = res.data.alternative;
      const next = [...completedSets];
      next[exIdx] = {
        ...grp,
        pe: {
          ...grp.pe,
          exercise: { ...grp.pe.exercise, name: `${grp.pe.exercise.name} → ${alternative.name}`, id: alternative.id },
        },
      };
      setCompletedSets(next);
      setMessage(`Exercice remplacé par : ${alternative.name}`);
    } catch (err) {
      setMessage(err.response?.data?.error || "Aucune alternative disponible");
    }
  };

  const submit = async () => {
    if (!selectedDay || !completedSets) return;
    const sets = [];
    completedSets.forEach((grp, exIdx) => {
      grp.sets.forEach((s, setIdx) => {
        sets.push({
          exercise_id: grp.pe.exercise.id,
          set_number: setIdx + 1,
          weight: s.weight,
          reps: s.reps,
          completed: s.completed,
        });
      });
    });
    try {
      const res = await api.post("/tracking/sessions", {
        program_day_id: selectedDay.id,
        feeling,
        notes,
        sets,
      });
      setMessage("Séance enregistrée !");
      setSelectedDay(null);
      api.get("/tracking/sessions").then((r) => setHistory(r.data.sessions));
    } catch (err) {
      setMessage(err.response?.data?.error || "Erreur lors de l'enregistrement");
    }
  };

  return (
    <div className="container">
      <h1 className="page-title">Suivi de séance</h1>

      {message && <div className="card" style={{ borderColor: "var(--success)", background: "#f0fdf4" }}>{message}</div>}

      {!selectedDay && (
        <div className="card">
          <h3>Choisir une séance du programme</h3>
          {program ? (
            <div className="grid grid-2">
              {program.days.map((day) => (
                <button key={day.id} className="btn" onClick={() => startDay(day)}>
                  Jour {day.day_number} : {day.name} ({day.exercises.length} ex. · ⏱ {formatDuration(dayMinutes(day))})
                </button>
              ))}
            </div>
          ) : (
            <p className="muted">Aucun programme actif. Générez-en un depuis la page Entraînement.</p>
          )}
        </div>
      )}

      {selectedDay && completedSets && (
        <div className="card">
          <h3>Séance : {selectedDay.name} <span className="badge">⏱ {formatDuration(dayMinutes(selectedDay))}</span>
            <button className="btn btn-secondary" style={{ float: "right" }} onClick={() => setSelectedDay(null)}>Annuler</button>
          </h3>
          {completedSets.map((grp, exIdx) => (
            <div key={grp.pe.id} style={{ marginBottom: "1.2rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h4 style={{ margin: "0.5rem 0" }}>{grp.pe.exercise.name}
                  <span className="badge" style={{ marginLeft: "0.5rem" }}>{grp.pe.exercise.equipment_needed}</span>
                  <span className="badge" style={{ marginLeft: "0.5rem" }}>⏱ {formatDuration(exerciseMinutes(grp.pe))}</span>
                </h4>
                <button className="btn btn-outline" style={{ padding: "0.3rem 0.7rem", fontSize: "0.85rem" }}
                  onClick={() => replaceExercise(exIdx)}>
                  Remplacer (matériel non dispo)
                </button>
              </div>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    <th style={thStyle}>Série</th>
                    <th style={thStyle}>Poids (kg)</th>
                    <th style={thStyle}>Reps</th>
                    <th style={thStyle}>Fait</th>
                  </tr>
                </thead>
                <tbody>
                  {grp.sets.map((s, setIdx) => (
                    <tr key={setIdx}>
                      <td style={tdStyle}>{setIdx + 1}</td>
                      <td style={tdStyle}><input style={{ width: "70px" }} type="number" value={s.weight} onChange={(e) => updateSet(exIdx, setIdx, "weight", e.target.value)} /></td>
                      <td style={tdStyle}><input style={{ width: "70px" }} type="number" value={s.reps} onChange={(e) => updateSet(exIdx, setIdx, "reps", e.target.value)} /></td>
                      <td style={tdStyle}><input type="checkbox" checked={s.completed} onChange={(e) => updateSet(exIdx, setIdx, "completed", e.target.checked)} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
          <div className="form-group">
            <label>Ressenti (1 = très dur, 5 = facile)</label>
            <select value={feeling} onChange={(e) => setFeeling(Number(e.target.value))}>
              {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Notes</label>
            <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} />
          </div>
          <button className="btn btn-success" onClick={submit}>Enregistrer la séance</button>
        </div>
      )}

      <div className="card">
        <h3>Historique des séances</h3>
        {history.length === 0 ? (
          <p className="muted">Aucune séance enregistrée.</p>
        ) : (
          <div className="grid grid-2">
            {history.map((s) => (
              <div key={s.id} className="card" style={{ margin: 0 }}>
                <strong>{s.date}</strong> · {s.sets.length} séries · {" "}
                <span className="badge">Ressenti {s.feeling}/5</span>
                {s.notes && <p className="muted" style={{ fontSize: "0.85rem" }}>{s.notes}</p>}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

const thStyle = { textAlign: "left", borderBottom: "1px solid var(--border)", padding: "0.4rem" };
const tdStyle = { textAlign: "left", padding: "0.3rem" };

const EFFORT_SEC_PER_REP = 3;
const WARMUP_MIN = 5;
const TRANSITION_MIN = 0.75;

function exerciseMinutes(pe) {
  const effortMin = (pe.reps * EFFORT_SEC_PER_REP * pe.sets) / 60;
  const restMin = (pe.sets - 1) * (pe.rest_seconds / 60);
  return Math.max(1, effortMin + restMin);
}

function dayMinutes(day) {
  const total = day.exercises.reduce((acc, pe) => acc + exerciseMinutes(pe), 0);
  const transitions = Math.max(0, day.exercises.length - 1) * TRANSITION_MIN;
  return Math.max(1, Math.round(total + transitions + WARMUP_MIN));
}

function formatDuration(min) {
  const m = Math.round(min);
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  const rest = m % 60;
  return rest > 0 ? `${h}h${rest}` : `${h}h`;
}
