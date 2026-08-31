import { useState, useEffect } from "react";
import { Routes, Route, Navigate, useNavigate } from "react-router-dom";
import api from "./api.js";
import Navbar from "./components/Navbar.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import TrainingProgram from "./pages/TrainingProgram.jsx";
import SessionLog from "./pages/SessionLog.jsx";
import Nutrition from "./pages/Nutrition.jsx";
import Progress from "./pages/Progress.jsx";
import Profile from "./pages/Profile.jsx";

export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

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

  return (
    <div className="app">
      {user && <Navbar user={user} onLogout={logout} />}
      <Routes>
        <Route
          path="/login"
          element={user ? <Navigate to="/" /> : <Login onAuth={setUser} />}
        />
        <Route
          path="/register"
          element={user ? <Navigate to="/" /> : <Register onAuth={setUser} />}
        />
        <Route path="/" element={user ? <Dashboard user={user} /> : <Navigate to="/login" />} />
        <Route path="/training" element={user ? <TrainingProgram user={user} /> : <Navigate to="/login" />} />
        <Route path="/session" element={user ? <SessionLog user={user} /> : <Navigate to="/login" />} />
        <Route path="/nutrition" element={user ? <Nutrition user={user} /> : <Navigate to="/login" />} />
        <Route path="/progress" element={user ? <Progress user={user} /> : <Navigate to="/login" />} />
        <Route path="/profile" element={user ? <Profile user={user} onUpdate={setUser} /> : <Navigate to="/login" />} />
        <Route path="*" element={<Navigate to={user ? "/" : "/login"} />} />
      </Routes>
    </div>
  );
}
