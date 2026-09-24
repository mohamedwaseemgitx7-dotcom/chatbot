/**
 * Row shapes of the Supabase tables (see supabase/migrations). JSDoc types for editor hints.
 *
 * @typedef {"english" | "tamil" | "tanglish"} Language
 *
 * @typedef {object} ConversationRow
 * @property {string} id
 * @property {string} user_id
 * @property {string} title
 * @property {Language | null} language
 * @property {string} created_at
 * @property {string} updated_at
 *
 * @typedef {object} MessageRow
 * @property {string} id
 * @property {string} conversation_id
 * @property {"user" | "assistant" | "system"} sender
 * @property {string} message
 * @property {Language | null} language
 * @property {string | null} intent
 * @property {number | null} confidence  0–1
 * @property {"text" | "image" | "voice" | "system"} message_type
 * @property {Record<string, unknown>} metadata  photo details / analysis result, rendered as UI — never shown raw
 * @property {string} created_at
 *
 * @typedef {object} KnowledgeRow
 * @property {string} id
 * @property {string} crop
 * @property {string} topic
 * @property {string | null} subtopic
 * @property {Language} language
 * @property {string} title
 * @property {string} content
 * @property {string[]} keywords
 * @property {string | null} source
 * @property {boolean} verification_required
 *
 * @typedef {object} ImagePredictionRow
 * @property {string} id
 * @property {string} message_id
 * @property {string} image_url  Storage path in the farmer-images bucket
 * @property {string | null} crop
 * @property {string | null} prediction
 * @property {number | null} confidence
 * @property {"processing" | "completed" | "failed"} status
 *
 * @typedef {object} FeedbackRow
 * @property {string} id
 * @property {string} message_id
 * @property {string} user_id
 * @property {1 | 2 | 3 | 4 | 5} rating
 * @property {string | null} feedback_text
 *
 * @typedef {object} VoiceTranscriptionRow
 * @property {string} id
 * @property {string} message_id
 * @property {string | null} audio_url
 * @property {string | null} transcript
 * @property {Language | null} language
 * @property {number | null} confidence
 * @property {"processing" | "completed" | "failed"} status
 */
export {};
