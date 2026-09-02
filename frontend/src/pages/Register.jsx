import { useState } from "react";
import { Link } from "react-router-dom";
import api from "../api.js";
import { FIT_IMAGES } from "../components/PageHero.jsx";

export default function Register({ onAuth }) {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const res = await api.post("/auth/register", { username, email, password });
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
        <form className="auth-card" onSubmit={submit}>
          <div className="auth-brand">
            <span className="brand-mark">💪</span>
            <span className="brand-name" style={{ fontSize: "1.6rem", fontWeight: 800 }}>
              IRONPULSE
            </span>
          </div>
          <h1>Inscription</h1>
          <p className="auth-sub">Créez votre compte, puis complétez votre profil</p>
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
          <button className="btn" type="submit" disabled={submitting} style={{ width: "100%" }}>
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
