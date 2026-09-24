/** Mirrors the backend limits in backend/app/security/file_security.py. */
export const ACCEPTED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"];
export const MAX_IMAGE_BYTES = 5 * 1024 * 1024;

/** @returns {string | null} a user-facing error, or null when the file is fine */
export function validateImage(file) {
  if (!file) return "No photo was selected.";
  if (!ACCEPTED_IMAGE_TYPES.includes(file.type)) {
    if (/hei[cf]/i.test(file.type) || /\.hei[cf]$/i.test(file.name || "")) {
      // Some Android phones save HEIC; browsers there can't convert it (iPhones convert to JPG automatically).
      return "This photo is in HEIC format. Please take the photo again with the camera set to JPG, or choose a JPG photo.";
    }
    return "Please choose a JPG, PNG or WEBP photo.";
  }
  if (file.size > MAX_IMAGE_BYTES) {
    return "This photo is larger than 5 MB. Please choose a smaller photo.";
  }
  if (file.size === 0) return "This photo file is empty. Please choose another one.";
  return null;
}

/** Real format from the file's first bytes — the name and declared MIME type can be wrong or faked. */
async function sniffImageType(file) {
  const bytes = new Uint8Array(await file.slice(0, 12).arrayBuffer());
  const ascii = (from, to) => String.fromCharCode(...bytes.slice(from, to));
  if (bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) return "image/jpeg";
  if (bytes[0] === 0x89 && ascii(1, 4) === "PNG") return "image/png";
  if (ascii(0, 4) === "RIFF" && ascii(8, 12) === "WEBP") return "image/webp";
  return null;
}

/** @returns {Promise<string | null>} a user-facing error when the content isn't the image it claims to be */
export async function validateImageContent(file) {
  try {
    const actual = await sniffImageType(file);
    if (!actual) return "This file doesn't look like a photo. Please choose a JPG, PNG or WEBP image.";
    if (actual !== file.type) return "This photo's format doesn't match its file type. Please choose another photo.";
    return null;
  } catch {
    return "This photo couldn't be read. Please choose another one.";
  }
}
