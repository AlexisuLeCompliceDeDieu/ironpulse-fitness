import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";

const STORAGE_KEY = "ironpulse_tour_done_v2";

/* ------------------------------------------------------------------
   Définition du parcours guidé.
   route      : page (onglet) à afficher pour cette étape
   target     : sélecteur CSS d'un élément de la page (ex: data-tour)
   tab        : route d'onglet → la cible est l'onglet (barre mobile OU menu du haut)
   title/text : contenu
   placement  : top / bottom / left / right / center
   ------------------------------------------------------------------ */
const STEPS = [
  { route: null, target: null, placement: "center", title: "👋 Bienvenue sur IRONPULSE !", text:
      "Ce petit tour guidé vous explique tout, étape par étape. Cliquez sur « Suivant » pour continuer, et l'application changera d'onglet toute seule. Bon entraînement !" },
  { route: "/", target: "[data-tour='today']", placement: "bottom", title: "🏠 L'accueil", text:
      "Ici votre résumé : objectif, niveau, séances réalisées, poids, et le programme du jour. C'est le point de départ de chaque visite." },
  { route: "/training", tab: "/training", placement: "top", title: "🗓️ Onglet Programme", text:
      "Votre plan d'entraînement personnalisé, généré automatiquement selon votre objectif, votre niveau, votre matériel et vos séances par semaine. Chaque jour a ses exercices." },
  { route: "/session", tab: "/session", placement: "top", title: "📋 Onglet Séance", text:
      "Pendant l'entraînement, enregistrez vos charges, séries, répétitions et votre ressenti. Ces données servent à ajuster votre programme." },
  { route: "/nutrition", tab: "/nutrition", placement: "top", title: "🥗 Onglet Nutrition", text:
      "Votre plan de repas et vos calories quotidiennes, adaptés à votre objectif (prise de masse, perte de poids…) et à vos préférences alimentaires." },
  { route: "/machines", tab: "/machines", placement: "top", title: "🏋️ Onglet Machines", text:
      "Le catalogue complet de la salle (70 machines) avec conseils d'utilisation et photos. Parfait pour savoir comment utiliser chaque machine." },
  { route: "/social", tab: "/social", placement: "top", title: "🏆 Onglet Classement", text:
      "Le classement entre amis ! Plus vous vous entraînez, plus vous montez dans le classement. La motivation en plus." },
  { route: "/friends", tab: "/friends", placement: "top", title: "👥 Onglet Amis", text:
      "Ajoutez vos amis ici. Ils doivent accepter votre demande avant d'apparaître dans le classement. Cherchez un pseudo et envoyez l'invitation." },
  { route: "/progress", tab: "/progress", placement: "top", title: "📈 Onglet Progression", text:
      "Visualisez vos progrès avec des graphiques : évolution du poids, volume soulevé, ressenti. Motivant de voir la courbe monter !" },
  { route: "/profile", target: "[data-tour='weight']", placement: "top", title: "👤 Profil : le poids du jour", text:
      "Complétez vos infos ici. Important : vous enregistrez votre POIDS DU JOUR dans la section « Enregistrer mon poids du jour ». Un seul poids par jour. Si vous vous êtes trompé, entrez la nouvelle valeur, elle remplacera la précédente." },
  { route: "/", target: null, placement: "center", title: "🎉 C'est tout !", text:
      "Vous savez maintenant utiliser IRONPULSE. Si vous avez un doute à nouveau, un bouton « ❓ » reste disponible en bas de l'écran pour relancer ce guide. Bonne chance dans votre transformation ! 💪" },
];

export function markTourDone() {
  try { localStorage.setItem(STORAGE_KEY, "1"); } catch (e) {}
}
export function isTourDone() {
  try { return localStorage.getItem(STORAGE_KEY) === "1"; } catch (e) { return false; }
}

