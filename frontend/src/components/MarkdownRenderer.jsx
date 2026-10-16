import React from "react";
import ReactMarkdown, { defaultUrlTransform } from "react-markdown";
import remarkGfm from "remark-gfm";

/**
 * Strips outer markdown code block fences (e.g., ```markdown ... ```)
 * that LLMs frequently wrap full note summaries in, preventing the entire
 * note from displaying as a single monolithic code block.
 */
function unwrapOuterMarkdownFences(text) {
  if (!text) return "";
  let trimmed = text.trim();

  // Handle opening fence ```markdown or ```md or ```
  if (/^```(?:markdown|md)?\s*\r?\n/.test(trimmed)) {
    trimmed = trimmed.replace(/^```(?:markdown|md)?\s*\r?\n/, "");
    // Remove closing ``` if before ## Charts or at the end of the content
    trimmed = trimmed.replace(/\r?\n```(\s*\r?\n\s*## Charts|\s*$)/, "$1");
  }

  return trimmed;
}

export default function MarkdownRenderer({ content, className = "" }) {
  if (!content) return null;

  const sanitizedContent = unwrapOuterMarkdownFences(content);

  return (
    <div className={`markdown-body text-gray-800 leading-relaxed ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        urlTransform={(url) => (url.startsWith("data:image/") ? url : defaultUrlTransform(url))}
        components={{
          h1: ({ node, ...props }) => (
            <h1 className="text-2xl font-extrabold text-gray-900 mt-7 mb-4 pb-2 border-b border-gray-200" {...props} />
          ),
          h2: ({ node, ...props }) => (
            <h2 className="text-xl font-bold text-gray-900 mt-6 mb-3 text-blue-900 flex items-center gap-2 border-l-4 border-blue-600 pl-3" {...props} />
          ),
          h3: ({ node, ...props }) => (
            <h3 className="text-lg font-bold text-gray-800 mt-5 mb-2 text-indigo-950" {...props} />
          ),
          h4: ({ node, ...props }) => (
            <h4 className="text-base font-semibold text-gray-800 mt-4 mb-2" {...props} />
          ),
          p: ({ node, ...props }) => (
            <p className="text-gray-700 leading-relaxed mb-3.5 text-[15px]" {...props} />
          ),
          ul: ({ node, ...props }) => (
            <ul className="list-disc list-outside ml-6 space-y-1.5 mb-4 text-gray-700 text-[15px]" {...props} />
          ),
          ol: ({ node, ...props }) => (
            <ol className="list-decimal list-outside ml-6 space-y-1.5 mb-4 text-gray-700 text-[15px]" {...props} />
          ),
          li: ({ node, ...props }) => (
            <li className="text-gray-700 leading-relaxed" {...props} />
          ),
          table: ({ node, ...props }) => (
            <div className="overflow-x-auto my-5 rounded-lg border border-gray-300 shadow-xs">
              <table className="w-full border-collapse text-sm text-left" {...props} />
            </div>
          ),
          thead: ({ node, ...props }) => (
            <thead className="bg-slate-100 border-b border-gray-300 font-semibold text-gray-800" {...props} />
          ),
          th: ({ node, ...props }) => (
            <th className="border-r border-gray-200 last:border-r-0 px-4 py-2.5 font-semibold text-gray-800" {...props} />
          ),
          td: ({ node, ...props }) => (
            <td className="border-t border-r border-gray-200 last:border-r-0 px-4 py-2.5 text-gray-700" {...props} />
          ),
          tr: ({ node, ...props }) => (
            <tr className="hover:bg-slate-50/70 transition-colors" {...props} />
          ),
          blockquote: ({ node, ...props }) => (
            <blockquote className="border-l-4 border-blue-500 bg-blue-50/40 pl-4 py-2.5 italic my-4 text-gray-700 rounded-r text-[15px]" {...props} />
          ),
          strong: ({ node, ...props }) => (
            <strong className="font-bold text-gray-900" {...props} />
          ),
          em: ({ node, ...props }) => (
            <em className="italic text-gray-800" {...props} />
          ),
          a: ({ node, ...props }) => (
            <a className="text-blue-600 hover:text-blue-800 underline font-medium" target="_blank" rel="noopener noreferrer" {...props} />
          ),
          hr: ({ node, ...props }) => (
            <hr className="border-t border-gray-200 my-6" {...props} />
          ),
          img: ({ node, ...props }) => (
            <img className="max-w-full h-auto rounded-xl shadow-md my-5 border border-gray-200 mx-auto block" alt={props.alt || "Lecture Image"} {...props} />
          ),
          pre: ({ node, ...props }) => (
            <pre className="bg-slate-900 text-slate-100 p-4 rounded-xl overflow-x-auto my-4 font-mono text-xs shadow-md border border-slate-800 leading-normal [&>code]:bg-transparent [&>code]:text-slate-100 [&>code]:p-0 [&>code]:border-0" {...props} />
          ),
          code: ({ node, className, children, ...props }) => {
            const isBlock = String(children).includes("\n") || /language-/.test(className || "");
            if (isBlock) {
              return (
                <code className={`font-mono text-xs ${className || ""}`} {...props}>
                  {children}
                </code>
              );
            }
            return (
              <code className={`bg-slate-100 text-pink-600 font-mono text-[13px] px-1.5 py-0.5 rounded border border-slate-200 ${className || ""}`} {...props}>
                {children}
              </code>
            );
          }
        }}
      >
        {sanitizedContent}
      </ReactMarkdown>
    </div>
  );
}
