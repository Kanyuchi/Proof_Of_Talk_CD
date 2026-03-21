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
          <span className="font-semibold text-[#E76315]">{children}</span>
        ),
        h3: ({ children }) => (
          <p className="font-medium text-white mt-3 first:mt-0 mb-1">{children}</p>
        ),
        em: ({ children }) => (
          <span className="italic text-white/60">{children}</span>
        ),
        ul: ({ children }) => (
          <ul className="space-y-1 my-1.5 ml-3 list-disc marker:text-[#E76315]/40 text-[13px]">
            {children}
          </ul>
        ),
        ol: ({ children }) => (
          <ol className="space-y-1 my-1.5 ml-3 list-decimal marker:text-[#E76315]/40 text-[13px]">
            {children}
          </ol>
        ),
        li: ({ children }) => (
          <li className="text-white/70 leading-relaxed">{children}</li>
        ),
        p: ({ children }) => (
          <p className="mb-2.5 last:mb-0 leading-relaxed">{children}</p>
        ),
        hr: () => (
          <div className="my-3 border-t border-white/5" />
        ),
        a: ({ href, children }) => (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[#E76315] underline underline-offset-2 hover:text-[#FF833A]"
          >
            {children}
          </a>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
