import { useState, useEffect } from "react";
import { Routes, Route, Navigate, useNavigate, useLocation } from "react-router-dom";
import api from "./api.js";
import Navbar from "./components/Navbar.jsx";
import Footer from "./components/Footer.jsx";
import InstallPrompt from "./components/InstallPrompt.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import TrainingProgram from "./pages/TrainingProgram.jsx";
import SessionLog from "./pages/SessionLog.jsx";
import Nutrition from "./pages/Nutrition.jsx";
import Progress from "./pages/Progress.jsx";
import Profile from "./pages/Profile.jsx";
import Machines from "./pages/Machines.jsx";
import Social from "./pages/Social.jsx";
import Friends from "./pages/Friends.jsx";

function Fade({ location, children }) {
  return (
    <div key={location.key} className="page-enter">
      {children}
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    api
      .get("/auth/me")
      .then((res) => setUser(res.data.user))
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  const logout = async () => {
    await api.post("/auth/logout");
    setUser(null);
    navigate("/login");
  };

  if (loading) {
    return <div className="center-page">Chargement...</div>;
  }

  const authed = user ? (
    <>
      <Navbar user={user} onLogout={logout} />
      <Fade location={location}>
        <Routes location={location}>
          <Route path="/" element={<Dashboard user={user} />} />
          <Route path="/training" element={<TrainingProgram user={user} />} />
          <Route path="/session" element={<SessionLog user={user} />} />
          <Route path="/nutrition" element={<Nutrition user={user} />} />
          <Route path="/machines" element={<Machines />} />
          <Route path="/friends" element={<Friends />} />
          <Route path="/social" element={<Social user={user} />} />
          <Route path="/progress" element={<Progress user={user} />} />
          <Route path="/profile" element={<Profile user={user} onUpdate={setUser} />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </Fade>
      <Footer />
      <InstallPrompt />
    </>
  ) : (
    <>
      <Fade location={location}>
        <Routes location={location}>
          <Route path="/login" element={<Login onAuth={setUser} />} />
          <Route path="/register" element={<Register onAuth={setUser} />} />
          <Route path="*" element={<Navigate to="/login" />} />
        </Routes>
      </Fade>
      <InstallPrompt />
    </>
  );

  return <div className="app">{authed}</div>;
}
