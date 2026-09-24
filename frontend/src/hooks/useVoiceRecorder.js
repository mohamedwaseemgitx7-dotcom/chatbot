import { useCallback, useEffect, useRef, useState } from "react";

const MIME_CANDIDATES = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"];

const voiceSupported =
  typeof window !== "undefined" &&
  typeof window.MediaRecorder !== "undefined" &&
  !!navigator.mediaDevices?.getUserMedia;

/** Turns getUserMedia errors into messages a farmer can act on. */
function micErrorMessage(error) {
  switch (error?.name) {
    case "NotAllowedError":
    case "SecurityError":
      return "Microphone access is blocked. Allow the microphone for this site in your browser settings, then try again.";
    case "NotFoundError":
    case "OverconstrainedError":
      return "No microphone was found on this device.";
    case "NotReadableError":
      return "The microphone is being used by another app. Close it and try again.";
    default:
      return "Couldn't start recording. Please try again.";
  }
}

/**
 * Records one voice clip at a time.
 * status: "idle" | "requesting" | "recording"
 * `onRecorded(blob, seconds)` is called after Stop (not after Cancel).
 * The microphone is requested only when start() is called, and released as soon as recording ends.
 */
export function useVoiceRecorder({ onRecorded, onError, maxSeconds = 60 }) {
  const [status, setStatus] = useState("idle");
  const [seconds, setSeconds] = useState(0);
  const recorderRef = useRef(null);
  const streamRef = useRef(null);
  const timerRef = useRef(null);
  const startedAtRef = useRef(0);
  const cancelledRef = useRef(false);
  const callbacks = useRef({ onRecorded, onError });
  callbacks.current = { onRecorded, onError };

  const releaseMic = useCallback(() => {
    clearInterval(timerRef.current);
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }, []);

  const stop = useCallback(() => {
    if (recorderRef.current?.state === "recording") recorderRef.current.stop();
  }, []);

  const cancel = useCallback(() => {
    cancelledRef.current = true;
    stop();
  }, [stop]);

  const start = useCallback(async () => {
    if (!voiceSupported || status !== "idle") return;
    setStatus("requesting");
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (error) {
      setStatus("idle");
      callbacks.current.onError?.(micErrorMessage(error));
      return;
    }

    streamRef.current = stream;
    const mimeType = MIME_CANDIDATES.find((t) => MediaRecorder.isTypeSupported?.(t));
    const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
    const chunks = [];
    cancelledRef.current = false;

    recorder.ondataavailable = (e) => { if (e.data?.size) chunks.push(e.data); };
    recorder.onstop = () => {
      const duration = (Date.now() - startedAtRef.current) / 1000;
      releaseMic();
      recorderRef.current = null;
      setStatus("idle");
      setSeconds(0);
      if (cancelledRef.current) return;
      if (duration < 1 || chunks.length === 0) {
        callbacks.current.onError?.("That recording was too short. Press the microphone, speak, then press stop.");
        return;
      }
      callbacks.current.onRecorded?.(new Blob(chunks, { type: recorder.mimeType || "audio/webm" }), duration);
    };

    recorderRef.current = recorder;
    startedAtRef.current = Date.now();
    recorder.start();
    setSeconds(0);
    setStatus("recording");
    timerRef.current = setInterval(() => {
      const elapsed = (Date.now() - startedAtRef.current) / 1000;
      setSeconds(elapsed);
      if (elapsed >= maxSeconds) recorder.stop();
    }, 250);
  }, [maxSeconds, releaseMic, status]);

  // Never leave the microphone on if the component goes away mid-recording.
  useEffect(() => () => {
    cancelledRef.current = true;
    if (recorderRef.current?.state === "recording") recorderRef.current.stop();
    releaseMic();
  }, [releaseMic]);

  return { status, seconds, start, stop, cancel, supported: voiceSupported, maxSeconds };
}
