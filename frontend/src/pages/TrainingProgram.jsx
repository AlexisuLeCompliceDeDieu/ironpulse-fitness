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
  prise_masse: { bg: "rgba(249,115,22,.16)", color: "#fb923c" },
  perte_poids: { bg: "rgba(251,146,60,.14)", color: "#fdba74" },
  force: { bg: "rgba(234,88,12,.16)", color: "#fb923c" },
  endurance: { bg: "rgba(253,186,116,.18)", color: "#ffedd5" },
};

const WEEK_OPTIONS = [2, 3, 4, 5, 6];

const CONSIGNES = [
  "Moins d'exercices, séances plus courtes",
  "Plus de travail sur les jambes",
  "Plus de cardio, moins de charges",
  "Garde les charges, change les exercices",
];

export default function TrainingProgram({ user }) {
  const [program, setProgram] = useState(null);
  const [presets, setPresets] = useState([]);
  const [selectedSplit, setSelectedSplit] = useState(null);
  const [daysPerWeek, setDaysPerWeek] = useState(user.sessions_per_week || 3);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [meta, setMeta] = useState(null);
  const [source, setSource] = useState("auto");
  const [iaAvailable, setIaAvailable] = useState(true);
  const [consigne, setConsigne] = useState("");

  useEffect(() => {
    api.get("/training/presets")
      .then((res) => setPresets(res.data.presets || []))
      .catch(() => setPresets([]));
    api.get("/training/program/current")
      .then((res) => setProgram(res.data.program))
      .catch(() => setProgram(null));
    api.get("/chat/status")
      .then((res) => setIaAvailable(!!res.data.groq_enabled))
      .catch(() => setIaAvailable(false));
  }, []);

  // Pré-sélection automatique depuis le profil : uniquement si un split explicite
  // a été choisi (jamais un split par objectif, pour éviter un PPL surprise).
  useEffect(() => {
    if (presets.length === 0 || selectedSplit) return;
    const fromProfileSplit = presets.find(
      (p) => p.kind === "split" && p.split_type && p.split_type === user.split_type
    );
    setSelectedSplit(fromProfileSplit || null);
  }, [presets, user.split_type]);

  const splitOptions = presets.filter((p) => p.kind === "split");
  const goalOptions = presets.filter((p) => p.kind === "goal");

  const generate = async () => {
    if (!selectedSplit) return;
    setLoading(true);
    setMessage("");
    try {
      const isSplit = selectedSplit.kind === "split";
      const res = await api.post("/training/program/generate", {
        // Un split nommé est envoyé en split_type ; un split par objectif en goal.
        // Sans cela, le split du profil peut écraser le choix du jour.
        split_type: isSplit ? selectedSplit.split_type : undefined,
        goal: isSplit ? undefined : selectedSplit.goal,
        days_per_week: daysPerWeek,
        source,
        consigne: consigne.trim() || undefined,
      });
      setMessage(res.data.message);
      setProgram(res.data.program);
      setMeta(res.data.meta || null);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (e) {
      setMessage(e.response?.data?.error || "Erreur");
    } finally {
      setLoading(false);
    }
  };

  const regenerate = async () => {
    setLoading(true);
    setMessage("");
    try {
      const res = await api.post("/training/program/regenerate", {
        source,
        consigne: consigne.trim() || undefined,
      });
      setMessage(res.data.message);
      setProgram(res.data.program);
      setMeta(res.data.meta || null);
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
          title="🏋️ Votre programme personnalisé"
          subtitle="Généré directement depuis votre profil : objectif, niveau, matériel et séances par semaine. Vous pouvez ajuster le split ci-dessous."
          image={FIT_IMAGES.training}
          tags={[`🎚️ Niveau : ${user.level}`, `🎯 ${goalMetaLabel(user.goal)}`, `📆 ${daysPerWeek} séances/semaine`]}
        />

        <div className="card" style={{ marginTop: "1rem" }}>
          <p style={{ margin: 0, fontSize: "0.95rem" }}>
            {user.split_type ? (
              <>✅ <strong>Le split est pré-rempli depuis votre profil.</strong> Cliquez simplement sur « ⚡ Générer mon programme » en bas, ou changez de type de séance ci-dessous.</>
            ) : (
              <>👆 <strong>Choisissez votre type de séance ci-dessous</strong> : un split précis (Upper/Lower, PPL…) ou un split automatique selon votre objectif.</>
            )}
          </p>
        </div>

        <div className="section-title">🏗️ Type de séance (split)</div>
        <div className="grid grid-2">
          {splitOptions.map((p) => (
            <div
              key={p.split_type}
              className={"goal-card" + (selectedSplit?.split_type === p.split_type ? " selected" : "")}
              onClick={() => setSelectedSplit(p)}
            >
              <div className="goal-ico" style={{ background: "var(--grad-primary)" }}>
                {p.icon}
              </div>
              <h4 style={{ margin: "0 0 0.2rem 0", fontSize: "1.1rem" }}>{p.label}</h4>
              <p className="muted" style={{ margin: "0 0 0.6rem 0", fontSize: "0.85rem" }}>
                {p.max_days} séances max / semaine
              </p>
              <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
                {p.days.map((d) => (
                  <span key={d} className="badge">{d}</span>
                ))}
              </div>
            </div>
          ))}
        </div>

        {goalOptions.length > 0 && (
          <>
            <div className="section-title">🎯 Ou selon votre objectif (automatique)</div>
            <div className="grid grid-2">
              {goalOptions.map((p) => {
                const meta = GOAL_META[p.goal] || { label: p.label, icon: "🎯", desc: "" };
                const color = GOAL_COLORS[p.goal] || {};
                return (
                  <div
                    key={p.goal}
                    className={"goal-card" + (selectedSplit?.split_type === p.goal ? " selected" : "")}
                    onClick={() => setSelectedSplit(p)}
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
          </>
        )}

        <div className="card" style={{ marginTop: "1.5rem" }}>
          <h3 style={{ marginTop: 0 }}>📆 Séances par semaine</h3>
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            {WEEK_OPTIONS.map((n) => (
              <button
                key={n}
                type="button"
                className={"chip" + (daysPerWeek === n ? " active" : "")}
                onClick={() => setDaysPerWeek(n)}
              >
                {n} séances
              </button>
            ))}
          </div>
        </div>

        <IaPanel
          source={source}
          setSource={setSource}
          consigne={consigne}
          setConsigne={setConsigne}
          iaAvailable={iaAvailable}
        />

        <button
          className="btn btn-lg"
          style={{ marginTop: "1.5rem" }}
          disabled={!selectedSplit || loading}
          onClick={generate}
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
        tags={[
          `📆 ${program.days.length} séances/semaine`,
          sourceBadge(program, meta),
        ]}
      />

      <div className="card" style={{ marginTop: "1rem" }}>
        <h3 style={{ marginTop: 0 }}>🔄 Régénérer le programme</h3>
        <p className="muted" style={{ marginTop: 0, fontSize: "0.9rem" }}>
          L'IA propose une nouvelle sélection d'exercices en tenant compte de tes
          dernières performances. Ton historique de séances est conservé.
        </p>
        <IaPanel
          source={source}
          setSource={setSource}
          consigne={consigne}
          setConsigne={setConsigne}
          iaAvailable={iaAvailable}
          compact
        />
        <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap", marginTop: "0.8rem" }}>
          <button className="btn" disabled={loading} onClick={regenerate}>
            {loading ? "⏳ Régénération..." : "🧠 Régénérer avec l'IA"}
          </button>
          <button className="btn btn-ghost" disabled={loading} onClick={() => setProgram(null)}>
            ⚙️ Changer de split
          </button>
        </div>
        {message && <p style={{ color: "var(--success)", fontWeight: 700 }}>{message}</p>}
        {meta?.raison && (
          <p className="muted" style={{ fontSize: "0.85rem", marginBottom: 0 }}>ℹ️ {meta.raison}</p>
        )}
        {meta?.avertissements?.length > 0 && (
          <details style={{ fontSize: "0.85rem" }}>
            <summary className="muted">{meta.avertissements.length} ajustement(s) appliqué(s) par l'IA</summary>
            <ul className="muted">
              {meta.avertissements.map((a, i) => <li key={i}>{a}</li>)}
            </ul>
          </details>
        )}
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

function sourceBadge(program, meta) {
  if (program.generation_source === "ia") {
    const variante = program.variation ? ` · variante ${program.variation + 1}` : "";
    const qui = meta?.fournisseur ? ` (${meta.fournisseur})` : "";
    return `🧠 Généré par l'IA${qui}${variante}`;
  }
  return "⚙️ Généré par l'algorithme";
}

function IaPanel({ source, setSource, consigne, setConsigne, iaAvailable, compact = false }) {
  return (
    <div className="card" style={compact ? { background: "var(--grad-soft)", marginTop: "0.8rem" } : { marginTop: "1.5rem" }}>
      <h3 style={{ marginTop: 0 }}>🧠 Génération</h3>
      <div className="mode-switch" style={{ marginBottom: "0.8rem" }}>
        <button
          type="button"
          className={"mode-btn" + (source === "auto" ? " active" : "")}
          onClick={() => setSource("auto")}
        >
          🧠 IA (repli auto)
        </button>
        <button
          type="button"
          className={"mode-btn" + (source === "algorithme" ? " active" : "")}
          onClick={() => setSource("algorithme")}
        >
          ⚙️ Algorithme
        </button>
      </div>
      {!iaAvailable && (
        <p className="muted" style={{ fontSize: "0.85rem", marginTop: 0 }}>
          Aucune IA configurée pour l'instant : le mode IA basculera automatiquement sur l'algorithme.
        </p>
      )}
      {source !== "algorithme" && (
        <>
          <div className="form-group" style={{ margin: 0 }}>
            <label>Consigne (optionnelle) : « plus de jambes », « séances plus courtes »…</label>
            <input
              type="text"
              value={consigne}
              maxLength={300}
              placeholder="Ex. : garde mes charges mais change les exercices"
              onChange={(e) => setConsigne(e.target.value)}
            />
          </div>
          <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap", marginTop: "0.5rem" }}>
            {CONSIGNES.map((c) => (
              <button key={c} type="button" className="chip" onClick={() => setConsigne(c)}>
                {c}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

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
  return Math.max(1, total + transitions);
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

function goalMetaLabel(goal) {
  return (GOAL_META[goal] || {}).label || goal;
}
