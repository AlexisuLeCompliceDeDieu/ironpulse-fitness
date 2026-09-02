import { useState, useEffect } from "react";
import api from "../api.js";
import PageHero, { FIT_IMAGES } from "../components/PageHero.jsx";

const CATEGORY = {
  pectoraux: "🫀 Pectoraux",
  epaule: "💪 Épaules",
  dos: "🔙 Dos",
  jambes: "🦵 Jambes",
  bras: "💪 Bras",
  core: "🧘 Core",
  cardio: "🏃 Cardio",
};

const CAT_ICON = {
  pectoraux: "🫀",
  epaule: "💪",
  dos: "🔙",
  jambes: "🦵",
  bras: "💪",
  core: "🧘",
  cardio: "🏃",
};

function MachineImage({ machine, large }) {
  const [failed, setFailed] = useState(false);
  if (!machine.image_url || failed) {
    return (
      <div
        className="machine-fallback"
        aria-label="Image indisponible"
        style={large ? { height: 220 } : {}}
      >
        <span>{CAT_ICON[machine.category] || "🏋️"}</span>
        <small className="muted">Reconnaissez la machine par son nom</small>
      </div>
    );
  }
  return (
    <div className="machine-img" style={large ? { height: 220 } : {}}>
      <img
        src={machine.image_url}
        alt={machine.name}
        loading="lazy"
        onError={() => setFailed(true)}
      />
    </div>
  );
}

export default function Machines() {
  const [machines, setMachines] = useState([]);
  const [brandFilter, setBrandFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get("/machines/")
      .then((res) => setMachines(res.data.machines || []))
      .catch(() => setMachines([]))
      .finally(() => setLoading(false));
  }, []);

  const brands = [...new Set(machines.map((m) => m.brand).filter(Boolean))].sort();
  const cats = [...new Set(machines.map((m) => m.category))].sort();

  const filtered = machines.filter(
    (m) =>
      (!brandFilter || m.brand === brandFilter) &&
      (!categoryFilter || m.category === categoryFilter)
  );

  return (
    <div className="container">
      <PageHero
        title="🏋️ Inventaire des machines"
        subtitle="Toutes les machines de la salle, avec leur code QR et les réglages selon votre morphologie."
        image={FIT_IMAGES.training}
        tags={[`${machines.length} machines`, "Technogym · Matrix", "Scan via code"]}
      />

      {selected && (
        <div className="modal-overlay" onClick={() => setSelected(null)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h2 style={{ margin: 0 }}>{selected.name}</h2>
              <button className="btn btn-ghost btn-sm" onClick={() => setSelected(null)}>✖</button>
            </div>
            <MachineImage machine={selected} large />

            <div className="muted" style={{ margin: "0.4rem 0 0.8rem", fontSize: "0.9rem" }}>
              {selected.brand} {selected.model} · {(CATEGORY[selected.category] || selected.category)}
            </div>

            <div style={{ border: "1.5px dashed var(--primary)", borderRadius: "12px", padding: "0.8rem", textAlign: "center", marginBottom: "0.8rem" }}>
              <div style={{ fontSize: "0.8rem", color: "var(--muted)", marginBottom: "0.3rem" }}>CODE QR / MACHINE</div>
              <strong style={{ fontFamily: "monospace", fontSize: "1.5rem", color: "var(--primary)", letterSpacing: "2px" }}>{selected.code}</strong>
            </div>

            <h4 style={{ margin: "0.8rem 0 0.3rem" }}>🔧 Réglage selon la morphologie</h4>
            <p className="muted" style={{ fontSize: "0.88rem", margin: 0 }}>{selected.setup_tips || "Aucun conseil enregistré."}</p>

            {selected.location && (
              <p className="muted" style={{ fontSize: "0.85rem", margin: "0.8rem 0 0" }}>📍 {selected.location}</p>
            )}
          </div>
        </div>
      )}

      <div className="card" style={{ marginBottom: "1rem" }}>
        <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
          <select value={brandFilter} onChange={(e) => setBrandFilter(e.target.value)}>
            <option value="">Toutes les marques</option>
            {brands.map((b) => <option key={b} value={b}>{b}</option>)}
          </select>
          <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}>
            <option value="">Toutes les catégories</option>
            {cats.map((c) => <option key={c} value={c}>{CATEGORY[c] || c}</option>)}
          </select>
        </div>
      </div>

      {loading ? (
        <p className="muted">Chargement des machines...</p>
      ) : filtered.length === 0 ? (
        <div className="empty-state">
          <div className="empty-ico">🏋️</div>
          <p>Aucune machine pour ces filtres.</p>
        </div>
      ) : (
        <div className="grid grid-2">
          {filtered.map((m) => (
            <div key={m.id} className="card hoverable" style={{ margin: 0, cursor: "pointer" }} onClick={() => setSelected(m)}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "0.5rem" }}>
                <div>
                  <h4 style={{ margin: 0 }}>{CATEGORY[m.category] || m.category}</h4>
                  <strong>{m.name}</strong>
                </div>
                <span className="badge badge-warn" style={{ fontFamily: "monospace" }}>{m.code}</span>
              </div>
              <MachineImage machine={m} />
              <div className="muted" style={{ fontSize: "0.83rem", margin: "0.4rem 0 0" }}>
                {m.brand} {m.model} · {m.location || "—"}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}