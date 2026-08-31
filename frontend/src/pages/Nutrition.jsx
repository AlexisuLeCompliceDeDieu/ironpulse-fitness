import { useState, useEffect } from "react";
import api from "../api.js";

export default function Nutrition({ user }) {
  const [days, setDays] = useState(7);
  const [plan, setPlan] = useState(null);
  const [shoppingList, setShoppingList] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    api.get("/nutrition/plan/latest")
      .then((res) => setPlan(res.data.plan))
      .catch(() => setPlan(null));
    api.get("/nutrition/shopping-list/latest")
      .then((res) => setShoppingList(res.data.shopping_list))
      .catch(() => setShoppingList(null));
  }, []);

  const generate = async () => {
    setLoading(true);
    setMessage("");
    try {
      const res = await api.post("/nutrition/plan/generate", { num_days: days });
      setPlan(res.data.plan);
      setMessage(res.data.message);
    } catch (err) {
      setMessage(err.response?.data?.error || "Erreur de génération");
    } finally {
      setLoading(false);
    }
  };

  const generateList = async () => {
    setLoading(true);
    setMessage("");
    try {
      const res = await api.post("/nutrition/shopping-list/generate", {
        meal_plan_id: plan?.id,
      });
      setShoppingList(res.data.shopping_list);
      setMessage(res.data.message);
    } catch (err) {
      setMessage(err.response?.data?.error || "Erreur de génération de la liste");
    } finally {
      setLoading(false);
    }
  };

  const dailyTotals = plan
    ? plan.meals.reduce(
        (acc, m) => {
          acc[m.day] = acc[m.day] || { kcal: 0, protein: 0, carbs: 0, fat: 0 };
          acc[m.day].kcal += m.totals.kcal;
          acc[m.day].protein += m.totals.protein;
          acc[m.day].carbs += m.totals.carbs;
          acc[m.day].fat += m.totals.fat;
          return acc;
        },
        {}
      )
    : {};

  return (
    <div className="container">
      <h1 className="page-title">Nutrition</h1>

      {message && <div className="card">{message}</div>}

      <div className="card">
        <h3>Objectif calorique : {user.daily_calories} kcal/jour</h3>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "end" }}>
          <div className="form-group" style={{ flex: 1 }}>
            <label>Nombre de jours</label>
            <input type="number" min="1" max="14" value={days} onChange={(e) => setDays(Number(e.target.value))} />
          </div>
          <button className="btn" onClick={generate} disabled={loading}>
            {loading ? "Génération..." : "Générer les menus"}
          </button>
        </div>
      </div>

      {plan && (
        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3>Plan alimentaire sur {plan.num_days} jours</h3>
            <button className="btn btn-secondary" onClick={generateList} disabled={loading}>
              Générer la liste de courses
            </button>
          </div>
          {Object.keys(dailyTotals).map((dayNum) => (
            <div key={dayNum} className="card day-card">
              <h4>Jour {dayNum}
                <span className="badge" style={{ marginLeft: "0.5rem" }}>
                  {Math.round(dailyTotals[dayNum].kcal)} kcal · P {Math.round(dailyTotals[dayNum].protein)}g · G {Math.round(dailyTotals[dayNum].carbs)}g · L {Math.round(dailyTotals[dayNum].fat)}g
                </span>
              </h4>
              {plan.meals.filter((m) => m.day === Number(dayNum)).map((meal) => (
                <div key={meal.id} className="exercise-row">
                  <div>
                    <strong>{meal.meal_type} : {meal.name}</strong>
                    <div className="muted" style={{ fontSize: "0.85rem" }}>
                      {meal.items.map((it) => `${it.food_name} (${it.quantity}g)`).join(" · ")}
                    </div>
                  </div>
                  <div className="muted" style={{ fontSize: "0.85rem" }}>{Math.round(meal.totals.kcal)} kcal</div>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}

      {shoppingList && (
        <div className="card">
          <h3>Liste de courses</h3>
          <ul>
            {shoppingList.items.map((item, idx) => (
              <li key={idx}>
                <input type="checkbox" style={{ width: "auto", marginRight: "0.5rem" }} />
                {item.name} : <strong>{item.qty_grams/1000 > 0 ? `${(item.qty_grams / 1000).toFixed(2)} kg` : `${item.qty_grams} g`}</strong>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
