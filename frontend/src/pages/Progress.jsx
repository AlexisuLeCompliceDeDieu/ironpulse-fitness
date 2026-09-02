import { useEffect, useState } from "react";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";
import api from "../api.js";
import PageHero, { FIT_IMAGES } from "../components/PageHero.jsx";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler);

export default function Progress({ user }) {
  const [weights, setWeights] = useState([]);
  const [exerciseData, setExerciseData] = useState(null);
  const [exercises, setExercises] = useState([]);
  const [selectedExercise, setSelectedExercise] = useState(null);

  useEffect(() => {
    api.get("/profile/weight").then((res) => setWeights(res.data.entries)).catch(() => {});
    api.get("/exercises/").then((res) => setExercises(res.data.exercises)).catch(() => {});
  }, []);

  const loadExercise = (id) => {
    setSelectedExercise(id);
    if (!id) {
      setExerciseData(null);
      return;
    }
    api.get(`/progress/exercises/${id}`).then((res) => setExerciseData(res.data.data)).catch(() => setExerciseData([]));
  };

  const weightChart = {
    labels: weights.map((w) => w.date),
    datasets: [
      {
        label: "Poids (kg)",
        data: weights.map((w) => w.weight),
        borderColor: "#f97316",
        backgroundColor: "rgba(249, 115, 22, 0.15)",
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointBackgroundColor: "#fdba74",
      },
    ],
  };

  const exerciseChart = exerciseData && {
    labels: exerciseData.map((d) => d.date),
    datasets: [
      {
        label: "Poids max (kg)",
        data: exerciseData.map((d) => d.max_weight),
        borderColor: "#f97316",
        backgroundColor: "rgba(249, 115, 22, 0.1)",
        fill: true,
        tension: 0.4,
      },
      {
        label: "Répétitions totales",
        data: exerciseData.map((d) => d.total_reps),
        borderColor: "#fdba74",
        backgroundColor: "rgba(253, 186, 116, 0.1)",
        fill: false,
        tension: 0.4,
      },
      {
        label: "Volume total (kg)",
        data: exerciseData.map((d) => d.total_volume),
        borderColor: "#fb923c",
        backgroundColor: "rgba(251, 146, 60, 0.1)",
        yAxisID: "y1",
        fill: false,
        tension: 0.4,
      },
    ],
  };

  const comparison = exerciseData && exerciseData.length >= 2
    ? {
        first: exerciseData[0],
        last: exerciseData[exerciseData.length - 1],
        deltaWeight: exerciseData[exerciseData.length - 1].max_weight - exerciseData[0].max_weight,
        deltaReps: exerciseData[exerciseData.length - 1].total_reps - exerciseData[0].total_reps,
        deltaVolume: exerciseData[exerciseData.length - 1].total_volume - exerciseData[0].total_volume,
      }
    : null;

  return (
    <div className="container">
      <PageHero
        title="📈 Analyse de progression"
        subtitle="Suivez l'évolution de vos performances et de votre poids dans le temps."
        image={FIT_IMAGES.progress}
        tags={[`⚖️ ${user.weight} kg actuel`, `🎯 ${user.target_weight} kg cible`, `🔥 ${user.daily_calories} kcal/jour`]}
      />

      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h3 style={{ marginTop: 0 }}>⚖️ Évolution du poids</h3>
        </div>
        {weights.length === 0 ? (
          <p className="muted">Aucune donnée de poids. Ajoutez votre poids dans le profil.</p>
        ) : (
          <Line data={weightChart} />
        )}
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>🏋️ Progression par exercice</h3>
        <label>Choisir un exercice</label>
        <select value={selectedExercise || ""} onChange={(e) => loadExercise(Number(e.target.value))}>
          <option value="">-- Choisir un exercice --</option>
          {exercises.map((ex) => (
            <option key={ex.id} value={ex.id}>{ex.name}</option>
          ))}
        </select>
        {exerciseData && exerciseData.length > 0 && (
          <Line data={exerciseChart} options={{ scales: { y1: { position: "right", grid: { display: false } } }, plugins: { legend: { labels: { usePointStyle: true } } } }} />
        )}
        {exerciseData && exerciseData.length === 0 && (
          <p className="muted">Aucune donnée pour cet exercice.</p>
        )}
      </div>

      {comparison && (
        <div className="pink-card card">
          <h3 style={{ marginTop: 0, color: "#fff" }}>⭐ Comparaison de vos performances</h3>
          <div className="grid grid-3">
            <div>
              <p className="muted" style={{ margin: 0 }}>Poids max</p>
              <p style={{ fontWeight: 800, fontSize: "1.2rem", margin: "0.2rem 0" }}>
                {comparison.first.max_weight} → {comparison.last.max_weight} kg
                {comparison.deltaWeight !== 0 && (
                  <span style={{ color: comparison.deltaWeight > 0 ? "#bbf7d0" : "#fecaca" }}>
                    {" "}({comparison.deltaWeight > 0 ? "+" : ""}{comparison.deltaWeight} kg)
                  </span>
                )}
              </p>
            </div>
            <div>
              <p className="muted" style={{ margin: 0 }}>Répétitions</p>
              <p style={{ fontWeight: 800, fontSize: "1.2rem", margin: "0.2rem 0" }}>
                {comparison.first.total_reps} → {comparison.last.total_reps}
                {comparison.deltaReps !== 0 && (
                  <span style={{ color: comparison.deltaReps > 0 ? "#bbf7d0" : "#fecaca" }}>
                    {" "}({comparison.deltaReps > 0 ? "+" : ""}{comparison.deltaReps})
                  </span>
                )}
              </p>
            </div>
            <div>
              <p className="muted" style={{ margin: 0 }}>Volume total</p>
              <p style={{ fontWeight: 800, fontSize: "1.2rem", margin: "0.2rem 0" }}>
                {comparison.first.total_volume} → {comparison.last.total_volume} kg
                {comparison.deltaVolume !== 0 && (
                  <span style={{ color: comparison.deltaVolume > 0 ? "#bbf7d0" : "#fecaca" }}>
                    {" "}({comparison.deltaVolume > 0 ? "+" : ""}{comparison.deltaVolume} kg)
                  </span>
                )}
              </p>
            </div>
          </div>
          <p className="muted" style={{ fontSize: "0.85rem", marginTop: "0.5rem" }}>
            📅 {comparison.first.date} → {comparison.last.date}
          </p>
        </div>
      )}
    </div>
  );
}
