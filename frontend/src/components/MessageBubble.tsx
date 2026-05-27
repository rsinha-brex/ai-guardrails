"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/cn";

export function MessageBubble({
  role,
  content,
}: {
  role: "user" | "assistant";
  content: string;
}) {
  const isUser = role === "user";
  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[78%] rounded-[var(--radius-lg)] px-3.5 py-2 text-sm leading-relaxed",
          isUser ? "bg-indigo text-bg-elevated" : "bg-bg-subtle text-ink",
        )}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{content}</p>
        ) : (
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              p: ({ children }) => (
                <p className="mb-2 last:mb-0 whitespace-pre-line">{children}</p>
              ),
              strong: ({ children }) => (
                <strong className="font-semibold text-ink">{children}</strong>
              ),
              em: ({ children }) => <em className="italic">{children}</em>,
              ul: ({ children }) => (
                <ul className="list-disc pl-5 my-2 space-y-1 last:mb-0">{children}</ul>
              ),
              ol: ({ children }) => (
                <ol className="list-decimal pl-5 my-2 space-y-1 last:mb-0">{children}</ol>
              ),
              li: ({ children }) => <li className="leading-relaxed">{children}</li>,
              code: ({ children }) => (
                <code className="font-mono text-[12px] bg-bg-elevated/70 rounded px-1 py-0.5 border border-border">
                  {children}
                </code>
              ),
              a: ({ href, children }) => (
                <a href={href} className="text-accent underline hover:text-accent-soft">
                  {children}
                </a>
              ),
              h1: ({ children }) => <p className="font-display text-base mb-1 last:mb-0">{children}</p>,
              h2: ({ children }) => <p className="font-display text-base mb-1 last:mb-0">{children}</p>,
              h3: ({ children }) => <p className="font-medium mb-1 last:mb-0">{children}</p>,
              hr: () => <hr className="my-2 border-border" />,
            }}
          >
            {content || ""}
          </ReactMarkdown>
        )}
      </div>
    </div>
  );
}
