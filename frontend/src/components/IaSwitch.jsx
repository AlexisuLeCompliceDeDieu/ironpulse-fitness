import { useEffect, useState } from "react";
import api from "../api";

const CLE = "ironpulse_ia_provider";

/** Sélecteur de fournisseur IA. Auto = failover automatique (recommandé).
 *  Un choix explicite est prioritaire mais ne désactive pas le failover. */
export default function IaSwitch({ value, onChange, compact = false }) {
  const [choix, setChoix] = useState(() => {
    try {
      return localStorage.getItem(CLE) || "";
    } catch (e) {
      return "";
    }
  });
  const [fournisseurs, setFournisseurs] = useState([]);

  useEffect(() => {
    if (value !== undefined && value !== null) setChoix(value);
  }, [value]);

  useEffect(() => {
    let vivant = true;
    api.get("/chat/status")
      .then((res) => {
        if (vivant) setFournisseurs((res.data.fournisseurs || []).filter((f) => f.configured));
      })
      .catch(() => { /* le switch reste sur « Auto » */ });
    return () => { vivant = false; };
  }, []);

  const choisir = (id) => {
    setChoix(id);
    try {
      if (id) localStorage.setItem(CLE, id);
      else localStorage.removeItem(CLE);
    } catch (e) { /* stockage indisponible */ }
    if (onChange) onChange(id || null);
  };

  const titres = {
    groq: "Groq · Llama",
    gemini: "Google Gemini",
    mistral: "Mistral",
    openrouter: "OpenRouter",
  };

  return (
    <div className={"ia-switch" + (compact ? " compact" : "")}>
      <span className="ia-switch-label">🧠 IA</span>
      <div className="mode-switch">
        <button
          type="button"
          className={"mode-btn" + (choix === "" ? " active" : "")}
          onClick={() => choisir("")}
          title="Automatique : le meilleur fournisseur disponible, avec bascule en cas de quota épuisé"
        >
          Auto
        </button>
        {fournisseurs.map((f) => (
          <button
            type="button"
            key={f.id}
            className={"mode-btn" + (choix === f.id ? " active" : "")}
            onClick={() => choisir(f.id)}
            title={f.usable ? (f.model || f.label) : (f.raison || "Indisponible")}
          >
            {titres[f.id] || f.label}
            {!f.usable && <span className="ia-dot" />}
          </button>
        ))}
      </div>
    </div>
  );
}
