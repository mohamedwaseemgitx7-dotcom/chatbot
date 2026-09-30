import { useEffect, useLayoutEffect, useRef, useState } from "react";
import AttachmentPreview from "./AttachmentPreview";
import { CloseIcon, ImageIcon, MicIcon, SendIcon } from "./Icons";
import VoiceBar from "./VoiceBar";
import { speechRecognitionSupported, useSpeechRecognition } from "../hooks/useSpeechRecognition";
import { useVoiceRecorder } from "../hooks/useVoiceRecorder";
import { serverVoiceAvailable, transcribeVoice } from "../services/botService";
import { toFriendlyError } from "../services/errors";
import { ACCEPTED_IMAGE_TYPES } from "../utils/validateImage";
import "./Composer.css";

const MAX_LENGTH = 1000; // matches the backend ChatRequest limit
const MAX_HEIGHT = 168;

// Browser speech recognition understands one language at a time; Tamil first for Tamil Nadu farmers.
export const SPEECH_LANGS = [
  { code: "ta-IN", label: "தமிழ்" },
  { code: "en-IN", label: "English" },
];
const SPEECH_LANG_KEY = "farmerassist.speechLang";

function readSpeechLang() {
  try {
    const saved = localStorage.getItem(SPEECH_LANG_KEY);
    if (SPEECH_LANGS.some((l) => l.code === saved)) return saved;
  } catch { /* storage blocked */ }
  return SPEECH_LANGS[0].code;
}

