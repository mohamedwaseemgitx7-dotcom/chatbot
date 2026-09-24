import { LogoMark } from "./Icons";
import "./WelcomeScreen.css";

const TOPICS = ["Crop diseases", "Pests", "Fertilizers", "Soil", "Irrigation", "Government schemes", "Crop management"];

const EXAMPLES = [
  { text: "My rice leaves are turning yellow", lang: "en", label: "English" },
  { text: "நெல் இலை மஞ்சளாகுது ஏன்?", lang: "ta", label: "தமிழ்" },
  { text: "nel la poochi iruku enna panrathu?", lang: "en", label: "Tanglish" },
];

export default function WelcomeScreen({ onExample, disabled }) {
  return (
    <section className="welcome" aria-labelledby="welcome-title">
      <LogoMark size={48} />
      <h2 id="welcome-title" className="welcome__title">FarmerAssist</h2>
      <p className="welcome__lead">Your local AI assistant for agriculture. Ask in Tamil, English or Tanglish.</p>

      <ul className="welcome__topics" aria-label="Topics you can ask about">
        {TOPICS.map((t) => <li key={t}>{t}</li>)}
      </ul>

      <div className="welcome__examples">
        <h3 className="welcome__examples-title">Try asking</h3>
        <div className="welcome__grid">
          {EXAMPLES.map((ex) => (
            <button key={ex.text} type="button" className="example-card" onClick={() => onExample(ex.text)} disabled={disabled}>
              <span className="example-card__lang">{ex.label}</span>
              <span className="example-card__text" lang={ex.lang}>{ex.text}</span>
            </button>
          ))}
        </div>
      </div>

      <p className="welcome__hint">You can also send a crop photo or a voice question.</p>
    </section>
  );
}