export default function TourGuide({ onClose }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [index, setIndex] = useState(0);
  const [rect, setRect] = useState(null);
  const [fallback, setFallback] = useState(false);
  const [viewW, setViewW] = useState(window.innerWidth);
  const measureTimer = useRef(null);
  const tooltipRef = useRef(null);
  const [tipSize, setTipSize] = useState(null);
  const step = STEPS[index];

  const isMobile = viewW < 768;

  // Placement effectif : les étapes "onglet" sur desktop visent le menu du haut
  // (tout en haut) → phylactère placé SOUS la barre.
  const effPlacement =
    step?.tab && !isMobile && step?.placement !== "center" ? "bottom" : step?.placement;
  const centerMode = effPlacement === "center" || fallback;

  // Sélecteur effectif de la cible
  const targetSelector = step?.tab
    ? isMobile
      ? `.mobile-tab[href='${step.tab}']`
      : `.nav-item:has(a[href='${step.tab}'])`
    : step?.target;

  // Resize -> recalcul
  useEffect(() => {
    const onResize = () => setViewW(window.innerWidth);
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  // Mesurer la taille réelle du phylactère pour le garder toujours dans l'écran
  useLayoutEffect(() => {
    if (!tooltipRef.current) return;
    setTipSize({
      w: tooltipRef.current.offsetWidth,
      h: tooltipRef.current.offsetHeight,
    });
  }, [index, step]);

  // Naviguer vers la page de l'étape (sauf pour les étapes "center")
  useEffect(() => {
    if (step && step.route && step.route !== location.pathname) {
      navigate(step.route);
    }
  }, [index]);

  // Mesurer la cible une fois la page affichée
  useLayoutEffect(() => {
    if (measureTimer.current) clearTimeout(measureTimer.current);
    setRect(null);
    setFallback(false);
    if (!step || centerMode || !targetSelector) {
      return;
    }
    let attempts = 0;
    const tryMeasure = () => {
      const el = document.querySelector(targetSelector);
      if (el) {
        const r = el.getBoundingClientRect();
        if (r.width > 0 && r.height > 0) {
          setRect({ top: r.top, left: r.left, width: r.width, height: r.height });
          return;
        }
      }
      attempts += 1;
      if (attempts > 12) {
        setRect(null);
        setFallback(true);
      } else {
        measureTimer.current = setTimeout(tryMeasure, 80);
      }
    };
    measureTimer.current = setTimeout(tryMeasure, 120);
    return () => {
      if (measureTimer.current) clearTimeout(measureTimer.current);
    };
  }, [step, targetSelector, location.pathname, index, centerMode]);

  const prev = () => index > 0 && setIndex(index - 1);
  const next = () => {
    if (index < STEPS.length - 1) setIndex(index + 1);
    else { markTourDone(); onClose(); }
  };
  const skip = () => { markTourDone(); onClose(); };

  const vw = window.innerWidth;
  const vh = window.innerHeight;

  // Panneaux d'assombrissement autour de la cible (coupure)
  const panels = (!centerMode && rect)
    ? [
        { top: 0, left: 0, w: vw, h: rect.top },
        { top: rect.top + rect.height, left: 0, w: vw, h: Math.max(vh - (rect.top + rect.height), 0) },
        { top: rect.top, left: 0, w: rect.left, h: rect.height },
        { top: rect.top, left: rect.left + rect.width, w: Math.max(vw - (rect.left + rect.width), 0), h: rect.height },
      ]
    : null;

  // Taille du phylactère (ou estimation avant mesure), + marge de sécurité dans l'écran
  const tw = tipSize ? tipSize.w : Math.min(360, vw - 20);
  const th = tipSize ? tipSize.h : 260;
  const M = 14; // marge min. avec les bords de l'écran

  // Position du phylactère : on place d'abord selon le placement, puis on CLAMPE
  // le coin haut-gauche pour que TOUT le phylactère reste dans le viewport (sans transform).
  let tipX, tipY;
  if (centerMode || !rect) {
    // Centré
    tipX = (vw - tw) / 2;
    tipY = (vh - th) / 2;
  } else if (effPlacement === "bottom") {
    tipX = rect.left + rect.width / 2 - tw / 2;
    tipY = rect.top + rect.height + M;
  } else if (effPlacement === "top") {
    tipX = rect.left + rect.width / 2 - tw / 2;
    tipY = rect.top - M - th;
  } else if (effPlacement === "left") {
    tipX = rect.left - M - tw;
    tipY = rect.top + rect.height / 2 - th / 2;
  } else { // right
    tipX = rect.left + rect.width + M;
    tipY = rect.top + rect.height / 2 - th / 2;
  }
  // Clamp final : le phylactère reste entièrement visible et cliquable
  tipX = Math.max(M, Math.min(tipX, vw - tw - M));
  tipY = Math.max(M, Math.min(tipY, vh - th - M));
  // Si la cible est en haut et le phylactère sous elle dépasse à l'écran, rebasculer proprement
  if (effPlacement === "bottom" && rect && tipY + th > vh - M && rect.top - M - th > M) {
    tipY = rect.top - M - th;
    tipY = Math.max(M, Math.min(tipY, vh - th - M));
  }

  return (
    <div className="tour-root">
      {panels && panels.map((p, i) => (
        <div key={i} className="tour-dim" style={{ top: p.top, left: p.left, width: p.w, height: p.h }} />
      ))}

      {!centerMode && rect && (
        <>
          <div className="tour-target-frame"
            style={{ top: rect.top, left: rect.left, width: rect.width, height: rect.height }} />
          <div className="tour-arrow"
            style={{
              left: rect.left + rect.width / 2,
              top: effPlacement === "top" ? rect.top - 8 : rect.top + rect.height + 8,
            }}
            data-dir={effPlacement} />
        </>
      )}

      <div
        ref={tooltipRef}
        className="tour-tooltip"
        style={{ left: tipX, top: tipY }}
        data-placement={centerMode ? "center" : effPlacement}
      >
        <span className="tour-step-count">{index + 1} / {STEPS.length}</span>
        <h3 className="tour-title">{step.title}</h3>
        <p className="tour-text">{step.text}</p>
        <div className="tour-actions">
          {index > 0 && (
            <button className="btn btn-secondary btn-sm" onClick={prev}>← Précédent</button>
          )}
          <button className="btn btn-sm tour-next" onClick={next}>
            {index === STEPS.length - 1 ? "Terminer" : "Suivant →"}
          </button>
        </div>
        <button className="tour-skip" onClick={skip}>Passer le guide</button>
      </div>
    </div>
  );
}
