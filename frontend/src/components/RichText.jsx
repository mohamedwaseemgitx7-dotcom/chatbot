import { Fragment } from "react";
import { WarningIcon } from "./Icons";

/**
 * Renders assistant text safely (React escapes everything; no HTML injection):
 * paragraphs, "-", "*" or "•" bullet lists, "1." numbered steps, **bold**, http(s) links,
 * and warning lines ("⚠️ …", "Warning: …", "Caution: …", "Important: …").
 */

const BULLET = /^\s*[-*•]\s+/;
const NUMBERED = /^\s*\d{1,2}[.)]\s+/;
const WARNING = /^\s*(⚠️?|warning\s*:|caution\s*:|important\s*:|எச்சரிக்கை\s*:)\s*/i;
const INLINE = /(\*\*[^*]+\*\*|https?:\/\/[^\s)]+)/g;

function Inline({ text }) {
  return text.split(INLINE).map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    if (/^https?:\/\//.test(part)) {
      const href = part.replace(/[.,;:!?]+$/, "");
      const trailing = part.slice(href.length);
      return (
        <Fragment key={i}>
          <a href={href} target="_blank" rel="noopener noreferrer">{href}</a>{trailing}
        </Fragment>
      );
    }
    return <Fragment key={i}>{part}</Fragment>;
  });
}

/** Groups lines into blocks: paragraph | ul | ol | warning. */
function toBlocks(text) {
  const blocks = [];
  let current = null;
  const push = (type, line) => {
    if (current?.type === type && type !== "warning") current.lines.push(line);
    else { current = { type, lines: [line] }; blocks.push(current); }
  };

  for (const raw of text.replace(/\r\n/g, "\n").split("\n")) {
    const line = raw.trimEnd();
    if (!line.trim()) { current = null; continue; }
    if (WARNING.test(line)) push("warning", line.replace(WARNING, ""));
    else if (BULLET.test(line)) push("ul", line.replace(BULLET, ""));
    else if (NUMBERED.test(line)) push("ol", line.replace(NUMBERED, ""));
    else push("p", line.trim());
  }
  return blocks;
}

export default function RichText({ text, lang }) {
  const blocks = toBlocks(text || "");
  return (
    <div className="rich-text" lang={lang}>
      {blocks.map((block, i) => {
        if (block.type === "ul" || block.type === "ol") {
          const List = block.type;
          return (
            <List key={i}>
              {block.lines.map((line, j) => <li key={j}><Inline text={line} /></li>)}
            </List>
          );
        }
        if (block.type === "warning") {
          return (
            <p key={i} className="rich-text__warning">
              <WarningIcon />
              <span><Inline text={block.lines[0]} /></span>
            </p>
          );
        }
        return (
          <p key={i}>
            {block.lines.map((line, j) => (
              <Fragment key={j}>{j > 0 && <br />}<Inline text={line} /></Fragment>
            ))}
          </p>
        );
      })}
    </div>
  );
}
