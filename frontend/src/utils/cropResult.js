/** Display helpers for image-analysis results, shared by the result card and the sidebar preview. */
const HEALTHY = /^(healthy|no[\s_-]?disease|normal)$/i;

const titleCase = (s) => s.replace(/[_-]+/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

export const isHealthy = (result) => HEALTHY.test(result?.condition || "");

export const cropName = (result) => (result?.crop ? titleCase(result.crop) : "Not identified");

export function conditionName(result) {
  if (!result?.condition) return "Not identified";
  return isHealthy(result) ? "No disease detected" : titleCase(result.condition);
}

/** Words, not certainty: the percentage is an AI estimate, not a diagnosis. */
export function confidenceLabel(confidence) {
  if (confidence >= 0.8) return "High";
  if (confidence >= 0.55) return "Moderate";
  return "Low";
}
