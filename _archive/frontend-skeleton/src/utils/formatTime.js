/**
 * Format timestamp into friendly 12-hour WhatsApp-like format (e.g. 10:32 AM)
 */
export function formatTime(isoString) {
  if (!isoString) return '';
  const date = new Date(isoString);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}
