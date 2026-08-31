import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../api.js";

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
    <div className="auth-wrapper">
      <form className="auth-card" onSubmit={submit}>
        <h1>IA Fitness</h1>
        {error && <div className="error">{error}</div>}
        <div className="form-group">
          <label>Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        <div className="form-group">
          <label>Mot de passe</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        <button className="btn" type="submit" style={{ width: "100%" }}>
          Connexion
        </button>
        <p className="muted" style={{ textAlign: "center", marginBottom: 0 }}>
          Pas de compte ? <Link to="/register">S'inscrire</Link>
        </p>
      </form>
    </div>
  );
}
