import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
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

export default function Register({ onAuth }) {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [goal, setGoal] = useState("");
  const [level, setLevel] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      const res = await api.post("/auth/register", { username, email, password, goal, level });
      onAuth(res.data.user);
      navigate("/");
    } catch (err) {
      setError(err.response?.data?.error || "Erreur d'inscription");
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
        <form className="auth-card" onSubmit={submit}>
          <div className="auth-brand">
            <span className="brand-mark">💪</span>
            <span className="brand-name" style={{ fontSize: "1.6rem", fontWeight: 800 }}>
              FITNESS ALGO
            </span>
          </div>
          <h1>Inscription</h1>
          <p className="auth-sub">Créez votre espace pour un suivi personnalisé</p>
          {error && <div className="error">{error}</div>}
          <div className="form-group">
            <label>Nom d'utilisateur</label>
            <input value={username} onChange={(e) => setUsername(e.target.value)} required placeholder="Alex" />
          </div>
          <div className="form-group">
            <label>Email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required placeholder="vous@exemple.com" />
          </div>
          <div className="form-group">
            <label>Mot de passe</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required placeholder="••••••••" />
          </div>
          <div className="form-group">
            <label>Votre objectif</label>
            <select value={goal} onChange={(e) => setGoal(e.target.value)} required>
              <option value="">-- Choisir --</option>
              {GOALS.map((g) => <option key={g.value} value={g.value}>{g.label}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Votre niveau</label>
            <select value={level} onChange={(e) => setLevel(e.target.value)} required>
              <option value="">-- Choisir --</option>
              {LEVELS.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}
            </select>
          </div>
          <button className="btn" type="submit" style={{ width: "100%" }}>
            S'inscrire
          </button>
          <p className="muted" style={{ textAlign: "center", marginBottom: 0 }}>
            Déjà un compte ? <Link to="/login" style={{ color: "var(--primary)", fontWeight: 700 }}>Se connecter</Link>
          </p>
        </form>
      </div>
    </div>
  );
}
