import { useEffect, useState, useRef } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";

export default function Navbar({ user, onLogout }) {
  const navigate = useNavigate();
  const [open, setOpen] = useState(null);
  const navRef = useRef(null);

  useEffect(() => {
    const close = (e) => {
      if (navRef.current && !navRef.current.contains(e.target)) setOpen(null);
    };
    document.addEventListener("click", close);
    return () => document.removeEventListener("click", close);
  }, []);

  const toggle = (key) => setOpen((prev) => (prev === key ? null : key));

  const logout = () => {
    onLogout();
    navigate("/login");
  };

  return (
    <nav className="navbar" ref={navRef}>
      <Link to="/" className="brand">
        <span className="brand-mark">💪</span>
        <span className="brand-name">IRONPULSE</span>
      </Link>

      <div className="nav">
        <div className="nav-item">
          <NavLink
            to="/"
            end
            className={({ isActive }) => "nav-link" + (isActive ? " active" : "")}
          >
            <span>🏠</span> Accueil
          </NavLink>
        </div>

        <div className={"nav-item" + (open === "training" ? " open" : "")} onClick={() => toggle("training")}>
          <span className="nav-link">
            <span>🏋️</span> Entraînement <span className="nav-caret">▾</span>
          </span>
          <div className="dropdown">
            <NavLink to="/training" onClick={() => setOpen(null)}>
              <span className="drop-icon">🗓️</span>
              <span>
                Mon programme
                <span className="drop-desc">Votre plan d'entraînement personnalisé</span>
              </span>
            </NavLink>
            <NavLink to="/session" onClick={() => setOpen(null)}>
              <span className="drop-icon">📋</span>
              <span>
                Suivi de séance
                <span className="drop-desc">Enregistrer charges et ressenti</span>
              </span>
            </NavLink>
          </div>
        </div>

        <div className="nav-item">
          <NavLink
            to="/nutrition"
            className={({ isActive }) => "nav-link" + (isActive ? " active" : "")}
          >
            <span>🥗</span> Nutrition
          </NavLink>
        </div>

        <div className="nav-item">
          <NavLink
            to="/machines"
            className={({ isActive }) => "nav-link" + (isActive ? " active" : "")}
          >
            <span>🏋️</span> Machines
          </NavLink>
        </div>

        <div className="nav-item">
          <NavLink
            to="/friends"
            className={({ isActive }) => "nav-link" + (isActive ? " active" : "")}
          >
            <span>👥</span> Amis
          </NavLink>
        </div>

        <div className="nav-item">
          <NavLink
            to="/social"
            className={({ isActive }) => "nav-link" + (isActive ? " active" : "")}
          >
            <span>🏆</span> Classement
          </NavLink>
        </div>

        <div className="nav-item">
          <NavLink
            to="/progress"
            className={({ isActive }) => "nav-link" + (isActive ? " active" : "")}
          >
            <span>📈</span> Progression
          </NavLink>
        </div>

        <div className="nav-item">
          <NavLink
            to="/profile"
            className={({ isActive }) => "nav-link" + (isActive ? " active" : "")}
          >
            <span>👤</span> Profil
          </NavLink>
        </div>
      </div>

      <div className="nav-user">
        <div className="avatar">{user?.username?.charAt(0)?.toUpperCase() || "U"}</div>
        <span style={{ fontWeight: 700 }}>{user?.username}</span>
        <button className="btn btn-secondary btn-sm" onClick={logout}>
          Déconnexion
        </button>
      </div>
    </nav>
  );
}
