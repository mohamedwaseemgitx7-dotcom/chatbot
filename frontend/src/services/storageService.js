/**
 * Crop photos in the private `farmer-images` bucket: <user_id>/<conversation_id>/<uuid>.<ext>.
 * Original file names are never used in paths. Storage re-checks size and type on the server.
 */
import { CloudError, getSession, unwrap } from "./supabaseService";
import { validateImage, validateImageContent } from "../utils/validateImage";

const BUCKET = "farmer-images";
const EXTENSION = { "image/jpeg": "jpg", "image/png": "png", "image/webp": "webp" };
const SIGNED_URL_SECONDS = 60 * 60;

const uuid = () => (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`);

/** Validates (type, size and actual file content) and uploads. @returns {Promise<string>} storage path */
export async function uploadImage(file, conversationId) {
  const problem = validateImage(file) || (await validateImageContent(file));
  if (problem) throw new CloudError("file-type", problem);

  const { supabase, userId } = await getSession();
  const path = `${userId}/${conversationId}/${uuid()}.${EXTENSION[file.type]}`;
  unwrap(
    await supabase.storage.from(BUCKET).upload(path, file, { contentType: file.type, upsert: false, cacheControl: "3600" }),
    "upload image",
  );
  return path;
}

/** Short-lived URL for showing a stored photo (the bucket is private). */
export async function getImageUrl(path) {
  const { supabase } = await getSession();
  const data = unwrap(await supabase.storage.from(BUCKET).createSignedUrl(path, SIGNED_URL_SECONDS), "sign image URL");
  return data?.signedUrl || null;
}

export async function deleteImage(path) {
  const { supabase } = await getSession();
  unwrap(await supabase.storage.from(BUCKET).remove([path]), "delete image");
}

/** Removes every photo stored for one conversation. */
export async function removeConversationFiles(conversationId) {
  const { supabase, userId } = await getSession();
  const folder = `${userId}/${conversationId}`;
  const files = unwrap(await supabase.storage.from(BUCKET).list(folder, { limit: 1000 }), "list images");
  if (files?.length) {
    unwrap(await supabase.storage.from(BUCKET).remove(files.map((f) => `${folder}/${f.name}`)), "delete images");
  }
}

/** Records the AI output for a photo message (a preliminary prediction, not a diagnosis). */
export async function saveImagePrediction({ messageId, path, result, status = "completed" }) {
  const { supabase } = await getSession();
  const confidence = typeof result?.confidence === "number" ? Math.min(1, Math.max(0, result.confidence)) : null;
  const row = {
    message_id: messageId,
    image_url: path,
    crop: result?.crop || null,
    prediction: result?.condition || null,
    confidence,
    status,
  };
  // Which model produced it (migration 20260924020000_prediction_versioning.sql adds these columns).
  const versioned = {
    ...row,
    model_name: result?.model?.name || null,
    model_version: result?.model?.version || null,
    dataset_version: result?.model?.datasetVersion || null,
  };
  let response = await supabase.from("image_predictions").insert(versioned);
  if (response.error?.code === "PGRST204") {
    // Database not migrated yet: keep the prediction, without version columns.
    response = await supabase.from("image_predictions").insert(row);
  }
  unwrap(response, "save image prediction");
}
