/** Where an answer came from. Links open the official page in a new tab. */
export default function SourceList({ sources }) {
  if (!Array.isArray(sources) || sources.length === 0) return null;
  return (
    <div className="sources">
      <span className="sources__label">Source{sources.length > 1 ? "s" : ""}</span>
      <ul>
        {sources.map((s) => (
          <li key={s.url}>
            <a href={s.url} target="_blank" rel="noopener noreferrer">{s.title}</a>
            {s.publisher && <span className="sources__publisher"> · {s.publisher}</span>}
          </li>
        ))}
      </ul>
      <p className="sources__note">Official source, pending expert review. Confirm with your local agriculture officer.</p>
    </div>
  );
}
