import React from "react";

function renderInline(text: string): React.ReactNode[] {
  const parts = text.split(/(\*\*[^*\n]+\*\*|\*[^*\n]+\*|\[[^\]]+\]\([^)]+\))/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**"))
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    if (part.startsWith("*") && part.endsWith("*"))
      return <em key={i}>{part.slice(1, -1)}</em>;
    const m = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
    if (m)
      return (
        <a
          key={i}
          href={m[2]}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[#0066cc] underline break-all"
        >
          {m[1]}
        </a>
      );
    return part;
  });
}

export function MarkdownText({ text }: { text: string }) {
  const lines = text.split("\n");
  const result: React.ReactNode[] = [];
  let listItems: string[] = [];
  let listKey = 0;

  const flushList = () => {
    if (listItems.length === 0) return;
    result.push(
      <ul key={`ul-${listKey++}`} className="list-disc pl-4 my-1 space-y-0.5">
        {listItems.map((item, i) => (
          <li key={i}>{renderInline(item)}</li>
        ))}
      </ul>
    );
    listItems = [];
  };

  lines.forEach((line, i) => {
    const bulletMatch = line.match(/^[-*] (.+)/);
    const numberedMatch = line.match(/^\d+\. (.+)/);
    if (bulletMatch || numberedMatch) {
      listItems.push((bulletMatch || numberedMatch)![1]);
    } else {
      flushList();
      if (line.trim()) {
        result.push(
          <p key={i} className="mb-1">
            {renderInline(line)}
          </p>
        );
      } else if (result.length > 0) {
        result.push(<br key={i} />);
      }
    }
  });
  flushList();

  return <>{result}</>;
}
