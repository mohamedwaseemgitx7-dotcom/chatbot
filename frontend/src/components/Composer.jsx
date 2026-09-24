import { useLayoutEffect, useRef, useState } from "react";
import AttachmentPreview from "./AttachmentPreview";
import { CloseIcon, ImageIcon, MicIcon, SendIcon } from "./Icons";
import VoiceBar from "./VoiceBar";
import { useVoiceRecorder } from "../hooks/useVoiceRecorder";
import { transcribeVoice } from "../services/botService";
import { toFriendlyError } from "../services/errors";
import { ACCEPTED_IMAGE_TYPES } from "../utils/validateImage";
import "./Composer.css";

const MAX_LENGTH = 1000; // matches the backend ChatRequest limit
const MAX_HEIGHT = 168;

export default function Composer({ busy, attachment, onAttach, onRemoveAttachment, onAnalyze, onSendText, feedback, onFeedback }) {
  const [text, setText] = useState("");
  const [transcribing, setTranscribing] = useState(null); // { audioUrl } while speech is being converted
  const textareaRef = useRef(null);
  const fileRef = useRef(null);
  const abortRef = useRef(null);

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
          // The transcript becomes a normal chat message. If it can't be sent right now, keep it in the input.
          const sent = onSendText(result.text.slice(0, MAX_LENGTH));
          if (!sent?.ok) {
            setText((current) => (current.trim() ? `${current.trim()} ${result.text}` : result.text).slice(0, MAX_LENGTH));
            onFeedback({ type: "info", text: `${sent?.error ? `${sent.error} ` : ""}Your voice question is in the box — press send when ready.` });
            requestAnimationFrame(() => textareaRef.current?.focus());
          }
        }
      } catch (error) {
        if (error?.kind !== "aborted") onFeedback({ type: "error", text: toFriendlyError(error, "voice").message });
      } finally {
        URL.revokeObjectURL(audioUrl);
        abortRef.current = null;
        setTranscribing(null);
      }
    },
  });

  const voiceActive = recorder.status !== "idle" || transcribing !== null;
  const hasText = text.trim().length > 0;
  const canSend = hasText && !busy && !voiceActive;

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
    recorder.start();
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

        {attachment && (
          <AttachmentPreview attachment={attachment} busy={busy} onRemove={onRemoveAttachment} onAnalyze={onAnalyze} />
        )}

        {voiceActive ? (
          <VoiceBar
            status={transcribing ? "transcribing" : recorder.status}
            seconds={recorder.seconds}
            maxSeconds={recorder.maxSeconds}
            audioUrl={transcribing?.audioUrl}
            onStop={recorder.stop}
            onCancel={transcribing ? cancelTranscription : recorder.cancel}
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
              disabled={!recorder.supported}
              aria-label={recorder.supported ? "Ask by voice" : "Voice input isn't supported in this browser"}
              title={recorder.supported ? "Ask by voice" : "Voice input isn't supported in this browser"}
            >
              <MicIcon />
            </button>

            <button
              type="submit"
              className="composer__send"
              disabled={!canSend}
              aria-label={busy ? "Waiting for the reply" : "Send message"}
              title={busy ? "Waiting for the reply" : "Send message"}
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
