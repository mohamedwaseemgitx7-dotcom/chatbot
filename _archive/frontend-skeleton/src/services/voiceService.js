import { API_BASE_URL } from './api';

/**
 * Voice Service Skeleton
 * Interfaces with POST /api/voice/transcribe
 */
export async function transcribeAudio(audioBlob) {
  // SKELETON: Business logic to be implemented in feature phase
  const formData = new FormData();
  formData.append('audio', audioBlob, 'recording.webm');

  const response = await fetch(`${API_BASE_URL}/api/voice/transcribe`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error('Voice transcription failed');
  }

  return response.json();
}
