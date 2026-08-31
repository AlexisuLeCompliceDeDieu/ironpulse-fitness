import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../api.js";

export default function Register({ onAuth }) {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      const res = await api.post("/auth/register", { username, email, password });
      onAuth(res.data.user);
      navigate("/");
    } catch (err) {
      setError(err.response?.data?.error || "Erreur d'inscription");
    }
  };

  return (
    <div className="auth-wrapper">
      <form className="auth-card" onSubmit={submit}>
        <div className="auth-brand">
          <span className="brand-mark">💪</span>
          <span className="brand-name" style={{ fontSize: "1.6rem", fontWeight: 800 }}>Fitness IA</span>
        </div>
        <h1>Inscription</h1>
        <p className="auth-sub">Créez votre espace pour un suivi personnalisé</p>
        {error && <div className="error">{error}</div>}
        <div className="form-group">
          <label>Nom d'utilisateur</label>
          <input value={username} onChange={(e) => setUsername(e.target.value)} required />
        </div>
        <div className="form-group">
          <label>Email</label>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div className="form-group">
          <label>Mot de passe</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </div>
        <button className="btn" type="submit" style={{ width: "100%" }}>
          S'inscrire
        </button>
        <p className="muted" style={{ textAlign: "center", marginBottom: 0 }}>
          Déjà un compte ? <Link to="/login">Se connecter</Link>
        </p>
      </form>
    </div>
  );
}
