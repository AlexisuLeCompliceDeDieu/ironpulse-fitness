import { useEffect, useState } from "react";
import api from "../api.js";
import PageHero, { FIT_IMAGES } from "../components/PageHero.jsx";

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

function videoUrl(name) {
  return `https://www.youtube.com/results?search_query=${encodeURIComponent(name + " exercice forme")}`;
}

function ExerciseVideo({ name }) {
  return (
    <a href={videoUrl(name)} target="_blank" rel="noreferrer" className="btn btn-ghost btn-sm" title="Voir le mouvement en vidéo">
      🎥 Vidéo
    </a>
  );
}

const FEELING_EMOJI = { 1: "😩", 2: "😓", 3: "😐", 4: "🙂", 5: "😄" };

const DIFFICULTY_OPTIONS = [
  { value: "", label: "—" },
  { value: "facile", label: "😎 Facile (+10%)" },
  { value: "moyen", label: "🙂 Moyen (+5%)" },
  { value: "difficile", label: "😤 Difficile (=" },
  { value: "impossible", label: "💀 Impossible (-10%)" },
];

const DIFFICULTY_FACTOR = {
  facile: 1.1,
  moyen: 1.05,
  difficile: 1.0,
  impossible: 0.9,
};

function roundWeight(w) {
  return Math.max(0, Math.round((w + Number.EPSILON) * 10) / 10);
}

function suggestNextWeight(weight, difficulty, reps) {
  const factor = DIFFICULTY_FACTOR[difficulty] || 1.0;
  const suggested = roundWeight((Number(weight) || 0) * factor);
  return { weight: suggested, reps };
}

