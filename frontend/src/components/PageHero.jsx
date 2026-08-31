import { useState } from "react";

export const FIT_IMAGES = {
  hero: "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=400&q=60&auto=format&fit=crop",
  training: "https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?w=400&q=60&auto=format&fit=crop",
  cardio: "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=400&q=60&auto=format&fit=crop",
  nutrition: "https://images.unsplash.com/photo-1490645935967-10de6ba17061?w=400&q=60&auto=format&fit=crop",
  progress: "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?w=400&q=60&auto=format&fit=crop",
  profile: "https://images.unsplash.com/photo-1526506118085-60ce8714f8c5?w=400&q=60&auto=format&fit=crop",
  auth: "https://images.unsplash.com/photo-1540497077202-7c8a3999166f?w=800&q=60&auto=format&fit=crop",
  dumbbell: "https://images.unsplash.com/photo-1583454110551-21f2fa2afe61?w=400&q=60&auto=format&fit=crop",
};

export default function PageHero({ title, subtitle, image = "", tags = [], tone = "default" }) {
  const [imgOk, setImgOk] = useState(true);

  return (
    <div className={"hero " + (tone !== "default" ? tone : "")}>
      <div className="hero-copy">
        <h1>{title}</h1>
        {subtitle && <p>{subtitle}</p>}
        {tags.length > 0 && (
          <div className="hero-badges">
            {tags.map((t, i) => (
              <span className="hero-tag" key={i}>{t}</span>
            ))}
          </div>
        )}
      </div>
      {image && imgOk && (
        <div className="hero-img-container">
          <img
            src={image}
            alt=""
            loading="lazy"
            onError={() => setImgOk(false)}
          />
        </div>
      )}
    </div>
  );
}
