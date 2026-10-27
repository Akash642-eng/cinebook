import { useEffect, useState } from "react";
import "./CinemaIntro.css";

type Props = {
  onEnter: () => void;
};

export default function CinemaIntro({ onEnter }: Props) {
  const [leaving, setLeaving] = useState(false);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Enter" && !leaving) {
        setLeaving(true);
        window.setTimeout(onEnter, 650);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [leaving, onEnter]);

  function enterCinema() {
    if (leaving) return;
    setLeaving(true);
    window.setTimeout(onEnter, 650);
  }

  return (
    <section
      className={`cinema-intro${leaving ? " cinema-intro-leaving" : ""}`}
      aria-label="Welcome to CineBook"
    >
      <div className="intro-grain" aria-hidden="true" />
      <div className="intro-spotlight" aria-hidden="true" />
      <div className="intro-content">
        <div className="intro-kicker"><span /> THE MOVIE NIGHT STARTS HERE</div>
        <div className="intro-reel" aria-hidden="true">
          <div className="reel-core">C<span>✦</span></div>
        </div>
        <div className="intro-wordmark">Cine<span>Book</span></div>
        <p className="intro-tagline">Every seat has a story.</p>
        <button className="intro-enter" onClick={enterCinema}>
          Enter the experience <span aria-hidden="true">↗</span>
        </button>
        <div className="intro-footnote">DISCOVER · CHOOSE · EXPERIENCE</div>
      </div>
      <div className="intro-frame intro-frame-left" aria-hidden="true" />
      <div className="intro-frame intro-frame-right" aria-hidden="true" />
    </section>
  );
}
