import { useState, useEffect, useRef } from "react";
import api from "../api.js";
import PageHero, { FIT_IMAGES } from "../components/PageHero.jsx";

const CHAT_SUGGESTIONS = [
  "Que manger pour prendre du muscle ?",
  "Répartis mes calories en macros",
  "Un programme force sans matériel ?",
  "Que manger le soir avant une grosse séance ?",
];

const AGENT_SUGGESTIONS = [
  "Comment se passe ma progression ?",
  "Répartis mes 3000 kcal en macros",
  "Prépare-moi une séance pour demain",
  "Enregistre ma séance d'hier (ressenti 4/5)",
];

export default function Assistant({ user }) {
  const [conv, setConv] = useState([]);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState(null);
  const [streaming, setStreaming] = useState(false);
  const [agentBusy, setAgentBusy] = useState(false);
  const [mode, setMode] = useState("agent");
  const [outils, setOutils] = useState([]);
  const [showTools, setShowTools] = useState(false);
  const [historique, setHistorique] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  const [histLoading, setHistLoading] = useState(false);
  const [resetBusy, setResetBusy] = useState(false);
  const abortRef = useRef(null);
  const bottomRef = useRef(null);
  const storageKey = `ironpulse_assistant_${user.id}`;

  const reinitialiserIa = async () => {
    setResetBusy(true);
    try {
      const res = await api.post("/chat/reset-quota");
      setStatus((s) => ({ ...(s || {}), ia: res.data.ia, groq_enabled: true }));
    } catch (e) {
      /* l'utilisateur réessaiera */
    } finally {
      setResetBusy(false);
    }
  };

  useEffect(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved) setConv(JSON.parse(saved));
    } catch (e) { /* ignore */ }
    api.get("/chat/status")
      .then((res) => setStatus(res.data))
      .catch(() => setStatus(null));
    api.get("/agent/outils")
      .then((res) => setOutils(res.data.outils || []))
      .catch(() => setOutils([]));
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(conv));
    } catch (e) { /* ignore */ }
  }, [conv]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [conv, streaming, agentBusy]);

  const busy = streaming || agentBusy;
  const iconeDe = (nom) => outils.find((o) => o.nom === nom)?.icone || "🔧";

  const stop = () => {
    if (abortRef.current) abortRef.current.abort();
  };

  const majMsg = (index, fn) => {
    setConv((c) => {
      const next = [...c];
      if (next[index]) next[index] = fn(next[index]);
      return next;
    });
  };

  const patchLast = (patch) => {
    setConv((c) => {
      const next = [...c];
      const last = next[next.length - 1];
      if (last && last.role === "assistant") next[next.length - 1] = { ...last, ...patch };
      return next;
    });
  };

  const appendToken = (token) => {
    setConv((c) => {
      const next = [...c];
      const last = next[next.length - 1];
      if (last && last.role === "assistant") {
        next[next.length - 1] = { ...last, content: (last.content || "") + token };
      }
      return next;
    });
  };

  // ── Mode chat (streaming de tokens) ──────────────────────────────
  const sendChat = async (textOverride) => {
    const text = (textOverride ?? input).trim();
    if (!text || streaming) return;
    const userMsg = { role: "user", content: text };
    const history = [...conv, userMsg];
    setConv([...history, { role: "assistant", content: "" }]);
    setInput("");
    setStreaming(true);

    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const resp = await fetch("/api/chat/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        signal: controller.signal,
        body: JSON.stringify({ messages: history }),
      });

      if (!resp.ok) {
        let msg = "Erreur du serveur";
        try {
          const err = await resp.json();
          if (err.error) msg = err.error;
        } catch (e) { /* ignore */ }
        patchLast({ content: `⚠️ ${msg}` });
        return;
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop();
        for (const part of parts) {
          const line = part.trim();
          if (!line.startsWith("data:")) continue;
          const payload = line.slice(5).trim();
          if (payload === "[DONE]") continue;
          try {
            const obj = JSON.parse(payload);
            if (obj.token !== undefined) {
              appendToken(obj.token);
            } else if (obj.error) {
              patchLast({ content: `⚠️ ${obj.error}` });
            }
          } catch (e) { /* ignore bad json */ }
        }
      }
    } catch (err) {
      if (err.name !== "AbortError") {
        patchLast({ content: "⚠️ Connexion coupée. Réessaie." });
      }
    } finally {
      setStreaming(false);
      abortRef.current = null;
    }
  };

  // ── Mode agent (flux d'événements : tools visibles en direct) ────
  const traiterEvent = (index, evt) => {
    switch (evt.type) {
      case "debut":
        majMsg(index, (m) => ({ ...m, demande_id: evt.demande_id, maxTours: evt.max_tours }));
        break;
      case "tour":
        majMsg(index, (m) => ({ ...m, tour: evt.tour, maxTours: evt.max_tours, fournisseur: evt.fournisseur || m.fournisseur }));
        break;
      case "tool_debut":
        majMsg(index, (m) => ({
          ...m,
          etapes: [
            ...(m.etapes || []),
            {
              etape: evt.etape, outil: evt.outil, arguments: evt.arguments || {},
              icone: evt.icone, libelle: evt.libelle, categorie: evt.categorie,
              statut: "en_cours",
            },
          ],
        }));
        break;
      case "tool_fin":
        majMsg(index, (m) => {
          const etapes = [...(m.etapes || [])];
          let cible = -1;
          for (let k = etapes.length - 1; k >= 0; k--) {
            if (etapes[k].outil === evt.outil && etapes[k].statut === "en_cours") { cible = k; break; }
          }
          const maj = {
            statut: "termine", resultat: evt.resultat, resume: evt.resume,
            duree_ms: evt.duree_ms, icone: evt.icone || etapes[cible]?.icone,
            libelle: evt.libelle || etapes[cible]?.libelle,
          };
          if (cible >= 0) etapes[cible] = { ...etapes[cible], ...maj };
          else etapes.push({ etape: evt.etape, outil: evt.outil, arguments: evt.arguments || {}, ...maj });
          return { ...m, etapes };
        });
        break;
      case "confirmation":
        majMsg(index, (m) => ({
          ...m,
          content: evt.reponse,
          agentLoading: false,
          statut: "confirmation_requise",
          confirmation: {
            ...evt.confirmation,
            icone: evt.icone, libelle: evt.libelle,
            demande_id: evt.demande_id, demande: m.demande,
          },
        }));
        break;
      case "reponse":
      case "limite":
      case "quota":
        majMsg(index, (m) => ({
          ...m,
          content: evt.reponse,
          statut: evt.type,
          agentLoading: false,
          confirmation: null,
          fournisseur: evt.fournisseur || m.fournisseur,
          etapes: evt.etapes || m.etapes,
        }));
        break;
      case "erreur":
        majMsg(index, (m) => ({ ...m, content: `⚠️ ${evt.reponse}`, statut: "erreur", agentLoading: false }));
        break;
      default:
        break;
    }
  };

  const lireFluxAgent = async (resp, index) => {
    const reader = resp.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop();
      for (const part of parts) {
        const line = part.trim();
        if (!line.startsWith("data:")) continue;
        const payload = line.slice(5).trim();
        if (payload === "[DONE]") continue;
        try {
          traiterEvent(index, JSON.parse(payload));
        } catch (e) { /* ignore bad json */ }
      }
    }
  };

  const sendAgent = async (textOverride) => {
    const text = (textOverride ?? input).trim();
    if (!text || agentBusy) return;
    const index = conv.length + 1;
    setConv((c) => [
      ...c,
      { role: "user", content: text },
      { role: "assistant", content: "", agentLoading: true, demande: text, etapes: [], tour: 0, maxTours: 5 },
    ]);
    setInput("");
    setAgentBusy(true);
    try {
      const resp = await fetch("/api/agent/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ demande: text }),
      });
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        majMsg(index, (m) => ({ ...m, agentLoading: false, content: `⚠️ ${data.error || "Erreur du serveur"}` }));
        return;
      }
      await lireFluxAgent(resp, index);
    } catch (err) {
      majMsg(index, (m) => ({ ...m, agentLoading: false, content: "⚠️ Connexion coupée. Réessaie." }));
    } finally {
      setAgentBusy(false);
    }
  };

  const confirmAgent = async (index, ok) => {
    const entry = conv[index];
    if (!entry?.confirmation || entry.confirming) return;
    if (!ok) {
      majMsg(index, (m) => ({
        ...m, content: "✔ Action annulée, rien n'a été modifié.",
        confirmation: null, statut: "reponse",
      }));
      return;
    }
    majMsg(index, (m) => ({ ...m, confirming: true, agentLoading: true }));
    try {
      const resp = await fetch("/api/agent/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          demande: entry.confirmation.demande || entry.demande || "Confirmation d'action",
          confirmation: {
            tool: entry.confirmation.tool,
            arguments: entry.confirmation.arguments,
            demande_id: entry.confirmation.demande_id,
          },
        }),
      });
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        majMsg(index, (m) => ({ ...m, confirming: false, agentLoading: false, content: `⚠️ ${data.error || "Échec de la confirmation."}` }));
        return;
      }
      await lireFluxAgent(resp, index);
    } catch (err) {
      majMsg(index, (m) => ({ ...m, confirming: false, agentLoading: false, content: "⚠️ Échec de la confirmation. Réessaie." }));
    } finally {
      majMsg(index, (m) => ({ ...m, confirming: false }));
    }
  };

  const send = (textOverride) => {
    if (mode === "agent") sendAgent(textOverride);
    else sendChat(textOverride);
  };

  const toggleHistory = async () => {
    const next = !showHistory;
    setShowHistory(next);
    if (!next) return;
    setHistLoading(true);
    try {
      const res = await api.get("/agent/historique");
      setHistorique(res.data.demandes || []);
    } catch (e) {
      setHistorique([]);
    } finally {
      setHistLoading(false);
    }
  };

  const suggestions = mode === "agent" ? AGENT_SUGGESTIONS : CHAT_SUGGESTIONS;
  const statusLine = status?.groq_enabled
    ? `Assistant prêt (${status.model})`
    : "Assistant indisponible (IA non configurée)";

  return (
    <div className="container">
      <PageHero
        title="🤖 Assistant IRONPULSE"
        subtitle="Posez vos questions sur l'entraînement, la nutrition ou votre progression : il répond avec le contexte réel de votre profil."
        image={FIT_IMAGES.nutrition}
        tags={[
          "💬 Contexte = votre profil",
          status?.groq_enabled ? "🟢 " + statusLine : "🔴 " + statusLine,
        ]}
      />

      <div className="mode-switch">
        <button className={"mode-btn" + (mode === "agent" ? " active" : "")} onClick={() => setMode("agent")}>
          🛠️ Agent (outils réels)
        </button>
        <button className={"mode-btn" + (mode === "chat" ? " active" : "")} onClick={() => setMode("chat")}>
          💬 Chat (conversation)
        </button>
      </div>

      {mode === "agent" && outils.length > 0 && (
        <div className="agent-panel">
          <button className="agent-panel-head" onClick={() => setShowTools((v) => !v)}>
            <span>🛠️ Outils de l'agent</span>
            <span className="agent-panel-count">{outils.length}</span>
            <span className="chev">{showTools ? "▾" : "▸"}</span>
          </button>
          {showTools && (
            <div className="agent-tools-list">
              {outils.map((o) => (
                <div key={o.nom} className="agent-tool">
                  <span className="agent-tool-ico">{o.icone}</span>
                  <div className="agent-tool-body">
                    <div className="agent-tool-name">
                      {o.libelle} <code>{o.nom}</code>
                      {o.sensible && <span className="badge-write">écriture · validation</span>}
                      <span className="badge-cat">{o.categorie}</span>
                    </div>
                    <div className="agent-tool-desc">{o.description}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {mode === "agent" && (
        <div className="agent-panel">
          <button className="agent-panel-head" onClick={toggleHistory}>
            <span>📜 Historique de l'agent</span>
            <span className="chev">{showHistory ? "▾" : "▸"}</span>
          </button>
          {showHistory && (
            <div className="agent-history">
              {histLoading && <div className="muted">Chargement…</div>}
              {!histLoading && historique.length === 0 && (
                <div className="muted">Aucune demande enregistrée pour le moment.</div>
              )}
              {historique.map((d) => {
                const trace = (d.resultats || []).filter((r) => r.outil_utilise);
                return (
                  <div key={d.id} className="agent-hist-item">
                    <div className="agent-hist-q">{d.texte}</div>
                    <div className="agent-hist-meta">
                      <span>{d.date_creation ? new Date(d.date_creation).toLocaleString("fr-FR") : ""}</span>
                      <span className="agent-hist-tools">
                        {trace.length === 0
                          ? <em>réponse directe</em>
                          : trace.map((r, j) => (
                            <span key={j} className="tool-badge">{iconeDe(r.outil_utilise)} {r.outil_utilise}</span>
                          ))}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {!status?.groq_enabled && (
        <div className="error">L'agent IA n'est pas encore configuré. Les messages ne pourront pas être envoyés.</div>
      )}

      {status?.ia?.configured?.length > 0 && status?.ia?.usable?.length === 0 && (
        <div className="card" style={{ marginTop: "1rem", borderColor: "rgba(245,158,11,.5)" }}>
          <p style={{ margin: 0, fontWeight: 700 }}>🚫 {status.ia.message}</p>
          <p className="muted" style={{ fontSize: "0.85rem", margin: "0.4rem 0 0.6rem 0" }}>
            Les fournisseurs sont bloqués temporairement (limite d'API ou message
            d'erreur mal interprété). Tu peux les réactiver sans attendre.
          </p>
          <button className="btn" disabled={resetBusy} onClick={reinitialiserIa}>
            {resetBusy ? "⏳ Réactivation..." : "🔄 Réactiver les IA"}
          </button>
        </div>
      )}

      <div className="card chat-card">
        <div className="chat-scroll">
          {conv.length === 0 && (
            <div className="muted" style={{ textAlign: "center", padding: "1.5rem" }}>
              <p style={{ margin: "0 0 0.8rem 0" }}>
                {mode === "agent"
                  ? "🛠️ Mode agent : l'IA raisonne et appelle vos outils (profil, progression, macros, séances) pour répondre avec vos vraies données."
                  : "💬 Commencez la conversation…"}
              </p>
              <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap", justifyContent: "center" }}>
                {suggestions.map((s) => (
                  <button key={s} className="btn btn-ghost btn-sm" onClick={() => send(s)} disabled={busy}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {conv.map((m, i) => (
            <div key={i} className={"chat-bubble " + (m.role === "user" ? "chat-user" : "chat-ai")}>
              <div className="chat-author">{m.role === "user" ? "Vous" : "🤖 Coach"}</div>

              {m.role === "assistant" && m.agentLoading && (
                <div className="agent-tour">
                  🔁 raisonnement — tour {Math.max(m.tour || 1, 1)}/{m.maxTours || 5}
                  {m.fournisseur ? ` · 🧠 ${m.fournisseur}` : ""}
                </div>
              )}

              <div className="chat-text">{m.content || (m.role === "assistant" && !m.agentLoading ? "…" : "")}</div>

              {m.role === "assistant" && m.etapes && m.etapes.length > 0 && (
                <div className="agent-steps">
                  {m.etapes.map((s, j) => (
                    <div key={j} className={"agent-step " + (s.statut === "en_cours" ? "en-cours" : "termine")}>
                      <span className="agent-step-ico">{s.icone || "🔧"}</span>
                      <div className="agent-step-main">
                        <div className="agent-step-top">
                          <span className="agent-step-name">{s.libelle || s.outil}</span>
                          <code className="agent-step-code">{s.outil}</code>
                          {s.statut === "en_cours"
                            ? <span className="agent-step-status running">● en cours…</span>
                            : <span className="agent-step-status ok">✓{s.duree_ms != null ? ` ${s.duree_ms} ms` : ""}</span>}
                        </div>
                        {s.arguments && Object.keys(s.arguments).length > 0 && (
                          <div className="agent-step-args">
                            {Object.entries(s.arguments).map(([k, v]) => (
                              <span key={k} className="arg-chip">{k}: {String(v)}</span>
                            ))}
                          </div>
                        )}
                        {s.resume && <div className="agent-step-resume">{s.resume}</div>}
                        {s.resultat && (
                          <details className="agent-step-raw">
                            <summary>données brutes</summary>
                            <pre>{JSON.stringify(s.resultat, null, 2)}</pre>
                          </details>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {m.role === "assistant" && m.confirmation && (
                <div className="confirm-card">
                  <div className="confirm-title">⚠️ Action d'écriture en attente de votre validation</div>
                  <div className="confirm-action">
                    {m.confirmation.icone || "🔧"} {m.confirmation.libelle || m.confirmation.tool}{" "}
                    <code>{m.confirmation.tool}</code>
                  </div>
                  {m.confirmation.arguments && (
                    <code className="confirm-args">{JSON.stringify(m.confirmation.arguments)}</code>
                  )}
                  <div className="confirm-buttons">
                    <button className="btn btn-sm" disabled={m.confirming} onClick={() => confirmAgent(i, true)}>
                      {m.confirming ? "Exécution…" : "✔ Valider"}
                    </button>
                    <button className="btn btn-ghost btn-sm" disabled={m.confirming} onClick={() => confirmAgent(i, false)}>
                      ✖ Refuser
                    </button>
                  </div>
                </div>
              )}

              {m.role === "assistant" && m.agentLoading && (
                <div className="chat-text typing">▌</div>
              )}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        <div className="chat-input">
          <input
            type="text"
            placeholder={mode === "agent"
              ? "Votre demande… (ex : enregistre ma séance d'hier, ressenti 4/5)"
              : "Votre question… (ex : donne-moi un repas à 700 kcal)"}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") send();
            }}
            disabled={busy || !status?.groq_enabled}
            style={{ flex: 1 }}
          />
          {streaming ? (
            <button className="btn btn-danger" onClick={stop}>■ Arrêter</button>
          ) : (
            <button className="btn" onClick={() => send()} disabled={!input.trim() || !status?.groq_enabled}>
              ➤ {mode === "agent" ? "Demander à l'agent" : "Envoyer"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}