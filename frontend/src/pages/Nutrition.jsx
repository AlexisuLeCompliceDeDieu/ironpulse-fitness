import { useState, useEffect } from "react";
import api from "../api.js";
import PageHero, { FIT_IMAGES } from "../components/PageHero.jsx";

const MEAL_ICON = {
  "Petit-déjeuner": "🌅",
  "Déjeuner": "🍽️",
  "Collation": "🍎",
  "Dîner": "🌙",
};

const MEAL_COLORS = {
  "Petit-déjeuner": "rgba(249,115,22,.16)",
  "Déjeuner": "rgba(253,186,116,.14)",
  "Collation": "rgba(251,146,60,.18)",
  "Dîner": "rgba(234,88,12,.16)",
};

export default function Nutrition({ user }) {
  const [days, setDays] = useState(7);
  const [plan, setPlan] = useState(null);
  const [shoppingList, setShoppingList] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState("success");
  const [targetKcal, setTargetKcal] = useState(user.daily_calories);
  const [useAI, setUseAI] = useState(true);
  const [aiStatus, setAiStatus] = useState(null);
  const [genInfo, setGenInfo] = useState(null);

  useEffect(() => {
    api.get("/nutrition/target")
      .then((res) => setTargetKcal(res.data?.current ?? user.daily_calories))
      .catch(() => {});
    api.get("/nutrition/plan/latest")
      .then((res) => setPlan(res.data.plan))
      .catch(() => setPlan(null));
    api.get("/nutrition/shopping-list/latest")
      .then((res) => setShoppingList(res.data.shopping_list))
      .catch(() => setShoppingList(null));
    api.get("/chat/status")
      .then((res) => setAiStatus({ ...res.data, ...(res.data.ia || {}) }))
      .catch(() => setAiStatus({ groq_enabled: false, chargement: false }));
  }, []);

  const showMessage = (msg, type = "success") => {
    setMessage(msg);
    setMessageType(type);
  };

  const generate = async () => {
    setLoading(true);
    setMessage("");
    setGenInfo(null);
    try {
      const res = await api.post("/nutrition/plan/generate", { num_days: days, use_ai: useAI });
      setPlan(res.data.plan);
      const g = res.data.generation || {};
      setGenInfo(g);
      if (useAI && g.mode !== "ai") {
        const extra = g.regenerated ? " Menus régénérés (sans répétition)." : "";
        showMessage("⚠️ " + aiFallbackMsg(g.reason) + extra, "error");
      } else if (g.regenerated) {
        showMessage(`🔄 Menus régénérés — ${g.avoided || 0} repas du plan précédent remplacés.`);
      } else {
        showMessage(res.data.message);
      }
    } catch (err) {
      showMessage(err.response?.data?.error || "Erreur de génération", "error");
    } finally {
      setLoading(false);
    }
  };

  const generateList = async () => {
    setLoading(true);
    setMessage("");
    try {
      const res = await api.post("/nutrition/shopping-list/generate", { meal_plan_id: plan?.id });
      setShoppingList(res.data.shopping_list);
      showMessage(res.data.message);
    } catch (err) {
      showMessage(err.response?.data?.error || "Erreur de génération de la liste", "error");
    } finally {
      setLoading(false);
    }
  };

  const dailyTotals = plan
    ? plan.meals.reduce((acc, m) => {
        acc[m.day] = acc[m.day] || { kcal: 0, protein: 0, carbs: 0, fat: 0 };
        acc[m.day].kcal += m.totals.kcal;
        acc[m.day].protein += m.totals.protein;
        acc[m.day].carbs += m.totals.carbs;
        acc[m.day].fat += m.totals.fat;
        return acc;
      }, {})
    : {};

  return (
    <div className="container">
      <PageHero
        title="🥗 Nutrition"
        subtitle="Générez vos menus et listes de courses selon votre objectif calorique personnalisé."
        image={FIT_IMAGES.nutrition}
        tags={[`🎯 ${targetKcal} kcal / jour`, `🥑 Repas équilibrés`, `🛒 Liste de courses`]}
      />

      {message && <div className={messageType === "error" ? "error" : "success-msg"}>{message}</div>}

      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <h3 style={{ margin: 0, display: "flex", alignItems: "center", gap: "0.5rem" }}>
              🎯 Objectif calorique
            </h3>
            <p style={{ margin: "0.3rem 0 0 0" }}>
              <strong style={{ fontSize: "1.6rem", color: "var(--primary)" }}>{targetKcal}</strong>{" "}
              kcal / jour
            </p>
          </div>
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "end", flexWrap: "wrap" }}>
            <div className="form-group" style={{ margin: 0 }}>
              <label>Jours</label>
              <input type="number" min="1" max="90" value={days} onChange={(e) => setDays(Number(e.target.value))} style={{ width: "90px" }} />
            </div>
            <button className="btn" onClick={generate} disabled={loading}>
              {loading ? "⏳ Génération..." : plan ? "🔄 Régénérer les menus" : "⚡ Générer les menus"}
            </button>
            <div style={{ display: "flex", gap: "0.3rem" }}>
              <button className="btn btn-ghost" onClick={() => setDays(7)}>[7j]</button>
              <button className="btn btn-ghost" onClick={() => setDays(30)}>[1 mois]</button>
              <button className="btn btn-ghost" onClick={() => setDays(90)}>[3 mois]</button>
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "0.8rem", flexWrap: "wrap", marginTop: "1rem" }}>
          <span className="muted" style={{ fontSize: "0.85rem" }}>Mode de génération :</span>
          <button
            type="button"
            className={"chip" + (useAI ? " active" : "")}
            onClick={() => setUseAI(true)}
            title="L'agent IA compose les repas (répartition automatique entre fournisseurs gratuits)."
          >
            🤖 Agent IA
          </button>
          <button
            type="button"
            className={"chip" + (!useAI ? " active" : "")}
            onClick={() => setUseAI(false)}
            title="Algorithme classique avec recettes fixes."
          >
            ⚙️ Classique
          </button>
        </div>

        {quotaWarning(aiStatus) && (
          <div className="error" style={{ marginTop: "0.6rem" }}>
            {quotaWarning(aiStatus)}
          </div>
        )}
      </div>

      {plan && (
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.5rem", margin: "0.5rem 0 1rem" }}>
            <h2 className="page-title" style={{ margin: 0, display: "flex", alignItems: "center", gap: "0.6rem" }}>
              Plan alimentaire · 🗓️ {plan.num_days} jours
              {genInfo?.mode === "ai" ? (
                <span className="badge badge-cyan" title={`Repas composés par ${genInfo.provider_label || "IA"} (${genInfo.model})`}>
                  🤖 {genInfo.provider_label || "IA"}
                </span>
              ) : (
                <span className="badge badge-warn" title={genInfo?.reason ? `Fallback : ${genInfo.reason}` : "Recettes classiques"}>⚙️ Classique</span>
              )}
            </h2>
            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
              <button className="btn" onClick={generate} disabled={loading} title="Régénère les menus en évitant de répéter les repas du plan actuel.">
                {loading ? "⏳ Régénération..." : "🔄 Régénérer les menus"}
              </button>
              <button className="btn btn-ghost" onClick={generateList} disabled={loading}>
                {loading ? "..." : "🛒 Générer ma liste de courses"}
              </button>
            </div>
          </div>

          <div className="grid grid-2">
            {Object.keys(dailyTotals).map((dayNum) => (
              <div className="card" key={dayNum} style={{ margin: 0 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.6rem" }}>
                  <h4 style={{ margin: 0 }}>📅 Jour {dayNum}</h4>
                  <span className="badge badge-pink">
                    {Math.round(dailyTotals[dayNum].kcal)} kcal
                  </span>
                </div>
                <div className="muted" style={{ fontSize: "0.82rem", marginBottom: "0.7rem" }}>
                  💪 P {Math.round(dailyTotals[dayNum].protein)}g · 🍞 G {Math.round(dailyTotals[dayNum].carbs)}g · 🥑 L {Math.round(dailyTotals[dayNum].fat)}g
                </div>
                {plan.meals.filter((m) => m.day === Number(dayNum)).map((meal) => (
                  <div key={meal.id} className="exercise-row" style={{ padding: "0.6rem 0.4rem" }}>
                    <div style={{ display: "flex", alignItems: "flex-start", gap: "0.6rem" }}>
                      <span className="exercise-ico" style={{ background: MEAL_COLORS[meal.meal_type] || "var(--card-2)" }}>
                        {MEAL_ICON[meal.meal_type] || "🍽️"}
                      </span>
                      <div>
                        <div className="meal-type">{meal.meal_type}</div>
                        <strong>{meal.name}</strong>
                        <div className="muted" style={{ fontSize: "0.82rem" }}>
                          {meal.items.map((it) => `${it.food_name} (${it.quantity}g)`).join(" · ")}
                        </div>
                      </div>
                    </div>
                    <div className="muted" style={{ fontSize: "0.8rem", whiteSpace: "nowrap" }}>
                      {Math.round(meal.totals.kcal)} kcal
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}

      {shoppingList && shoppingList.items.length > 0 && (
        <div className="card" style={{ marginTop: "1.3rem" }}>
          <h3 style={{ marginTop: 0 }}>🛒 Liste de courses</h3>
          <div className="grid grid-2">
            {shoppingList.items.map((item, idx) => (
              <label key={idx} style={{ display: "flex", alignItems: "center", gap: "0.6rem", fontWeight: 600, background: "var(--card-2)", padding: "0.6rem 0.8rem", borderRadius: "10px" }}>
                <input
                  type="checkbox"
                  style={{ width: "20px", height: "20px", margin: 0, accentColor: "var(--primary)" }}
                />
                <span style={{ flex: 1 }}>{item.name}</span>
                {item.pack_note ? (
                  <span className="badge badge-cyan">{item.pack_note}</span>
                ) : null}
                <span className="badge badge-warn">{formatQty(item.qty_grams)}</span>
              </label>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function formatQty(grams) {
  if (grams >= 1000) return `${(grams / 1000).toFixed(2).replace(/\.?0+$/, "")} kg`;
  return `${Math.round(grams)} g`;
}

function aiFallbackMsg(reason) {
  if (!reason) return "L'agent IA n'a pas pu générer les menus — mode classique utilisé.";
  if (reason.startsWith("provider_error")) {
    if (reason.includes("daily_limit")) {
      return "Quota IA atteint pour aujourd'hui — menus générés en mode classique (retour automatique demain).";
    }
    if (reason.includes("none_available")) {
      return "Aucune IA disponible (tous les fournisseurs ont atteint leur limite) — menus en mode classique.";
    }
    if (reason.includes("rate_limit") || reason.includes("per_minute")) {
      return "Les IAs sont momentanément limitées — menus en mode classique, réessaie dans une minute.";
    }
    if (reason.includes("invalid_key")) {
      return "Clé IA invalide — menus générés en mode classique.";
    }
    return "Toutes les IAs ont échoué. Menus générés en mode classique.";
  }
  if (reason.startsWith("parse_error")) {
    return "L'IA a renvoyé un format invalide. Menus générés en mode classique.";
  }
  if (reason.startsWith("db_error")) {
    return "Erreur d'enregistrement côté IA. Menus générés en mode classique.";
  }
  if (reason.startsWith("ai_error")) {
    return "Erreur de l'agent IA. Menus générés en mode classique.";
  }
  if (reason === "too_many_days") {
    return "Plan trop long pour l'agent IA (maximum 30 jours) — menus générés en mode classique.";
  }
  if (reason === "quota_exceeded") {
    return "Quota IA atteint pour aujourd'hui — menus générés en mode classique.";
  }
  if (reason === "groq_unavailable" || reason === "groq_disabled" || reason === "ai_disabled") {
    return "Agent IA non configuré — menus générés en mode classique.";
  }
  return "Menus générés en mode classique.";
}

function quotaWarning(aiStatus) {
  if (!aiStatus) return "";
  const configures = aiStatus.configured?.length || 0;
  if (!configures) {
    return aiStatus.chargement === false
      ? "ℹ️ Impossible de lire le statut de l'IA : les repas sont générés en mode classique."
      : "ℹ️ L'agent IA n'est pas configuré (fallback classique).";
  }
  if (!(aiStatus.usable?.length || 0)) {
    return `🚫 ${aiStatus.message || "Toutes les IA sont bloquées"} — les repas sont générés en mode classique.`;
  }
  const rpdPct = Number(aiStatus.groq_rpd_pct || 0);
  const rpmPct = Number(aiStatus.groq_rpm_pct || 0);
  if (rpdPct >= 85) return `⚠️ Quota IA presque épuisé (${rpdPct.toFixed(0)} % du quota journalier).`;
  if (rpmPct >= 80) return `⚠️ Nombreux appels IA ce moment — ralentissez un peu.`;
  return "";
}
