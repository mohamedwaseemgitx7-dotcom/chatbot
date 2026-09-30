import { useEffect } from "react";
import { CloseIcon, StopIcon } from "./Icons";
import { formatDuration } from "../utils/format";

/** Replaces the input row while a voice question is being recorded or transcribed. */
export default function VoiceBar({ status, seconds, maxSeconds, audioUrl, liveText, languages, language, onLanguageChange, onStop, onCancel }) {
  // Escape cancels, like closing any other temporary panel.
  useEffect(() => {
    const onKey = (e) => { if (e.key === "Escape") onCancel(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onCancel]);

  return (
    <div className={`voice-bar voice-bar--${status}`}>
      <button type="button" className="icon-btn" onClick={onCancel} disabled={status === "requesting"} aria-label={status === "transcribing" ? "Cancel transcription" : "Cancel recording"}>
        <CloseIcon />
      </button>

      <div className="voice-bar__status" role="status" aria-live="polite">
        {status === "requesting" && <span>Waiting for microphone permission…</span>}
        {status === "recording" && (
          <>
            <span className="voice-bar__dot" aria-hidden="true" />
            <span>Recording…</span>
            <span className="voice-bar__time">
              {formatDuration(seconds)}
              <span className="voice-bar__max"> / {formatDuration(maxSeconds)}</span>
            </span>
          </>
        )}
        {status === "transcribing" && (
          <>
            <span className="spinner" aria-hidden="true" />
            <span>Transcribing…</span>
          </>
        )}
      </div>

      {languages && status === "recording" && (
        <div className="voice-bar__langs" role="group" aria-label="Speaking language">
          {languages.map((l) => (
            <button
              key={l.code}
              type="button"
              className="voice-bar__lang"
              aria-pressed={l.code === language}
              onClick={() => l.code !== language && onLanguageChange(l.code)}
            >
              {l.label}
            </button>
          ))}
        </div>
      )}

      {liveText !== undefined && status === "recording" && (
        <p className="voice-bar__live" aria-live="polite">
          {liveText || <span className="voice-bar__hint">Speak now — your words appear here.</span>}
        </p>
      )}

      {status === "transcribing" && audioUrl && (
        <audio className="voice-bar__audio" src={audioUrl} controls aria-label="Play back your recording" />
      )}

      {status === "recording" && (
        <button type="button" className="voice-bar__stop" onClick={onStop} aria-label="Stop recording and transcribe">
          <StopIcon />
          <span>Stop</span>
        </button>
      )}
    </div>
  );
}
