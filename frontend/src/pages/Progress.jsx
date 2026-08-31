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
} from "chart.js";
import api from "../api.js";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

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
        borderColor: "#2563eb",
        backgroundColor: "rgba(37, 99, 235, 0.1)",
        fill: true,
      },
    ],
  };

  const exerciseChart = exerciseData && {
    labels: exerciseData.map((d) => d.date),
    datasets: [
      {
        label: "Poids max (kg)",
        data: exerciseData.map((d) => d.max_weight),
        borderColor: "#16a34a",
        backgroundColor: "rgba(22, 163, 74, 0.1)",
        fill: true,
      },
      {
        label: "Volume total (kg)",
        data: exerciseData.map((d) => d.total_volume),
        borderColor: "#dc2626",
        backgroundColor: "rgba(220, 38, 38, 0.1)",
        yAxisID: "y1",
        fill: false,
      },
    ],
  };

  return (
    <div className="container">
      <h1 className="page-title">Analyse de progression</h1>

      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h3>Évolution du poids</h3>
          {weights.length === 0 && <p className="muted">Aucune donnée de poids.</p>}
        </div>
        {weights.length > 0 && <Line data={weightChart} />}
      </div>

      <div className="card">
        <h3>Progression par exercice</h3>
        <select value={selectedExercise || ""} onChange={(e) => loadExercise(Number(e.target.value))}>
          <option value="">-- Choisir un exercice --</option>
          {exercises.map((ex) => (
            <option key={ex.id} value={ex.id}>{ex.name}</option>
          ))}
        </select>
        {exerciseData && exerciseData.length > 0 && (
          <Line data={exerciseChart} options={{ scales: { y1: { position: "right" } } }} />
        )}
        {exerciseData && exerciseData.length === 0 && (
          <p className="muted">Aucune donnée pour cet exercice.</p>
        )}
      </div>

      <div className="card">
        <h3>Informations</h3>
        <p className="muted">Poids actuel : <strong>{user.weight} kg</strong> · Poids cible : <strong>{user.target_weight} kg</strong></p>
        <p className="muted">Calorie quotidienne : <strong>{user.daily_calories} kcal</strong></p>
      </div>
    </div>
  );
}
