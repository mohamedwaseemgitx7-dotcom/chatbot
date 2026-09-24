const timeFmt = new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" });
const dayFmt = new Intl.DateTimeFormat(undefined, { day: "numeric", month: "short" });
const yearFmt = new Intl.DateTimeFormat(undefined, { day: "numeric", month: "short", year: "numeric" });

export const sameDay = (a, b) => a.toDateString() === b.toDateString();

function isYesterday(date, now) {
  const y = new Date(now);
  y.setDate(now.getDate() - 1);
  return sameDay(date, y);
}

/** "10:42 am" — inside messages */
export const formatTime = (date) => timeFmt.format(date);

/** Sidebar: time for today, "Yesterday", otherwise the date */
export function formatListTime(date) {
  const now = new Date();
  if (sameDay(date, now)) return formatTime(date);
  if (isYesterday(date, now)) return "Yesterday";
  return date.getFullYear() === now.getFullYear() ? dayFmt.format(date) : yearFmt.format(date);
}

/** Divider label inside the chat */
export function formatDayLabel(date) {
  const now = new Date();
  if (sameDay(date, now)) return "Today";
  if (isYesterday(date, now)) return "Yesterday";
  return yearFmt.format(date);
}

/** 7 → "00:07" */
export function formatDuration(totalSeconds) {
  const s = Math.max(0, Math.floor(totalSeconds));
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

/** 1536000 → "1.5 MB" */
export function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** Maps our language names to BCP-47 tags for the `lang` attribute (fonts, screen readers). */
export const langTag = (language) => (language === "tamil" ? "ta" : "en");
