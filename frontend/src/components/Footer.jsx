import { Link } from "react-router-dom";

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-inner">
        <div>
          <div className="footer-brand">💪 IRONPULSE</div>
          <p className="muted" style={{ margin: "0.5rem 0 0 0", maxWidth: "320px" }}>
            Votre coach IA pour l'entraînement et la nutrition. Progression guidée, programmes
            adaptatifs et suivi complet.
          </p>
        </div>
        <div className="footer-col">
          <h4>Navigation</h4>
          <Link to="/">Accueil</Link>
          <Link to="/training">Mon programme</Link>
          <Link to="/session">Suivi de séance</Link>
          <Link to="/nutrition">Nutrition</Link>
        </div>
        <div className="footer-col">
          <h4>Suivi</h4>
          <Link to="/progress">Progression</Link>
          <Link to="/profile">Profil</Link>
        </div>
      </div>
      <div className="footer-inner" style={{ marginTop: "1.5rem", borderTop: "1px solid rgba(255,255,255,0.08)", paddingTop: "1rem" }}>
        <p className="muted" style={{ margin: 0, fontSize: "0.85rem" }}>
          © {new Date().getFullYear()} IRONPULSE — Projet étudiant.
        </p>
      </div>
    </footer>
  );
}
