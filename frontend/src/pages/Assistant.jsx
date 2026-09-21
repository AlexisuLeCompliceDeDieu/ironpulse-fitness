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

const STEP_ICONS = { 1: "①", 2: "②", 3: "③", 4: "④", 5: "⑤" };

function stepLabel(etape) {
  return `${STEP_ICONS[etape] ?? "-"} étape ${etape}`;
}

export default function Assistant({ user }) {
  const [conv, setConv] = useState([]);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState(null);
  const [streaming, setStreaming] = useState(false);
  const [agentBusy, setAgentBusy] = useState(false);
  const [mode, setMode] = useState("agent");
  const abortRef = useRef(null);
  const bottomRef = useRef(null);
  const storageKey = `ironpulse_assistant_${user.id}`;

  useEffect(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved) setConv(JSON.parse(saved));
    } catch (e) { /* ignore */ }
    api.get("/chat/status")
      .then((res) => setStatus(res.data))
      .catch(() => setStatus(null));
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

  const stop = () => {
    if (abortRef.current) abortRef.current.abort();
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

  const sendAgent = async (textOverride) => {
    const text = (textOverride ?? input).trim();
    if (!text || agentBusy) return;
    const userMsg = { role: "user", content: text };
    setConv((c) => [
      ...c,
      userMsg,
      { role: "assistant", content: "", agentLoading: true, demande: text },
    ]);
    setInput("");
    setAgentBusy(true);
    try {
      const resp = await fetch("/api/agent/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ demande: text }),
      });
      const data = await resp.json().catch(() => ({}));
      const statut = data.statut || "erreur";
      const contenu = data.reponse || data.error || "Erreur du serveur";
      patchLast({
        agentLoading: false,
        statut,
        content: statut === "confirmation_requise" ? contenu : contenu,
        etapes: data.etapes || [],
        confirmation: data.confirmation
          ? { ...data.confirmation, demande_id: data.demande_id, demande: text }
          : null,
      });
    } catch (err) {
      patchLast({ agentLoading: false, content: "⚠️ Connexion coupée. Réessaie." });
    } finally {
      setAgentBusy(false);
    }
  };

  const confirmAgent = async (index, ok) => {
    const entry = conv[index];
    if (!entry?.confirmation || entry.confirming) return;
    if (!ok) {
      setConv((c) => {
        const next = [...c];
        next[index] = { ...next[index], content: "✔ Action annulée, rien n'a été modifié.", confirmation: null, statut: "reponse" };
        return next;
      });
      return;
    }
    setConv((c) => {
      const next = [...c];
      next[index] = { ...next[index], confirming: true };
      return next;
    });
    try {
      const resp = await fetch("/api/agent/", {
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
      const data = await resp.json().catch(() => ({}));
      setConv((c) => {
        const next = [...c];
        next[index] = {
          role: "assistant",
          content: data.reponse || data.error || "Action confirmée.",
          statut: data.statut || "erreur",
          etapes: [...(entry.etapes || []), ...(data.etapes || [])],
          confirmation: null,
        };
        return next;
      });
    } catch (err) {
      setConv((c) => {
        const next = [...c];
        next[index] = { ...next[index], confirming: false, content: "⚠️ Échec de la confirmation. Réessaie." };
        return next;
      });
    }
  };

  const send = (textOverride) => {
    if (mode === "agent") sendAgent(textOverride);
    else sendChat(textOverride);
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
        <button
          className={"mode-btn" + (mode === "agent" ? " active" : "")}
          onClick={() => setMode("agent")}
        >
          🛠️ Agent (outils réels)
        </button>
        <button
          className={"mode-btn" + (mode === "chat" ? " active" : "")}
          onClick={() => setMode("chat")}
        >
          💬 Chat (conversation)
        </button>
      </div>

      {!status?.groq_enabled && (
        <div className="error">L'agent IA n'est pas encore configuré. Les messages ne pourront pas être envoyés.</div>
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
              <div className="chat-text">{m.content || (m.role === "assistant" && !m.agentLoading ? "…" : "")}</div>

              {m.role === "assistant" && !m.confirming && m.etapes && m.etapes.length > 0 && (
                <div className="agent-steps">
                  {m.etapes.map((s, j) => (
                    <div key={j} className="agent-step">
                      <span className="agent-step-n">{stepLabel(s.etape)}</span>
                      <span className="agent-step-name">🔧 {s.outil}</span>
                      <code className="agent-step-out">
                        {s.resultat ? JSON.stringify(s.resultat) : "…"}
                      </code>
                    </div>
                  ))}
                </div>
              )}

              {m.role === "assistant" && m.confirmation && (
                <div className="confirm-card">
                  <div className="confirm-title">⚠️ Action d'écriture en attente de votre validation</div>
                  <div className="confirm-action">🔧 {m.confirmation.tool}</div>
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