import ReactMarkdown from "react-markdown";

interface MarkdownMessageProps {
  content: string;
  role: "user" | "assistant";
}

export default function MarkdownMessage({ content, role }: MarkdownMessageProps) {
  if (role === "user") {
    return <>{content}</>;
  }

  return (
    <ReactMarkdown
      components={{
        strong: ({ children }) => (
          <span className="font-semibold text-white">{children}</span>
        ),
        h3: ({ children }) => (
          <h3 className="text-sm font-medium text-[#E76315] mt-2 mb-1">{children}</h3>
        ),
        ul: ({ children }) => (
          <ul className="space-y-1.5 my-2 list-disc list-inside marker:text-[#E76315]/60">
            {children}
          </ul>
        ),
        ol: ({ children }) => (
          <ol className="space-y-1.5 my-2 list-decimal list-inside marker:text-[#E76315]/60">
            {children}
          </ol>
        ),
        li: ({ children }) => (
          <li className="text-white/80">{children}</li>
        ),
        p: ({ children }) => (
          <p className="mb-2 last:mb-0">{children}</p>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
