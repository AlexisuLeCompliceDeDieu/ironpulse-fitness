import { Link, NavLink, useNavigate } from "react-router-dom";

const LINKS = [
  { to: "/", label: "Accueil", icon: "🏠" },
  { to: "/training", label: "Entraînement", icon: "🏋️" },
  { to: "/session", label: "Séances", icon: "📋" },
  { to: "/nutrition", label: "Nutrition", icon: "🥗" },
  { to: "/progress", label: "Progression", icon: "📈" },
  { to: "/profile", label: "Profil", icon: "👤" },
];

export default function Navbar({ user, onLogout }) {
  const navigate = useNavigate();

  const logout = () => {
    onLogout();
    navigate("/login");
  };

  return (
    <nav className="navbar">
      <Link to="/" className="brand">
        <span className="brand-mark">💪</span>
        <span className="brand-name">Fitness IA</span>
      </Link>

      <div className="nav-links">
        {LINKS.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            className={({ isActive }) => "nav-link" + (isActive ? " active" : "")}
          >
            <span>{l.icon}</span>
            <span>{l.label}</span>
          </NavLink>
        ))}
      </div>

      <div className="nav-user">
        <div className="avatar">{user?.username?.charAt(0)?.toUpperCase() || "U"}</div>
        <span style={{ fontWeight: 600 }}>{user?.username}</span>
        <button className="btn btn-secondary btn-sm" onClick={logout}>
          Déconnexion
        </button>
      </div>
    </nav>
  );
}
