/**
 * Detects whether a message is Tamil (script), Tanglish (Tamil in Latin letters) or English.
 * Rule-based on purpose: fast, explainable and easy to replace with the Python classifier later.
 */

const TAMIL_CHAR = /[\u0B80-\u0BFF]/g;
const LATIN_CHAR = /[A-Za-z]/g;

// Common Tanglish words a farmer is likely to type. Keep them lowercase.
const TANGLISH_WORDS = new Set([
  "vanakkam", "vanakam", "naan", "nan", "ungal", "unga", "enna", "yenna", "epdi", "eppadi", "eppo", "yeppo",
  "enga", "evlo", "iruku", "irukku", "illa", "venum", "vendam", "sollunga", "solunga", "nandri", "romba",
  "konjam", "anna", "akka", "ayya", "pathi", "podanum", "pannanum", "pannalaam", "poochi", "uram", "thanni",
  "mazhai", "nel", "nellu", "vivasayam", "vivasayi", "payir", "ilai", "marundhu", "vilai", "seri", "sari",
  "da", "machan", "inniku", "naalaiku", "ippo", "nalla", "iruken", "irukeenga", "aagudhu", "varudhu",
]);

/** @returns {"tamil" | "tanglish" | "english"} */
export function detectLanguage(text) {
  const tamilCount = (text.match(TAMIL_CHAR) || []).length;
  const latinCount = (text.match(LATIN_CHAR) || []).length;
  const letters = tamilCount + latinCount;
  if (letters === 0) return "english";

  if (tamilCount / letters >= 0.3) return "tamil";

  const words = text.toLowerCase().match(/[a-z]+/g) || [];
  const tanglishHits = words.filter((w) => TANGLISH_WORDS.has(w)).length;
  // One hit is enough for short messages ("vanakkam"), longer ones need ~20% Tanglish words.
  if (tanglishHits >= 1 && (words.length <= 3 || tanglishHits / words.length >= 0.2)) return "tanglish";

  return "english";
}
