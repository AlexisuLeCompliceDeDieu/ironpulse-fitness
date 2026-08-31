import { Link } from "react-router-dom";

export default function Navbar({ user, onLogout }) {
  return (
    <nav
      style={{
        background: "var(--primary)",
        color: "#fff",
        padding: "0.8rem 1.5rem",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        flexWrap: "wrap",
        gap: "0.5rem",
      }}
    >
      <div style={{ fontWeight: 700, fontSize: "1.1rem" }}>IA Fitness</div>
      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
        <Link to="/" style={linkStyle}>Accueil</Link>
        <Link to="/training" style={linkStyle}>Entraînement</Link>
        <Link to="/session" style={linkStyle}>Séances</Link>
        <Link to="/nutrition" style={linkStyle}>Nutrition</Link>
        <Link to="/progress" style={linkStyle}>Progression</Link>
        <Link to="/profile" style={linkStyle}>Profil</Link>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: "0.8rem" }}>
        <span style={{ fontSize: "0.9rem" }}>{user?.username}</span>
        <button onClick={onLogout} className="btn btn-outline" style={{ color: "#fff", borderColor: "#fff", background: "transparent" }}>
          Déconnexion
        </button>
      </div>
    </nav>
  );
}

const linkStyle = {
  color: "#fff",
  textDecoration: "none",
  padding: "0.4rem 0.7rem",
  borderRadius: "6px",
};
