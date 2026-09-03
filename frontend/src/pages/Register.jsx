import { useState } from "react";
import { Link } from "react-router-dom";
import api from "../api.js";
import { FIT_IMAGES } from "../components/PageHero.jsx";

const GOALS = [
  { value: "prise_masse", label: "💪 Prise de masse" },
  { value: "perte_poids", label: "🔥 Perte de poids" },
  { value: "force", label: "🏋️ Développement de la force" },
  { value: "endurance", label: "🏃 Amélioration de l'endurance" },
];

const LEVELS = [
  { value: "debutant", label: "Débutant" },
  { value: "intermediaire", label: "Intermédiaire" },
  { value: "avance", label: "Avancé" },
];

const SPLITS = [
  { value: "", label: "Automatique (selon l'objectif)" },
  { value: "full_body", label: "🧘 Full Body" },
  { value: "upper_lower", label: "🍗 Upper / Lower" },
  { value: "push_pull_legs", label: "🏋️ Push / Pull / Legs" },
  { value: "upper_lower_push_pull", label: "⚡ U/L + Push/Pull (4 j)" },
  { value: "bro_split", label: "💪 Split par muscle (5 j)" },
];

const WEEK_OPTIONS = [
  { value: "", label: "Automatique (selon le split)" },
  { value: "2", label: "2 séances / semaine" },
  { value: "3", label: "3 séances / semaine" },
  { value: "4", label: "4 séances / semaine" },
  { value: "5", label: "5 séances / semaine" },
  { value: "6", label: "6 séances / semaine" },
];

export default function Register({ onAuth }) {
  const [form, setForm] = useState({
    username: "",
    email: "",
    password: "",
    age: "",
    weight: "",
    target_weight: "",
    height: "",
    sessions_per_week: "",
    goal: "prise_masse",
    level: "debutant",
    split_type: "",
    daily_calories: "2500",
  });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    const payload = { ...form };
    for (const k of ["age", "weight", "target_weight", "height", "daily_calories"]) {
      payload[k] = form[k] === "" ? null : Number(form[k]);
    }
    payload.sessions_per_week = form.sessions_per_week ? Number(form.sessions_per_week) : null;
    payload.split_type = form.split_type || null;
    try {
      const res = await api.post("/auth/register", payload);
      // On force le guide d'introduction juste après l'inscription (PC + mobile)
      try {
        localStorage.removeItem("ironpulse_tour_done_v2");
        sessionStorage.setItem("ironpulse_just_registered", "1");
      } catch (e) {}
      onAuth(res.data.user);
    } catch (err) {
      setError(err.response?.data?.error || "Erreur d'inscription");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-side">
        <img src={FIT_IMAGES.auth} alt="" />
        <div className="overlay">
          <h2>🔥 Musclez vos résultats</h2>
          <p>
            Un coach IA qui s'adapte à votre niveau, votre matériel et vos objectifs. Bienvenue.
          </p>
        </div>
      </div>
      <div className="auth-main">
        <form className="auth-card auth-card-wide" onSubmit={submit}>
          <div className="auth-brand">
            <span className="brand-mark">💪</span>
            <span className="brand-name" style={{ fontSize: "1.6rem", fontWeight: 800 }}>
              IRONPULSE
            </span>
          </div>
          <h1>Inscription</h1>
          <p className="auth-sub">Créez votre compte et complétez votre profil en quelques étapes</p>
          {error && <div className="error">{error}</div>}

          <div className="form-section">
            <div className="form-section-title">👤 Votre compte</div>
            <div className="form-group">
              <label>Nom d'utilisateur</label>
              <input name="username" value={form.username} onChange={onChange} required placeholder="Alex" autoComplete="username" />
            </div>
            <div className="form-group">
              <label>Email</label>
              <input type="email" name="email" value={form.email} onChange={onChange} required placeholder="vous@exemple.com" autoComplete="email" />
            </div>
            <div className="form-group">
              <label>Mot de passe</label>
              <input type="password" name="password" value={form.password} onChange={onChange} required placeholder="••••••••" autoComplete="new-password" />
            </div>
          </div>

          <div className="form-section">
            <div className="form-section-title">📏 Vos informations</div>
            <div className="grid grid-2">
              <div className="form-group">
                <label>Âge</label>
                <input type="number" name="age" value={form.age} onChange={onChange} placeholder="ex : 21" />
              </div>
              <div className="form-group">
                <label>Poids actuel (kg)</label>
                <input type="number" name="weight" value={form.weight} onChange={onChange} placeholder="ex : 70" />
              </div>
              <div className="form-group">
                <label>Poids cible (kg)</label>
                <input type="number" name="target_weight" value={form.target_weight} onChange={onChange} placeholder="ex : 65" />
              </div>
              <div className="form-group">
                <label>Taille (cm)</label>
                <input type="number" name="height" value={form.height} onChange={onChange} placeholder="ex : 175" />
              </div>
              <div className="form-group">
                <label>Objectif</label>
                <select name="goal" value={form.goal} onChange={onChange}>
                  {GOALS.map((g) => <option key={g.value} value={g.value}>{g.label}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Niveau sportif</label>
                <select name="level" value={form.level} onChange={onChange}>
                  {LEVELS.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}
                </select>
              </div>
            </div>
          </div>

          <div className="form-section">
            <div className="form-section-title">🏋️ Vos séances</div>
            <div className="form-group">
              <label>Type de séance (split)</label>
              <select name="split_type" value={form.split_type} onChange={onChange}>
                {SPLITS.map((s) => <option key={s.value || "auto"} value={s.value}>{s.label}</option>)}
              </select>
              <small className="muted">Réglé sur "Automatique" par défaut : l'application choisit le meilleur split pour vous.</small>
            </div>
            <div className="form-group">
              <label>Séances par semaine</label>
              <select name="sessions_per_week" value={form.sessions_per_week} onChange={onChange}>
                {WEEK_OPTIONS.map((w) => <option key={w.value || "auto"} value={w.value}>{w.label}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label>Calories quotidiennes (kcal)</label>
              <input type="number" name="daily_calories" value={form.daily_calories} onChange={onChange} />
              <small className="muted">Valeur indicative par défaut, ajustable dans votre profil.</small>
            </div>
          </div>

          <button className="btn" type="submit" disabled={submitting} style={{ width: "100%", marginTop: "0.5rem" }}>
            {submitting ? "Création du compte..." : "S'inscrire"}
          </button>
          <p className="muted" style={{ textAlign: "center", marginBottom: 0 }}>
            Déjà un compte ? <Link to="/login" style={{ color: "var(--primary)", fontWeight: 700 }}>Se connecter</Link>
          </p>
        </form>
      </div>
    </div>
  );
}
