import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.jsx";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  });
}

// Empêche le pavé tactile / la molette de modifier les champs numériques (on tape uniquement)
document.addEventListener(
  "wheel",
  (e) => {
    const el = e.target;
    if (el && el.matches && el.matches('input[type="number"]')) {
      e.preventDefault();
      el.blur();
    }
  },
  { passive: false }
);
