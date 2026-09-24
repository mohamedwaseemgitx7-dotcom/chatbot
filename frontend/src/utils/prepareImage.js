import { ACCEPTED_IMAGE_TYPES } from "./validateImage";

/**
 * Phone cameras produce 5–15 MB photos, but the model only looks at 224 px. Large photos are downscaled
 * in the browser (longest side 1600 px, JPEG) before validation and upload: they no longer hit the
 * 5 MB limit, and farmers on mobile data upload ~300 KB instead of several MB.
 * The browser applies the photo's EXIF rotation when drawing, so portrait shots stay upright.
 * If the image can't be decoded, the original file is returned and normal validation explains the problem.
 */
const MAX_SIDE = 1600;
const RESIZE_ABOVE_BYTES = 1.5 * 1024 * 1024;
const JPEG_QUALITY = 0.88;

function loadImage(url) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("decode failed"));
    img.src = url;
  });
}

/** @param {File} file @returns {Promise<File>} */
export async function prepareImage(file) {
  if (!file || !ACCEPTED_IMAGE_TYPES.includes(file.type) || file.size <= RESIZE_ABOVE_BYTES) return file;
  const url = URL.createObjectURL(file);
  try {
    const img = await loadImage(url);
    const scale = Math.min(1, MAX_SIDE / Math.max(img.naturalWidth, img.naturalHeight));
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(img.naturalWidth * scale));
    canvas.height = Math.max(1, Math.round(img.naturalHeight * scale));
    const context = canvas.getContext("2d");
    if (!context) return file;
    context.fillStyle = "#ffffff"; // PNG transparency → white, not black, in the JPEG
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.drawImage(img, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", JPEG_QUALITY));
    if (!blob || blob.size >= file.size) return file;
    const name = `${file.name.replace(/\.[^.]+$/, "") || "photo"}.jpg`;
    return new File([blob], name, { type: "image/jpeg", lastModified: Date.now() });
  } catch {
    return file;
  } finally {
    URL.revokeObjectURL(url);
  }
}
