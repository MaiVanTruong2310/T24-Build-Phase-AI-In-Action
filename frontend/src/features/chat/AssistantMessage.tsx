import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

function normalizeAssistantMarkdown(text: string): string {
  return text
    .replace(/\\n/g, '\n')
    .replace(/\\([*`])/g, '$1')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

export function AssistantMessage({ text }: { text: string }) {
  return (
    <div className="space-y-2 [&_p]:whitespace-pre-wrap [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_li]:my-1 [&_strong]:font-semibold [&_h1]:font-bold [&_h2]:font-bold [&_h3]:font-semibold [&_blockquote]:border-l-2 [&_blockquote]:pl-3 [&_table]:block [&_table]:overflow-x-auto [&_td]:border [&_td]:p-2 [&_th]:border [&_th]:p-2 [&_pre]:overflow-x-auto [&_code]:rounded [&_code]:bg-slate-100 [&_code]:px-1 dark:[&_code]:bg-slate-800">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children }) => {
            // Only real web links may open from generated assistant content.
            if (!href || !/^https?:\/\//i.test(href)) return <span>{children}</span>;
            return (
              <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-600 underline underline-offset-2 hover:text-blue-800 dark:text-cyan-300 dark:hover:text-cyan-200">
                {children}
              </a>
            );
          },
          // Keep externally supplied images as readable text, without fetching them.
          img: ({ alt }) => <span>{alt}</span>,
        }}
      >
        {normalizeAssistantMarkdown(text)}
      </ReactMarkdown>
    </div>
  );
}
