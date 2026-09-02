import { useState, useEffect } from "react";
import api from "../api.js";
import PageHero, { FIT_IMAGES } from "../components/PageHero.jsx";

const MEDALS = ["🥇", "🥈", "🥉"];

export default function Social({ user }) {
  const [leaderboard, setLeaderboard] = useState([]);
  const [flagged, setFlagged] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get("/social/leaderboard")
      .then((res) => {
        setLeaderboard(res.data.leaderboard || []);
        setFlagged(res.data.my_flagged_sessions || 0);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const formatVol = (v) => {
    const n = v || 0;
    if (n >= 1000000) return `${(n / 1000000).toFixed(1)} t`;
    if (n >= 1000) return `${(n / 1000).toFixed(1)} k`;
    return String(n);
  };

  const friendsCount = Math.max(0, leaderboard.length - 1);
  const me = (row) => (row.me ? { fontWeight: 800, color: "var(--primary)" } : {});

  return (
    <div className="container">
      <PageHero
        title="🏆 Classement entre potes"
        subtitle="Comparez vos tonnes soulevées de la semaine avec vos amis. Le volume = poids × répétitions, séances anti-triche comprises."
        image={FIT_IMAGES.progress}
        tags={["💪 Volume hebdo", `👥 ${friendsCount} ami(s)`, flagged > 0 ? `🚩 ${flagged} séance(s) signalée(s)` : "🛡️ Compte clean"]}
      />

      <div className="section-title">📊 Classement de la semaine</div>

      {loading ? (
        <p className="muted">Chargement...</p>
      ) : (
        <div className="card" style={{ padding: "0.5rem 1rem" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={thStyle}>#</th>
                <th style={thStyle}>Joueur</th>
                <th style={thStyle}>Volume (7 j)</th>
                <th style={thStyle}>Séances</th>
                <th style={thStyle}>Séries</th>
              </tr>
            </thead>
            <tbody>
              {leaderboard.map((row, i) => (
                <tr key={row.user.id}>
                  <td style={tdStyle}><strong>{MEDALS[i] || `${i + 1}.`}</strong></td>
                  <td style={{ ...tdStyle, ...me(row) }}>
                    {row.user.username}
                    {row.me ? " (vous)" : ""}
                  </td>
                  <td style={tdStyle}><strong>{formatVol(row.week_volume_7d)}</strong></td>
                  <td style={tdStyle}>{row.week_sessions_7d}</td>
                  <td style={tdStyle}>{row.week_sets_7d}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {leaderboard.length === 1 && (
            <p className="muted" style={{ fontSize: "0.85rem" }}>
              Seul pour l'instant. Ajoute des potes dans l'onglet « Amis » pour lancer la compétition 💪
            </p>
          )}
        </div>
      )}

      <div className="card soft-card" style={{ marginTop: "1rem" }}>
        <h4 style={{ marginTop: 0 }}>🛡️ Anti-triche</h4>
        <p className="muted" style={{ fontSize: "0.85rem", marginBottom: 0 }}>
          Les séances suspectes ne comptent pas dans le classement : dates futures, charges déraisonnables,
          pics de volume brutaux OU trop de séances le même jour. {flagged > 0 ? `Vous avez ${flagged} séance(s) signalée(s).` : ""}
        </p>
      </div>
    </div>
  );
}

const thStyle = { textAlign: "left", borderBottom: "2px solid var(--border)", padding: "0.6rem", color: "var(--muted)" };
const tdStyle = { textAlign: "left", padding: "0.6rem", borderBottom: "1px solid rgba(255,255,255,0.06)", fontSize: "0.95rem" };