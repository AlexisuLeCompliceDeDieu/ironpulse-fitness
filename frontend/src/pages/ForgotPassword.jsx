import { useState } from "react";
import { Link } from "react-router-dom";
import api from "../api.js";
import { FIT_IMAGES } from "../components/PageHero.jsx";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [debugPassword, setDebugPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setMessage("");
    setDebugPassword("");
    try {
      const res = await api.post("/auth/forgot-password", { email });
      setMessage(res.data.message);
      if (res.data.debug_password) {
        setDebugPassword(res.data.debug_password);
      }
      setEmail("");
    } catch (err) {
      setError(err.response?.data?.error || "Erreur lors de la demande");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-side">
        <img src={FIT_IMAGES.auth} alt="" />
        <div className="overlay">
          <h2>💪 Pas de panique</h2>
          <p>Indiquez l'email de votre compte et nous vous enverrons un nouveau mot de passe.</p>
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
          <h1>Mot de passe oublié</h1>
          <p className="auth-sub">Un nouveau mot de passe vous sera envoyé par email</p>

          {error && <div className="error">{error}</div>}
          {message && <div className="success-msg">{message}</div>}
          {debugPassword && (
            <div className="card soft-card" style={{ marginTop: "0.6rem", padding: "0.8rem" }}>
              <small className="muted" style={{ display: "block", marginBottom: "0.3rem" }}>
                Mode debug (SMTP non configuré) — nouveau mot de passe :
              </small>
              <code style={{ fontSize: "1.1rem", fontWeight: 800, color: "var(--primary)" }}>{debugPassword}</code>
            </div>
          )}

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

          <button className="btn" type="submit" style={{ width: "100%" }} disabled={loading}>
            {loading ? "⏳ Envoi..." : "✉️ Envoyer un nouveau mot de passe"}
          </button>

          <p className="muted" style={{ textAlign: "center", marginBottom: 0 }}>
            Retour à la <Link to="/login" style={{ color: "var(--primary)", fontWeight: 700 }}>connexion</Link>
          </p>
        </form>
      </div>
    </div>
  );
}