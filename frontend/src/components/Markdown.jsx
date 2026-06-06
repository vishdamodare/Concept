import React from "react";

// Minimal markdown renderer (headings, bold, lists, code, paragraphs)
export default function Markdown({ text = "" }) {
  const lines = text.split(/\r?\n/);
  const out = [];
  let listBuf = null;

  const flushList = () => {
    if (listBuf) {
      out.push(
        <ul key={`ul-${out.length}`} className="list-disc">
          {listBuf.map((li, i) => (
            <li key={i} dangerouslySetInnerHTML={{ __html: inline(li) }} />
          ))}
        </ul>
      );
      listBuf = null;
    }
  };

  const inline = (s) =>
    s
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/\*([^*]+)\*/g, "<em>$1</em>");

  lines.forEach((raw, idx) => {
    const line = raw.trimEnd();
    if (/^##\s+/.test(line)) {
      flushList();
      out.push(<h2 key={idx} dangerouslySetInnerHTML={{ __html: inline(line.replace(/^##\s+/, "")) }} />);
    } else if (/^###\s+/.test(line)) {
      flushList();
      out.push(<h3 key={idx} dangerouslySetInnerHTML={{ __html: inline(line.replace(/^###\s+/, "")) }} />);
    } else if (/^\s*[-*]\s+/.test(line)) {
      if (!listBuf) listBuf = [];
      listBuf.push(line.replace(/^\s*[-*]\s+/, ""));
    } else if (line === "") {
      flushList();
    } else {
      flushList();
      out.push(<p key={idx} dangerouslySetInnerHTML={{ __html: inline(line) }} />);
    }
  });
  flushList();
  return <div className="md-content">{out}</div>;
}
