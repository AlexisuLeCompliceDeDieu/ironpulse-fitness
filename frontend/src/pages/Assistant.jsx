import { useState, useEffect, useRef } from "react";
import api from "../api.js";
import PageHero, { FIT_IMAGES } from "../components/PageHero.jsx";

const SUGGESTIONS = [
  "Que manger pour prendre du muscle ?",
  "Répartis mes calories en macros",
  "Un programme force sans matériel ?",
  "Que manger le soir avant une grosse séance ?",
];

export default function Assistant({ user }) {
  const [conv, setConv] = useState([]);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState(null);
  const [streaming, setStreaming] = useState(false);
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
  }, [conv, streaming]);

  const stop = () => {
    if (abortRef.current) abortRef.current.abort();
  };

  const send = async (textOverride) => {
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
        setConv((c) => {
          const next = [...c];
          next[next.length - 1] = { role: "assistant", content: `⚠️ ${msg}` };
          return next;
        });
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
              setConv((c) => {
                const next = [...c];
                const last = next[next.length - 1];
                if (last && last.role === "assistant") {
                  next[next.length - 1] = { ...last, content: last.content + obj.token };
                }
                return next;
              });
            } else if (obj.error) {
              setConv((c) => {
                const next = [...c];
                const last = next[next.length - 1];
                if (last && last.role === "assistant") {
                  next[next.length - 1] = { ...last, content: `⚠️ ${obj.error}` };
                }
                return next;
              });
            }
          } catch (e) { /* ignore bad json */ }
        }
      }
    } catch (err) {
      if (err.name !== "AbortError") {
        setConv((c) => {
          const next = [...c];
          next[next.length - 1] = { role: "assistant", content: "⚠️ Connexion coupée. Réessaie." };
          return next;
        });
      }
    } finally {
      setStreaming(false);
      abortRef.current = null;
    }
  };

  const statusLine = status?.groq_enabled
    ? `Assistant prêt (${status.model})`
    : "Assistant indisponible (IA non configurée)";

  return (
    <div className="container">
      <PageHero
        title="🤖 Assistant IRONPULSE"
        subtitle="Posez toutes vos questions sur l'entraînement, la nutrition ou votre progression : il répond avec le contexte de votre profil."
        image={FIT_IMAGES.nutrition}
        tags={["💬 Contexte = votre profil", status?.groq_enabled ? "🟢 " + statusLine : "🔴 " + statusLine]}
      />

      {!status?.groq_enabled && (
        <div className="error">L'agent IA n'est pas encore configuré. Les messages ne pourront pas être envoyés.</div>
      )}

      <div className="card chat-card">
        <div className="chat-scroll">
          {conv.length === 0 && (
            <div className="muted" style={{ textAlign: "center", padding: "1.5rem" }}>
              <p style={{ margin: "0 0 0.8rem 0" }}>💬 Commencez la conversation…</p>
              <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap", justifyContent: "center" }}>
                {SUGGESTIONS.map((s) => (
                  <button key={s} className="btn btn-ghost btn-sm" onClick={() => send(s)} disabled={streaming}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {conv.map((m, i) => (
            <div key={i} className={"chat-bubble " + (m.role === "user" ? "chat-user" : "chat-ai")}>
              <div className="chat-author">{m.role === "user" ? "Vous" : "🤖 Coach"}</div>
              <div className="chat-text">{m.content || (m.role === "assistant" ? "…" : "")}</div>
            </div>
          ))}
          {streaming && (
            <div className="chat-bubble chat-ai">
              <div className="chat-author">🤖 Coach</div>
              <div className="chat-text typing">▌</div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="chat-input">
          <input
            type="text"
            placeholder="Votre question… (ex : donne-moi un repas à 700 kcal)"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") send();
            }}
            disabled={streaming || !status?.groq_enabled}
            style={{ flex: 1 }}
          />
          {streaming ? (
            <button className="btn btn-danger" onClick={stop}>■ Arrêter</button>
          ) : (
            <button className="btn" onClick={() => send()} disabled={!input.trim() || !status?.groq_enabled}>
              ➤ Envoyer
            </button>
          )}
        </div>
      </div>
    </div>
  );
}