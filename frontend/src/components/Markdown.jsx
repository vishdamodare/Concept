import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize from "rehype-sanitize";

/**
 * Safe markdown renderer.
 * - react-markdown does NOT parse or render raw HTML by default → no XSS surface.
 * - rehype-sanitize is layered on as defense-in-depth in case a plugin ever enables HTML.
 */
export default function Markdown({ text = "" }) {
  return (
    <div className="md-content">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSanitize]}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}