export default function Composer({ busy, attachment, onAttach, onRemoveAttachment, onAnalyze, onSendText, feedback, onFeedback, cooldown }) {
  const [text, setText] = useState("");
  const [transcribing, setTranscribing] = useState(null); // { audioUrl } while speech is being converted
  const textareaRef = useRef(null);
  const fileRef = useRef(null);
  const abortRef = useRef(null);

  // "server" = record audio and transcribe with Whisper on the API; "browser" = the browser's own speech recognition,
  // used when the server has no voice model (e.g. Render free plan).
  const [voiceMode, setVoiceMode] = useState("server");
  const [speechLang, setSpeechLang] = useState(readSpeechLang);

  useEffect(() => {
    if (!speechRecognitionSupported) return;
    let active = true;
    serverVoiceAvailable().then((available) => { if (active && !available) setVoiceMode("browser"); });
    return () => { active = false; };
  }, []);

  function changeSpeechLang(lang) {
    setSpeechLang(lang);
    try { localStorage.setItem(SPEECH_LANG_KEY, lang); } catch { /* storage blocked: choice lasts this visit */ }
  }

  /** A transcript becomes a normal chat message. If it can't be sent right now, keep it in the input. */
  function deliverTranscript(transcript) {
    const sent = onSendText(transcript.slice(0, MAX_LENGTH));
    if (!sent?.ok) {
      setText((current) => (current.trim() ? `${current.trim()} ${transcript}` : transcript).slice(0, MAX_LENGTH));
      onFeedback({ type: "info", text: `${sent?.error ? `${sent.error} ` : ""}Your voice question is in the box — press send when ready.` });
      requestAnimationFrame(() => textareaRef.current?.focus());
    }
  }

  const speech = useSpeechRecognition({
    lang: speechLang,
    onError: (message) => onFeedback({ type: "error", text: message }),
    onResult: (transcript) => {
      onFeedback(null);
      deliverTranscript(transcript);
    },
  });

  const recorder = useVoiceRecorder({
    onError: (message) => onFeedback({ type: "error", text: message }),
    onRecorded: async (blob) => {
      const audioUrl = URL.createObjectURL(blob);
      const controller = new AbortController();
      abortRef.current = controller;
      setTranscribing({ audioUrl });
      onFeedback(null);
      try {
        const result = await transcribeVoice(blob, { signal: controller.signal });
        if (!result.text) {
          onFeedback({ type: "error", text: "We couldn't make out any words. Please try again closer to the microphone, or type your question." });
        } else {
          deliverTranscript(result.text);
        }
      } catch (error) {
        if (error?.status === 429) cooldown?.start("voice", error.retryAfter);
        if (error?.status === 503 && speechRecognitionSupported) {
          setVoiceMode("browser");
          onFeedback({ type: "info", text: "Voice now uses your browser's speech recognition. Press the microphone and speak again." });
        } else if (error?.kind !== "aborted") {
          onFeedback({ type: "error", text: toFriendlyError(error, "voice").message });
        }
      } finally {
        URL.revokeObjectURL(audioUrl);
        abortRef.current = null;
        setTranscribing(null);
      }
    },
  });

  // Switching language while listening restarts listening in the new language — within the same tap, as iOS requires.
  function switchSpeechLang(lang) {
    speech.cancel();
    changeSpeechLang(lang);
    speech.start(lang);
  }

  const useBrowserSpeech = voiceMode === "browser";
  const voice = useBrowserSpeech ? speech : recorder;
  const voiceActive = voice.status !== "idle" || transcribing !== null;
  const hasText = text.trim().length > 0;
  const chatWait = cooldown?.remaining("chat") || 0;
  const imageWait = cooldown?.remaining("image") || 0;
  const voiceWait = cooldown?.remaining("voice") || 0;
  const canSend = hasText && !busy && !voiceActive && chatWait === 0;

  // Grow with the content up to MAX_HEIGHT, then scroll inside the field.
  useLayoutEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT)}px`;
    el.style.overflowY = el.scrollHeight > MAX_HEIGHT ? "auto" : "hidden";
  }, [text, voiceActive]);

  function submit(event) {
    event?.preventDefault();
    if (!canSend) return;
    const result = onSendText(text);
    if (result?.ok) {
      setText("");
      onFeedback(null);
    } else if (result?.error) {
      onFeedback({ type: "error", text: result.error });
    }
  }

  function onKeyDown(event) {
    // Enter sends, Shift+Enter adds a line. Never send while an IME (e.g. Tamil keyboard) is composing.
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing && event.keyCode !== 229) {
      event.preventDefault();
      submit();
    }
  }

  function onFileChange(event) {
    const file = event.target.files?.[0];
    if (file) onAttach(file);
    event.target.value = ""; // allow picking the same photo again
  }

  function onPaste(event) {
    const file = [...(event.clipboardData?.files || [])].find((f) => f.type.startsWith("image/"));
    if (file) {
      event.preventDefault();
      onAttach(file);
    }
  }

  function startVoice() {
    onFeedback(null); // an old error shouldn't sit above a new recording
    voice.start();
  }

  function cancelTranscription() {
    abortRef.current?.abort();
  }

  return (
    <div className="composer">
      <div className="composer__inner">
        {feedback && (
          <div className={`composer__feedback composer__feedback--${feedback.type}`} role={feedback.type === "error" ? "alert" : "status"}>
            <span>{feedback.text}</span>
            <button type="button" className="composer__feedback-close" onClick={() => onFeedback(null)} aria-label="Dismiss message">
              <CloseIcon />
            </button>
          </div>
        )}

        {chatWait > 0 && (
          <div className="composer__cooldown" role="status" aria-live="polite">
            <strong>Rate limit reached.</strong> Try again in {chatWait} seconds. Your message is kept.
          </div>
        )}

        {attachment && (
          <AttachmentPreview attachment={attachment} busy={busy} waitSeconds={imageWait} onRemove={onRemoveAttachment} onAnalyze={onAnalyze} />
        )}

        {voiceActive ? (
          <VoiceBar
            status={transcribing ? "transcribing" : voice.status}
            seconds={voice.seconds}
            maxSeconds={voice.maxSeconds}
            audioUrl={transcribing?.audioUrl}
            liveText={useBrowserSpeech ? speech.transcript : undefined}
            languages={useBrowserSpeech ? SPEECH_LANGS : undefined}
            language={speechLang}
            onLanguageChange={switchSpeechLang}
            onStop={voice.stop}
            onCancel={transcribing ? cancelTranscription : voice.cancel}
          />
        ) : (
          <form className="composer__bar" onSubmit={submit}>
            <button
              type="button"
              className="icon-btn composer__tool"
              onClick={() => fileRef.current?.click()}
              aria-label="Add a crop photo"
              title="Add a crop photo"
            >
              <ImageIcon />
            </button>
            <input ref={fileRef} type="file" accept={ACCEPTED_IMAGE_TYPES.join(",")} hidden onChange={onFileChange} />

            <div className="composer__field">
              <label htmlFor="message-input" className="visually-hidden">Type your farming question</label>
              <textarea
                id="message-input"
                ref={textareaRef}
                rows={1}
                value={text}
                maxLength={MAX_LENGTH}
                placeholder="Type your farming question…"
                enterKeyHint="send"
                autoComplete="off"
                onChange={(e) => setText(e.target.value)}
                onKeyDown={onKeyDown}
                onPaste={onPaste}
              />
            </div>

            <button
              type="button"
              className="icon-btn composer__tool"
              onClick={startVoice}
              disabled={!voice.supported || voiceWait > 0}
              aria-label={!voice.supported ? "Voice input isn't supported in this browser" : voiceWait > 0 ? `Voice available again in ${voiceWait} seconds` : "Ask by voice"}
              title={!voice.supported ? "Voice input isn't supported in this browser" : voiceWait > 0 ? `Voice available again in ${voiceWait} s` : "Ask by voice"}
            >
              <MicIcon />
            </button>

            <button
              type="submit"
              className="composer__send"
              disabled={!canSend}
              aria-label={chatWait > 0 ? `Rate limit reached, try again in ${chatWait} seconds` : busy ? "Waiting for the reply" : "Send message"}
              title={chatWait > 0 ? `Try again in ${chatWait} s` : busy ? "Waiting for the reply" : "Send message"}
            >
              {busy ? <span className="spinner" aria-hidden="true" /> : <SendIcon />}
            </button>
          </form>
        )}

        {text.length > MAX_LENGTH - 150 && !voiceActive && (
          <p className="composer__count" aria-live="polite">{text.length} / {MAX_LENGTH}</p>
        )}
      </div>
    </div>
  );
}
