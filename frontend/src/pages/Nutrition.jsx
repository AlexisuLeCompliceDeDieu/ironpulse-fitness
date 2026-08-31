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
  "Petit-déjeuner": "rgba(245,158,11,.14)",
  "Déjeuner": "rgba(14,165,233,.14)",
  "Collation": "rgba(34,211,238,.18)",
  "Dîner": "rgba(236,72,153,.14)",
};

export default function Nutrition({ user }) {
  const [days, setDays] = useState(7);
  const [plan, setPlan] = useState(null);
  const [shoppingList, setShoppingList] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState("success");

  useEffect(() => {
    api.get("/nutrition/plan/latest")
      .then((res) => setPlan(res.data.plan))
      .catch(() => setPlan(null));
    api.get("/nutrition/shopping-list/latest")
      .then((res) => setShoppingList(res.data.shopping_list))
      .catch(() => setShoppingList(null));
  }, []);

  const showMessage = (msg, type = "success") => {
    setMessage(msg);
    setMessageType(type);
  };

  const generate = async () => {
    setLoading(true);
    setMessage("");
    try {
      const res = await api.post("/nutrition/plan/generate", { num_days: days });
      setPlan(res.data.plan);
      showMessage(res.data.message);
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
        tags={[`🎯 ${user.daily_calories} kcal / jour`, `🥑 Repas équilibrés`, `🛒 Liste de courses`]}
      />

      {message && <div className={messageType === "error" ? "error" : "success-msg"}>{message}</div>}

      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <h3 style={{ margin: 0, display: "flex", alignItems: "center", gap: "0.5rem" }}>
              🎯 Objectif calorique
            </h3>
            <p style={{ margin: "0.3rem 0 0 0" }}>
              <strong style={{ fontSize: "1.6rem", color: "var(--primary)" }}>{user.daily_calories}</strong>{" "}
              kcal / jour
            </p>
          </div>
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "end" }}>
            <div className="form-group" style={{ margin: 0 }}>
              <label>Jours</label>
              <input type="number" min="1" max="14" value={days} onChange={(e) => setDays(Number(e.target.value))} style={{ width: "90px" }} />
            </div>
            <button className="btn" onClick={generate} disabled={loading}>
              {loading ? "⏳ Génération..." : "⚡ Générer les menus"}
            </button>
          </div>
        </div>
      </div>

      {plan && (
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.5rem", margin: "0.5rem 0 1rem" }}>
            <h2 className="page-title" style={{ margin: 0 }}>Plan alimentaire · 🗓️ {plan.num_days} jours</h2>
            <button className="btn btn-ghost" onClick={generateList} disabled={loading}>
              {loading ? "..." : "🛒 Générer ma liste de courses"}
            </button>
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
                <span className="badge badge-warn">
                  {item.qty_grams / 1000 > 0 ? `${(item.qty_grams / 1000).toFixed(2)} kg` : `${item.qty_grams} g`}
                </span>
              </label>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