export default function SessionLog() {
  const [mode, setMode] = useState("program"); // "program" | "free"
  const [program, setProgram] = useState(null);
  const [selectedDay, setSelectedDay] = useState(null);
  const [feeling, setFeeling] = useState(3);
  const [notes, setNotes] = useState("");
  const [completedSets, setCompletedSets] = useState(null);
  const [message, setMessage] = useState("");
  const [history, setHistory] = useState([]);

  // Séance libre (personnalisée)
  const [catalog, setCatalog] = useState([]);
  const [freeEx, setFreeEx] = useState([]); // [{exercise, sets:[{weight,reps,completed}]}]

  useEffect(() => {
    api.get("/training/program/current")
      .then((res) => setProgram(res.data.program))
      .catch(() => setProgram(null));
    api.get("/tracking/sessions").then((res) => setHistory(res.data.sessions)).catch(() => {});
    api.get("/exercises/")
      .then((res) => setCatalog(res.data.exercises || []))
      .catch(() => setCatalog([]));
  }, []);

  const startDay = (day) => {
    setSelectedDay(day);
    setCompletedSets(
      day.exercises.map((pe) => ({
        pe,
        sets: Array.from({ length: pe.sets }, () => ({ weight: pe.target_weight, reps: pe.reps, completed: true, difficulty: "" })),
      }))
    );
    setMessage("");
  };

  const updateSet = (exIdx, setIdx, field, value) => {
    const next = [...completedSets];
    next[exIdx].sets[setIdx][field] = field === "difficulty" ? value : Number(value);
    setCompletedSets(next);
    if (field === "difficulty") autoAdjust(exIdx, setIdx, next);
  };

  // Ajustement auto : la série suivante est pré-remplie selon le ressenti de la série courante
  const autoAdjust = (exIdx, setIdx, next) => {
    const grp = next[exIdx];
    const s = grp.sets[setIdx];
    if (!s.difficulty) return;
    const nextSet = grp.sets[setIdx + 1];
    if (nextSet) {
      const { weight, reps } = suggestNextWeight(s.weight, s.difficulty, s.reps);
      nextSet.weight = weight;
      nextSet.reps = reps;
      setCompletedSets([...next]);
    }
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

  // ---- Séance libre ----
  const addFreeExercise = (exercise) => {
    setFreeEx((prev) => [
      ...prev,
      {
        exercise,
        sets: Array.from({ length: 3 }, () => ({ weight: 0, reps: 10, completed: true, difficulty: "" })),
      },
    ]);
    setMessage("");
  };

  const removeFreeExercise = (idx) => {
    setFreeEx((prev) => prev.filter((_, i) => i !== idx));
  };

  const updateFreeSet = (exIdx, setIdx, field, value) => {
    const next = [...freeEx];
    next[exIdx].sets[setIdx][field] = field === "difficulty" ? value : Number(value);
    setFreeEx(next);
    if (field === "difficulty") {
      const s = next[exIdx].sets[setIdx];
      const nextSet = next[exIdx].sets[setIdx + 1];
      if (s.difficulty && nextSet) {
        const { weight, reps } = suggestNextWeight(s.weight, s.difficulty, s.reps);
        nextSet.weight = weight;
        nextSet.reps = reps;
        setFreeEx([...next]);
      }
    }
  };

  const addFreeSet = (exIdx) => {
    const next = [...freeEx];
    next[exIdx].sets.push({ weight: 0, reps: 10, completed: true, difficulty: "" });
    setFreeEx(next);
  };

  const removeFreeSet = (exIdx, setIdx) => {
    const next = [...freeEx];
    next[exIdx].sets = next[exIdx].sets.filter((_, i) => i !== setIdx);
    setFreeEx(next);
  };

  const submitFree = async () => {
    if (freeEx.length === 0) return;
    const sets = [];
    freeEx.forEach((grp) => {
      grp.sets.forEach((s, i) => {
        sets.push({
          exercise_id: grp.exercise.id,
          set_number: i + 1,
          weight: s.weight,
          reps: s.reps,
          completed: s.completed,
          difficulty: s.difficulty || "",
        });
      });
    });
    try {
      await api.post("/tracking/sessions", { feeling, notes, sets });
      setMessage("Séance libre enregistrée ! 🎉");
      setFreeEx([]);
      api.get("/tracking/sessions").then((r) => setHistory(r.data.sessions));
    } catch (err) {
      setMessage(err.response?.data?.error || "Erreur lors de l'enregistrement");
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
          difficulty: s.difficulty || "",
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
      setMessage("Séance enregistrée ! 🎉");
      setSelectedDay(null);
      api.get("/tracking/sessions").then((r) => setHistory(r.data.sessions));
    } catch (err) {
      setMessage(err.response?.data?.error || "Erreur lors de l'enregistrement");
    }
  };

  return (
    <div className="container">
      <PageHero
        title="📋 Suivi de séance"
        subtitle="Enregistrez vos charges, séries, répétitions et ressenti après chaque entraînement."
        image={FIT_IMAGES.dumbbell}
        tags={["🏋️ Remplissage des séries", `😴 Ressenti /5`, `📝 Notes et ajustements`]}
      />

      {message && <div className="success-msg">{message}</div>}

      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1.2rem", flexWrap: "wrap" }}>
        <button className={"chip" + (mode === "program" ? " active" : "")} onClick={() => { setMode("program"); setSelectedDay(null); }}>
          🗓️ Séance du programme
        </button>
        <button className={"chip" + (mode === "free" ? " active" : "")} onClick={() => { setMode("free"); setSelectedDay(null); }}>
          ✍️ Séance libre
        </button>
      </div>

      {mode === "free" ? (
        <div className="card" style={{ marginBottom: "1.2rem" }}>
          <h3 style={{ marginTop: 0 }}>✍️ Créer une séance libre</h3>
          <p className="muted" style={{ fontSize: "0.85rem", margin: "0 0 0.8rem 0" }}>
            Ajoutez des exercices/machines, renseignez le poids et les répétitions par série. Cette séance ponctuelle
            apparaîtra dans votre historique sans modifier votre programme mensuel.
          </p>

          <div className="form-group">
            <label>Ajouter un exercice / une machine</label>
            <select
              value=""
              onChange={(e) => {
                const ex = catalog.find((x) => String(x.id) === e.target.value);
                if (ex) addFreeExercise(ex);
              }}
            >
              <option value="">-- Choisir un exercice --</option>
              {catalog.map((ex) => (
                <option key={ex.id} value={ex.id}>
                  {ex.name} ({ex.equipment_needed})
                </option>
              ))}
            </select>
          </div>

          {freeEx.length > 0 && (
            <div>
              {freeEx.map((grp, exIdx) => (
                <div key={grp.exercise.id} style={{ marginBottom: "1.2rem", border: "1px solid var(--border)", borderRadius: "12px", padding: "0.9rem" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.5rem" }}>
                    <h4 style={{ margin: 0, display: "flex", alignItems: "center", gap: "0.5rem" }}>
                      <span className="exercise-ico">{MUSCLE_ICON[grp.exercise.category] || "🏋️"}</span>
                      {grp.exercise.name}
                      <span className="badge">{grp.exercise.equipment_needed}</span>
                    </h4>
                    <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                      <ExerciseVideo name={grp.exercise.name} />
                      <button className="btn btn-ghost btn-sm" onClick={() => removeFreeExercise(exIdx)}>🗑️ Retirer</button>
                    </div>
                  </div>
                  <table style={{ width: "100%", borderCollapse: "collapse", marginTop: "0.5rem" }}>
                    <thead>
                      <tr>
                        <th style={thStyle}>Série</th>
                        <th style={thStyle}>Poids (kg)</th>
                        <th style={thStyle}>Reps</th>
                        <th style={thStyle}>Ressenti</th>
                        <th style={thStyle}>Fait</th>
                        <th style={thStyle}></th>
                      </tr>
                    </thead>
                    <tbody>
                      {grp.sets.map((s, setIdx) => (
                        <tr key={setIdx}>
                          <td style={tdStyle}><strong>{setIdx + 1}</strong></td>
                          <td style={tdStyle}><input style={{ width: "80px" }} type="number" value={s.weight} onChange={(e) => updateFreeSet(exIdx, setIdx, "weight", e.target.value)} placeholder="kg" /></td>
                          <td style={tdStyle}><input style={{ width: "80px" }} type="number" value={s.reps} onChange={(e) => updateFreeSet(exIdx, setIdx, "reps", e.target.value)} /></td>
                          <td style={tdStyle}>
                            <select value={s.difficulty || ""} onChange={(e) => updateFreeSet(exIdx, setIdx, "difficulty", e.target.value)} style={{ width: "130px" }}>
                              {DIFFICULTY_OPTIONS.map((d) => <option key={d.value} value={d.value}>{d.label}</option>)}
                            </select>
                          </td>
                          <td style={tdStyle}><input type="checkbox" checked={s.completed} onChange={(e) => updateFreeSet(exIdx, setIdx, "completed", e.target.checked)} style={{ width: "20px", height: "20px", accentColor: "var(--primary)" }} /></td>
                          <td style={tdStyle}><button className="btn btn-ghost btn-sm" onClick={() => removeFreeSet(exIdx, setIdx)}>✖</button></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <button className="btn btn-ghost btn-sm" onClick={() => addFreeSet(exIdx)}>＋ Ajouter une série</button>
                </div>
              ))}

              <div style={{ borderTop: "1px dashed var(--border)", paddingTop: "1rem", marginTop: "0.5rem" }}>
                <div className="form-group">
                  <label>Ressenti (1 = très dur, 5 = facile)</label>
                  <select value={feeling} onChange={(e) => setFeeling(Number(e.target.value))}>
                    {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n} {FEELING_EMOJI[n]}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Notes</label>
                  <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} placeholder="Comment s'est passée la séance ?" />
                </div>
                <button className="btn btn-success btn-lg" disabled={freeEx.length === 0} onClick={submitFree}>💾 Enregistrer la séance libre</button>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div>
          {!selectedDay && (
            <div>
              <div className="section-title">🗓️ Choisir une séance du programme</div>
              {program ? (
                <div className="grid grid-2">
                  {program.days.map((day) => (
                    <button key={day.id} className="card hoverable" style={{ textAlign: "left", cursor: "pointer", border: "1.5px solid var(--border)", background: "var(--card)" }} onClick={() => startDay(day)}>
                      <h3 style={{ margin: "0 0 0.4rem 0", fontSize: "1.15rem" }}>
                        Jour {day.day_number} : {day.name}
                      </h3>
                      <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
                        <span className="badge">{day.exercises.length} exercices</span>
                        <span className="badge badge-warn">⏱ {formatDuration(day.estimated_minutes)}</span>
                      </div>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="empty-state">
                  <div className="empty-ico">🗓️</div>
                  <p>Aucun programme actif. Générez-en un depuis la page Entraînement.</p>
                </div>
              )}
            </div>
          )}

          {selectedDay && completedSets && (
            <div className="card">
              <div className="day-card-header">
                <h3 style={{ margin: 0 }}>Séance : {selectedDay.name}
                  <span className="badge badge-warn" style={{ marginLeft: "0.5rem" }}>⏱ {formatDuration(dayMinutes(selectedDay))}</span>
                </h3>
                <button className="btn btn-secondary" onClick={() => setSelectedDay(null)}>✖ Annuler</button>
              </div>

              {completedSets.map((grp, exIdx) => (
                <div key={grp.pe.id} style={{ marginBottom: "1.4rem" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.5rem" }}>
                    <h4 style={{ margin: "0.5rem 0", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                      <span className="exercise-ico">{MUSCLE_ICON[grp.pe.exercise.category] || "🏋️"}</span>
                      {grp.pe.exercise.name}
                    </h4>
                    <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                      <ExerciseVideo name={grp.pe.exercise.name} />
                      <button className="btn btn-ghost btn-sm" onClick={() => replaceExercise(exIdx)}>
                        🔄 Remplacer (matériel non dispo)
                      </button>
                    </div>
                  </div>
                  <table style={{ width: "100%", borderCollapse: "collapse" }}>
                    <thead>
                      <tr>
                        <th style={thStyle}>Série</th>
                        <th style={thStyle}>Poids (kg)</th>
                        <th style={thStyle}>Reps</th>
                        <th style={thStyle}>Ressenti</th>
                        <th style={thStyle}>Fait</th>
                      </tr>
                    </thead>
                    <tbody>
                      {grp.sets.map((s, setIdx) => (
                        <tr key={setIdx}>
                          <td style={tdStyle}><strong>{setIdx + 1}</strong></td>
                          <td style={tdStyle}><input style={{ width: "80px" }} type="number" value={s.weight} onChange={(e) => updateSet(exIdx, setIdx, "weight", e.target.value)} /></td>
                          <td style={tdStyle}><input style={{ width: "80px" }} type="number" value={s.reps} onChange={(e) => updateSet(exIdx, setIdx, "reps", e.target.value)} /></td>
                          <td style={tdStyle}>
                            <select value={s.difficulty || ""} onChange={(e) => updateSet(exIdx, setIdx, "difficulty", e.target.value)} style={{ width: "130px" }}>
                              {DIFFICULTY_OPTIONS.map((d) => <option key={d.value} value={d.value}>{d.label}</option>)}
                            </select>
                            {setIdx < grp.sets.length - 1 && s.difficulty && (
                              <div className="muted" style={{ fontSize: "0.7rem", marginTop: "2px" }}>
                                → série {setIdx + 2} : {roundWeight((Number(s.weight) || 0) * (DIFFICULTY_FACTOR[s.difficulty] || 1))} kg
                              </div>
                            )}
                          </td>
                          <td style={tdStyle}><input type="checkbox" checked={s.completed} onChange={(e) => updateSet(exIdx, setIdx, "completed", e.target.checked)} style={{ width: "20px", height: "20px", accentColor: "var(--primary)" }} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ))}

              <div style={{ borderTop: "1px dashed var(--border)", paddingTop: "1rem", marginTop: "0.5rem" }}>
                <div className="form-group">
                  <label>Ressenti (1 = très dur, 5 = facile)</label>
                  <select value={feeling} onChange={(e) => setFeeling(Number(e.target.value))}>
                    {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n} {FEELING_EMOJI[n]}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Notes</label>
                  <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} placeholder="Comment s'est passée la séance ?" />
                </div>
                <button className="btn btn-success btn-lg" onClick={submit}>💾 Enregistrer la séance</button>
              </div>
            </div>
          )}
        </div>
      )}

      <div className="card">
        <h3 style={{ marginTop: 0 }}>🗒️ Historique des séances</h3>
        {history.length === 0 ? (
          <p className="muted">Aucune séance enregistrée.</p>
        ) : (
          <div className="grid grid-2">
            {history.map((s) => (
              <div key={s.id} className="card" style={{ margin: 0 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <strong>📅 {s.date}</strong>
                  <span className="badge badge-pink">Ressenti {s.feeling}/5 {FEELING_EMOJI[s.feeling] || ""}</span>
                </div>
                <p className="muted" style={{ fontSize: "0.85rem", margin: "0.5rem 0 0 0" }}>{s.sets.length} séries enregistrées</p>
                {s.notes && <p className="muted" style={{ fontSize: "0.85rem" }}>{s.notes}</p>}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

const thStyle = { textAlign: "left", borderBottom: "2px solid var(--border)", padding: "0.5rem", color: "var(--muted)" };
const tdStyle = { textAlign: "left", padding: "0.35rem" };

const EFFORT_SEC_PER_REP = 5;   // ~5s par répétition (tempo conc. + excentrique)
const SETUP_MIN_PER_EX = 0.75;  // ~45s pour charger/régler le matériel
const WARMUP_MIN_PER_EX = 1.0;  // 1 série d'échauffement par exercice
const TRANSITION_MIN = 2.0;     // passer d'un exercice à l'autre

function exerciseMinutes(pe) {
  const effortMin = (pe.reps * EFFORT_SEC_PER_REP * pe.sets) / 60;
  const restMin = (pe.sets - 1) * (pe.rest_seconds / 60);
  return Math.max(1, effortMin + restMin + SETUP_MIN_PER_EX + WARMUP_MIN_PER_EX);
}

function dayMinutes(day) {
  const total = day.exercises.reduce((acc, pe) => acc + exerciseMinutes(pe), 0);
  const transitions = Math.max(0, day.exercises.length - 1) * TRANSITION_MIN;
  return Math.max(1, Math.round(total + transitions));
}

function formatDuration(min) {
  const m = Math.round(min);
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  const rest = m % 60;
  return rest > 0 ? `${h}h${rest}` : `${h}h`;
}
