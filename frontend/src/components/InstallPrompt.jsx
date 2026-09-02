import { useState, useEffect } from "react";

const isIos = () =>
  /iphone|ipad|ipod/i.test(navigator.userAgent) && !window.MSStream;
const isStandalone = () =>
  window.matchMedia("(display-mode: standalone)").matches ||
  navigator.standalone === true;

export default function InstallPrompt() {
  const [promptEvt, setPromptEvt] = useState(null);
  const [show, setShow] = useState(false);
  const ios = isIos();

  useEffect(() => {
    if (isStandalone()) return;

    const handler = (e) => {
      e.preventDefault();
      setPromptEvt(e);
      setShow(true);
    };
    window.addEventListener("beforeinstallprompt", handler);

    // iOS : pas d'événement natif, afficher le guide après un délai
    let timer = null;
    if (isIos()) {
      timer = setTimeout(() => {
        if (!isStandalone()) setShow(true);
      }, 4000);
    }

    return () => {
      window.removeEventListener("beforeinstallprompt", handler);
      if (timer) clearTimeout(timer);
    };
  }, []);

  if (!show) return null;

  const install = async () => {
    if (promptEvt) {
      promptEvt.prompt();
      const choice = await promptEvt.userChoice;
      if (choice.outcome === "accepted") setShow(false);
    }
  };

  return (
    <div className="install-banner">
      <div className="install-text">
        <strong>Installer IRONPULSE ?</strong>
        <p className="muted" style={{ fontSize: "0.85rem", margin: "0.2rem 0 0 0" }}>
          {ios
            ? "Ajoutez l'application à votre écran d'accueil pour l'ouvrir comme une vraie app."
            : "Ajoutez l'application à votre écran d'accueil pour un accès rapide."}
        </p>
        {ios && (
          <p className="muted" style={{ fontSize: "0.78rem", margin: "0.3rem 0 0 0" }}>
            📱 Safari : touchez <strong>Partager</strong> → <strong>Sur l'écran d'accueil</strong>
          </p>
        )}
      </div>
      <div className="install-actions">
        {!ios && (
          <button className="btn btn-sm" style={{ background: "var(--primary)", color: "#fff" }} onClick={install}>
            Installer
          </button>
        )}
        <button className="btn btn-sm btn-ghost" onClick={() => setShow(false)}>
          Plus tard
        </button>
      </div>
    </div>
  );
}
