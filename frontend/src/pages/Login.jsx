import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../api.js";
import { FIT_IMAGES } from "../components/PageHero.jsx";

export default function Login({ onAuth }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      const res = await api.post("/auth/login", { email, password });
      onAuth(res.data.user);
      navigate("/");
    } catch (err) {
      setError(err.response?.data?.error || "Erreur de connexion");
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-side">
        <img src={FIT_IMAGES.auth} alt="" />
        <div className="overlay">
          <h2>💪 Votre progression commence ici</h2>
          <p>
            Programmes d'entraînement adaptatifs, plans nutritionnels personnalisés et suivi de
            vos performances.
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
          <h1>Connexion</h1>
          <p className="auth-sub">Retrouvez votre suivi sportif et nutritionnel</p>
          {error && <div className="error">{error}</div>}
          <div className="form-group">
            <label>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="vous@exemple.com"
            />
          </div>
          <div className="form-group">
            <label>Mot de passe</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="••••••••"
            />
          </div>
          <button className="btn" type="submit" style={{ width: "100%" }}>
            Connexion
          </button>
          <p className="muted" style={{ textAlign: "center", marginBottom: 0 }}>
            Pas de compte ? <Link to="/register" style={{ color: "var(--primary)", fontWeight: 700 }}>S'inscrire</Link>
          </p>
        </form>
      </div>
    </div>
  );
}
