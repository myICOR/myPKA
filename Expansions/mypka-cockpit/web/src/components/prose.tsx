// prose.tsx — renders the server's ReadableBlock[] as scannable prose inside a
// Sheet/Dialog. Paragraphs get air, bullets become real lists, headings become
// quiet sub-labels, **bold** runs become emphasized key-lines. This is what turns
// a wall of text into something a health-anxious reader can scan (v2 #3).
import type { ReactNode } from 'react';
import type { ReadableBlock } from '../lib/types';

// Render inline **bold** markers as emphasized spans. Everything else is plain
// text — the server already stripped wikilinks / code / icons.
function renderInline(text: string): ReactNode[] {
  const out: ReactNode[] = [];
  const re = /\*\*([^*]+)\*\*/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let key = 0;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push(text.slice(last, m.index));
    out.push(
      <strong key={`b${key++}`} className="font-[520] text-fg">
        {m[1]}
      </strong>
    );
    last = re.lastIndex;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

export function ReadableBlocks({ blocks }: { blocks: ReadableBlock[] }) {
  if (!blocks.length) {
    return <p className="text-caption text-fg-subtle">No further text on file.</p>;
  }
  return (
    <>
      {blocks.map((b, i) => {
        switch (b.type) {
          case 'h':
            return (
              <h3 key={i} className="mt-md mb-xs text-meta font-[520] text-fg first:mt-0">
                {renderInline(b.text)}
              </h3>
            );
          case 'ul':
            return (
              <ul key={i}>
                {b.items.map((it, j) => (
                  <li key={j}>{renderInline(it)}</li>
                ))}
              </ul>
            );
          case 'quote':
            return (
              <p
                key={i}
                className="border-l-2 border-marker pl-md text-fg-muted italic"
              >
                {renderInline(b.text)}
              </p>
            );
          case 'p':
          default:
            return <p key={i}>{renderInline(b.text)}</p>;
        }
      })}
    </>
  );
}
