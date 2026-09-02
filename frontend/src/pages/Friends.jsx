import { useState, useEffect } from "react";
import api from "../api.js";
import PageHero, { FIT_IMAGES } from "../components/PageHero.jsx";

export default function Friends() {
  const [friends, setFriends] = useState([]);
  const [incoming, setIncoming] = useState([]);
  const [outgoing, setOutgoing] = useState([]);
  const [friendInput, setFriendInput] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = () => {
    Promise.all([
      api.get("/social/friends").catch(() => ({ data: { friends: [] } })),
      api.get("/social/friends/requests").catch(() => ({ data: { incoming: [], outgoing: [] } })),
    ]).then(([fRes, rRes]) => {
      setFriends(fRes.data.friends || []);
      setIncoming(rRes.data.incoming || []);
      setOutgoing(rRes.data.outgoing || []);
    });
  };

  useEffect(() => {
    load();
    setLoading(false);
  }, []);

  const addFriend = async (e) => {
    e.preventDefault();
    setMessage("");
    setError("");
    if (!friendInput.trim()) return;
    try {
      const res = await api.post("/social/friends", { email: friendInput.trim() });
      setMessage(res.data.message || "✅ Demande envoyée !");
      setFriendInput("");
      load();
    } catch (err) {
      setError(err.response?.data?.error || "Erreur lors de l'ajout");
    }
  };

  const acceptFriend = async (userId) => {
    try {
      const res = await api.post("/social/friends/accept", { friend_id: userId });
      setMessage(res.data.message || "✅ Ami ajouté !");
      load();
    } catch (err) {
      setError(err.response?.data?.error || "Erreur");
    }
  };

  const declineFriend = async (userId) => {
    try {
      await api.post("/social/friends/decline", { friend_id: userId });
      load();
    } catch (err) {
      setError(err.response?.data?.error || "Erreur");
    }
  };

  const removeFriend = async (id) => {
    try {
      await api.delete(`/social/friends/${id}`);
      load();
    } catch (err) {
      setError(err.response?.data?.error || "Erreur");
    }
  };

  const cancelRequest = async (id) => {
    try {
      await api.delete(`/social/friends/${id}`);
      load();
    } catch (err) {
      setError(err.response?.data?.error || "Erreur");
    }
  };

  const formatVol = (v) => {
    const n = v || 0;
    if (n >= 1000000) return `${(n / 1000000).toFixed(1)} t`;
    if (n >= 1000) return `${(n / 1000).toFixed(1)} k`;
    return String(n);
  };

  const pendingCount = incoming.length;
  const totalTags = [`${friends.length} ami(s)`];
  if (pendingCount > 0) totalTags.unshift(`📩 ${pendingCount} demande(s)`);
  if (outgoing.length > 0) totalTags.push(`⏳ ${outgoing.length} en attente`);

  return (
    <div className="container">
      <PageHero
        title="👥 Mes amis"
        subtitle="Ajoutez vos potes pour les retrouver au classement et comparer vos progrès."
        image={FIT_IMAGES.progress}
        tags={totalTags}
      />

      {message && <div className="success-msg">{message}</div>}
      {error && <div className="error">{error}</div>}

      {/* ---------- DEMANDES REÇUES ---------- */}
      {incoming.length > 0 && (
        <>
          <div className="section-title">📩 Demandes reçues ({incoming.length})</div>
          <div className="grid grid-2" style={{ marginBottom: "1.2rem" }}>
            {incoming.map((u) => (
              <div key={u.id} className="card hoverable" style={{ margin: 0, borderLeft: "3px solid var(--primary)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "0.5rem" }}>
                  <div>
                    <strong>{u.username}</strong>
                    <div className="muted" style={{ fontSize: "0.82rem" }}>Veut devenir ton ami</div>
                  </div>
                  <div style={{ display: "flex", gap: "0.4rem" }}>
                    <button className="btn btn-sm" onClick={() => acceptFriend(u.id)} style={{ background: "var(--primary)", color: "#fff" }}>✓</button>
                    <button className="btn btn-danger btn-sm" onClick={() => declineFriend(u.id)}>✗</button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* ---------- DEMANDES ENVOYÉES ---------- */}
      {outgoing.length > 0 && (
        <>
          <div className="section-title">⏳ En attente de validation ({outgoing.length})</div>
          <div className="grid grid-2" style={{ marginBottom: "1.2rem" }}>
            {outgoing.map((u) => (
              <div key={u.id} className="card" style={{ margin: 0, opacity: 0.75, borderLeft: "3px solid #f59e0b" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "0.5rem" }}>
                  <div>
                    <strong>{u.username}</strong>
                    <div className="muted" style={{ fontSize: "0.82rem" }}>Demande envoyée</div>
                  </div>
                  <button className="btn btn-danger btn-sm" onClick={() => cancelRequest(u.id)}>Annuler</button>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* ---------- FORMULAIRE AJOUT ---------- */}
      <div className="card" style={{ marginBottom: "1.2rem" }}>
        <h3 style={{ marginTop: 0 }}>➕ Ajouter un ami</h3>
        <form onSubmit={addFriend} style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          <input
            style={{ flex: 1, minWidth: "220px", marginBottom: 0 }}
            type="text"
            placeholder="Email ou nom d'utilisateur de ton pote"
            value={friendInput}
            onChange={(e) => setFriendInput(e.target.value)}
          />
          <button className="btn" type="submit">Envoyer la demande</button>
        </form>
      </div>

      {/* ---------- AMIS VALIDÉS ---------- */}
      <div className="section-title">👥 Mes amis ({friends.length})</div>

      {loading ? (
        <p className="muted">Chargement...</p>
      ) : friends.length === 0 ? (
        <div className="empty-state">
          <div className="empty-ico">🫂</div>
          <p>Aucun ami pour le moment. Ajoute ton premier pote pour comparer vos progrès !</p>
        </div>
      ) : (
        <div className="grid grid-2">
          {friends.map((f) => (
            <div key={f.id} className="card hoverable" style={{ margin: 0, animation: `fadeUp 0.4s var(--ease)` }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "0.5rem" }}>
                <div>
                  <strong>{f.username}</strong>
                  <div className="muted" style={{ fontSize: "0.82rem" }}>
                    {f.sessions_7d} séance(s) · volume {formatVol(f.volume_7d)} / 7j
                  </div>
                </div>
                <button className="btn btn-danger btn-sm" onClick={() => removeFriend(f.id)}>Retirer</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ---------- ASTUCE ---------- */}
      <div className="card soft-card" style={{ marginTop: "1rem" }}>
        <h4 style={{ marginTop: 0 }}>💡 Astuce</h4>
        <p className="muted" style={{ fontSize: "0.85rem", marginBottom: 0 }}>
          Pour ajouter un ami, entre son email ou son pseudo : une demande de validation est envoyée.
          L'amitié n'est créée que lorsque l'autre personne accepte ta demande depuis sa page Amis.
        </p>
      </div>
    </div>
  );
}
