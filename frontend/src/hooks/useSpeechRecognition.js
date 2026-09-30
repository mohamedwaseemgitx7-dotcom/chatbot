import { useCallback, useEffect, useRef, useState } from "react";

const SpeechRecognitionImpl =
  typeof window !== "undefined" ? window.SpeechRecognition || window.webkitSpeechRecognition : undefined;

export const speechRecognitionSupported = typeof SpeechRecognitionImpl === "function";

// iPhone/iPad Safari (iPadOS reports itself as a Mac with touch). Its recognizer is unreliable in continuous
// mode, can repeat earlier words in later results, and sometimes never fires `end` after stop().
const isIOS =
  typeof navigator !== "undefined" &&
  (/iP(hone|ad|od)/.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1));

// How long to wait for the recognizer to finish after Stop before finishing ourselves.
const STOP_GRACE_MS = 1500;

/** Turns SpeechRecognition error codes into messages a farmer can act on. */
function speechErrorMessage(code) {
  switch (code) {
    case "not-allowed":
      return isIOS
        ? "Microphone or speech access is blocked. Allow the microphone for this site (Settings → Safari → Microphone), and turn on Siri & Dictation, then try again."
        : "Microphone access is blocked. Allow the microphone for this site in your browser settings, then try again.";
    case "service-not-allowed":
      return isIOS
        ? "Voice needs Dictation. Turn on Settings → General → Keyboard → Enable Dictation (and Siri), then try again — or type your question."
        : "Speech recognition is turned off in this browser. Please type your question.";
    case "audio-capture":
      return "No microphone was found on this device.";
    case "no-speech":
      return "We couldn't hear anything. Press the microphone and speak closer to the phone, or type your question.";
    case "network":
      return "Voice needs an internet connection. Please check your connection, or type your question.";
    case "language-not-supported":
      return "This phone can't recognise that language. Try the other language, or type your question.";
    default:
      return "Couldn't recognise your voice. Please try again, or type your question.";
  }
}

/**
 * Joins recognition results into one sentence. Some browsers (iOS Safari) repeat the words so far in each
 * new result; a result that starts with, or is already contained at the end of, the text so far replaces
 * or is skipped instead of being appended twice.
 */
export function joinResults(results) {
  let text = "";
  for (const result of results) {
    const part = (result?.[0]?.transcript || "").replace(/\s+/g, " ").trim();
    if (!part) continue;
    const lower = text.toLowerCase();
    const partLower = part.toLowerCase();
    if (!text || partLower.startsWith(lower)) text = part;
    else if (!lower.endsWith(partLower)) text = `${text} ${part}`;
  }
  return text;
}

/**
 * Speech-to-text in the browser (Web Speech API), used when the server has no voice model (Render free plan).
 * status: "idle" | "recording". The words appear in `transcript` while the farmer speaks;
 * `onResult(text)` is called when listening ends — after Stop, or on iPhone after a pause — but not after Cancel.
 * Chrome/Edge/Android and iOS Safari (with Dictation on) support it; Firefox doesn't.
 */
export function useSpeechRecognition({ lang, onResult, onError, maxSeconds = 60 }) {
  const [status, setStatus] = useState("idle");
  const [seconds, setSeconds] = useState(0);
  const [transcript, setTranscript] = useState("");
  const recognitionRef = useRef(null);
  const timerRef = useRef(null);
  const graceRef = useRef(null);
  const startedAtRef = useRef(0);
  const cancelledRef = useRef(false);
  const finishedRef = useRef(true);
  const errorRef = useRef(null);
  const textRef = useRef("");
  const callbacks = useRef({ onResult, onError });
  callbacks.current = { onResult, onError };

  /** Ends a listening session exactly once, whether the recognizer reported `end` or our watchdog fired. */
  const finish = useCallback(() => {
    if (finishedRef.current) return;
    finishedRef.current = true;
    clearInterval(timerRef.current);
    clearTimeout(graceRef.current);
    const recognition = recognitionRef.current;
    recognitionRef.current = null;
    if (recognition) {
      recognition.onresult = recognition.onerror = recognition.onend = null;
      try { recognition.abort(); } catch { /* already stopped */ }
    }
    setStatus("idle");
    setSeconds(0);
    if (cancelledRef.current) return;
    const text = textRef.current;
    if (text) callbacks.current.onResult?.(text);
    else callbacks.current.onError?.(speechErrorMessage(errorRef.current || "no-speech"));
  }, []);

  const stop = useCallback(() => {
    const recognition = recognitionRef.current;
    if (!recognition) return;
    try { recognition.stop(); } catch { /* not started yet */ }
    clearTimeout(graceRef.current);
    graceRef.current = setTimeout(finish, STOP_GRACE_MS); // iOS may never fire `end`
  }, [finish]);

  const cancel = useCallback(() => {
    cancelledRef.current = true;
    finish();
  }, [finish]);

  /** Starts listening, in `langOverride` if given. Call it straight from a tap: iOS only allows that. */
  const start = useCallback((langOverride) => {
    if (!speechRecognitionSupported || !finishedRef.current) return;
    let recognition;
    try {
      recognition = new SpeechRecognitionImpl();
    } catch {
      callbacks.current.onError?.(speechErrorMessage(null));
      return;
    }
    recognition.lang = typeof langOverride === "string" ? langOverride : lang;
    recognition.continuous = !isIOS; // iPhone: one phrase, ends by itself after a pause
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    cancelledRef.current = false;
    finishedRef.current = false;
    errorRef.current = null;
    textRef.current = "";
    setTranscript("");

    recognition.onresult = (event) => {
      textRef.current = joinResults(event.results);
      setTranscript(textRef.current);
    };
    recognition.onerror = (event) => {
      if (event.error !== "aborted") errorRef.current = event.error;
    };
    recognition.onend = finish;

    recognitionRef.current = recognition;
    try {
      recognition.start(); // must run inside the tap handler on iOS — callers call start() directly from onClick
    } catch {
      recognitionRef.current = null;
      finishedRef.current = true;
      callbacks.current.onError?.(speechErrorMessage(null));
      return;
    }
    startedAtRef.current = Date.now();
    setSeconds(0);
    setStatus("recording");
    timerRef.current = setInterval(() => {
      const elapsed = (Date.now() - startedAtRef.current) / 1000;
      setSeconds(elapsed);
      if (elapsed >= maxSeconds) stop();
    }, 250);
  }, [finish, lang, maxSeconds, stop]);

  // Never leave the microphone on if the component goes away mid-recording.
  useEffect(() => () => {
    cancelledRef.current = true;
    finish();
  }, [finish]);

  return { status, seconds, transcript, start, stop, cancel, supported: speechRecognitionSupported, maxSeconds };
}
