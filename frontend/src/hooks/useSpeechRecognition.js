import { useCallback, useEffect, useRef, useState } from "react";

const SpeechRecognitionImpl =
  typeof window !== "undefined" ? window.SpeechRecognition || window.webkitSpeechRecognition : undefined;

export const speechRecognitionSupported = typeof SpeechRecognitionImpl === "function";

/** Turns SpeechRecognition error codes into messages a farmer can act on. */
function speechErrorMessage(code) {
  switch (code) {
    case "not-allowed":
    case "service-not-allowed":
      return "Microphone access is blocked. Allow the microphone for this site in your browser settings, then try again.";
    case "audio-capture":
      return "No microphone was found on this device.";
    case "no-speech":
      return "We couldn't hear anything. Press the microphone and speak closer to the phone, or type your question.";
    case "network":
      return "Voice needs an internet connection. Please check your connection, or type your question.";
    case "language-not-supported":
      return "This browser can't recognise that language. Try the other language, or type your question.";
    default:
      return "Couldn't recognise your voice. Please try again, or type your question.";
  }
}

/**
 * Speech-to-text in the browser (Web Speech API), used when the server has no voice model (Render free plan).
 * status: "idle" | "recording". The words appear in `transcript` while the farmer speaks;
 * `onResult(text)` is called after Stop (not after Cancel). Chrome/Edge/Android support it; Firefox doesn't.
 */
export function useSpeechRecognition({ lang, onResult, onError, maxSeconds = 60 }) {
  const [status, setStatus] = useState("idle");
  const [seconds, setSeconds] = useState(0);
  const [transcript, setTranscript] = useState("");
  const recognitionRef = useRef(null);
  const timerRef = useRef(null);
  const startedAtRef = useRef(0);
  const cancelledRef = useRef(false);
  const errorRef = useRef(null);
  const textRef = useRef("");
  const callbacks = useRef({ onResult, onError });
  callbacks.current = { onResult, onError };

  const stop = useCallback(() => recognitionRef.current?.stop(), []);

  const cancel = useCallback(() => {
    cancelledRef.current = true;
    recognitionRef.current?.abort();
  }, []);

  const start = useCallback(() => {
    if (!speechRecognitionSupported || status !== "idle") return;
    const recognition = new SpeechRecognitionImpl();
    recognition.lang = lang;
    recognition.continuous = true; // keep listening through pauses until the farmer presses Stop
    recognition.interimResults = true;
    cancelledRef.current = false;
    errorRef.current = null;
    textRef.current = "";
    setTranscript("");

    recognition.onresult = (event) => {
      textRef.current = [...event.results].map((r) => r[0].transcript).join(" ").replace(/\s+/g, " ").trim();
      setTranscript(textRef.current);
    };
    recognition.onerror = (event) => {
      if (event.error !== "aborted") errorRef.current = event.error;
    };
    recognition.onend = () => {
      clearInterval(timerRef.current);
      recognitionRef.current = null;
      setStatus("idle");
      setSeconds(0);
      if (cancelledRef.current) return;
      const text = textRef.current;
      if (text) callbacks.current.onResult?.(text);
      else callbacks.current.onError?.(speechErrorMessage(errorRef.current || "no-speech"));
    };

    recognitionRef.current = recognition;
    try {
      recognition.start();
    } catch {
      recognitionRef.current = null;
      callbacks.current.onError?.(speechErrorMessage(null));
      return;
    }
    startedAtRef.current = Date.now();
    setSeconds(0);
    setStatus("recording");
    timerRef.current = setInterval(() => {
      const elapsed = (Date.now() - startedAtRef.current) / 1000;
      setSeconds(elapsed);
      if (elapsed >= maxSeconds) recognition.stop();
    }, 250);
  }, [lang, maxSeconds, status]);

  // Never leave the microphone on if the component goes away mid-recording.
  useEffect(() => () => {
    cancelledRef.current = true;
    clearInterval(timerRef.current);
    recognitionRef.current?.abort();
  }, []);

  return { status, seconds, transcript, start, stop, cancel, supported: speechRecognitionSupported, maxSeconds };
}
