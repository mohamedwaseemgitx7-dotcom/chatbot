import { InfoIcon } from "./Icons";
import RichText from "./RichText";
import SourceList from "./SourceList";
import { conditionName, confidenceLabel, cropName, isHealthy } from "../utils/cropResult";
import "./ImageResultCard.css";

export default function ImageResultCard({ result }) {
  const crop = cropName(result);
  const healthy = isHealthy(result);
  const condition = conditionName(result);
  const confidence = typeof result?.confidence === "number" ? result.confidence : null;
  const pct = confidence === null ? null : Math.round(confidence * 100);
  const causes = Array.isArray(result?.causes) ? result.causes : [];
  const nextSteps = Array.isArray(result?.nextSteps) ? result.nextSteps : [];
  const sources = Array.isArray(result?.sources) ? result.sources : [];

  return (
    <article className="result-card" aria-label="Crop photo analysis">
      <header className="result-card__header">
        <h3 className="result-card__title">Crop analysis</h3>
        <span className="result-card__badge">Preliminary AI prediction</span>
      </header>

      <dl className="result-card__facts">
        <div>
          <dt>Crop</dt>
          <dd>{crop}</dd>
        </div>
        <div>
          <dt>Possible condition</dt>
          <dd className={healthy ? "result-card__healthy" : undefined}>{condition}</dd>
        </div>
        {pct !== null && (
          <div className="result-card__confidence">
            <dt>AI confidence</dt>
            <dd>
              {pct}% <span className="result-card__level">· {confidenceLabel(confidence)}</span>
              <span className="result-card__meter" aria-hidden="true"><span style={{ width: `${pct}%` }} /></span>
            </dd>
          </div>
        )}
      </dl>

      {causes.length > 0 && (
        <section className="result-card__section">
          <h4>Possible causes</h4>
          <ul>{causes.map((c, i) => <li key={i}>{c}</li>)}</ul>
        </section>
      )}

      {nextSteps.length > 0 && (
        <section className="result-card__section">
          <h4>What you can do</h4>
          {nextSteps.map((s, i) => <RichText key={i} text={s} />)}
        </section>
      )}

      {healthy ? null : nextSteps.length === 0 && (
        <p className="result-card__none">No verified treatment information is available for this condition yet. Please show the plant to your local agriculture officer.</p>
      )}
      <SourceList sources={sources} />

      <p className="result-card__note">
        <InfoIcon />
        <span>
          {result?.disclaimer ||
            "This is an AI-assisted preliminary assessment. Confirm with your local agriculture officer before using any pesticide or chemical."}
        </span>
      </p>
    </article>
  );
}
