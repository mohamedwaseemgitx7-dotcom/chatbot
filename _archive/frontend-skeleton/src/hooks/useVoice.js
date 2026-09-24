import { useState } from 'react';

/**
 * useVoice Hook Skeleton
 * Manages browser MediaRecorder / SpeechRecognition lifecycle.
 */
export function useVoice() {
  const [isRecording, setIsRecording] = useState(false);

  const startRecording = () => {
    // SKELETON: To be implemented in execution phase
  };

  const stopRecording = () => {
    // SKELETON: To be implemented in execution phase
  };

  return { isRecording, startRecording, stopRecording };
}
