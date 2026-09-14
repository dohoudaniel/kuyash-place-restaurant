import { Fragment, type ReactNode } from "react";

/**
 * A deliberately small Markdown renderer for policy pages written in the admin.
 *
 * Supports `##`/`###` headings, paragraphs, `- ` lists, `**bold**` and
 * `[links](https://…)`. It builds React elements — never HTML strings — so
 * nothing typed into the admin can inject markup or script.
 */
export interface MarkdownClasses {
  h2: string;
  h3: string;
  p: string;
  ul: string;
  link: string;
  style?: { heading?: React.CSSProperties; text?: React.CSSProperties; link?: React.CSSProperties };
}

const SAFE_HREF = /^(https?:\/\/|mailto:|tel:|\/(?!\/))/i;

function inline(text: string, classes: MarkdownClasses, keyBase: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  const pattern = /\*\*(.+?)\*\*|\[([^\]]+)\]\(([^)\s]+)\)/g;
  let last = 0;
  let match: RegExpExecArray | null;
  while ((match = pattern.exec(text)) !== null) {
    if (match.index > last) nodes.push(text.slice(last, match.index));
    const key = `${keyBase}-${match.index}`;
    if (match[1] !== undefined) {
      nodes.push(<strong key={key}>{match[1]}</strong>);
    } else if (SAFE_HREF.test(match[3])) {
      nodes.push(
        <a key={key} href={match[3]} className={classes.link} style={classes.style?.link}>
          {match[2]}
        </a>
      );
    } else {
      nodes.push(match[2]);
    }
    last = match.index + match[0].length;
  }
  if (last < text.length) nodes.push(text.slice(last));
  return nodes;
}

export function renderMarkdown(source: string, classes: MarkdownClasses, { skipHeading }: { skipHeading?: string } = {}): ReactNode {
  const blocks: ReactNode[] = [];
  const lines = source.replace(/\r\n/g, "\n").split("\n");
  let paragraph: string[] = [];
  let list: string[] = [];

  const flush = () => {
    if (paragraph.length) {
      const key = `p-${blocks.length}`;
      blocks.push(
        <p key={key} className={classes.p} style={classes.style?.text}>
          {inline(paragraph.join(" "), classes, key)}
        </p>
      );
      paragraph = [];
    }
    if (list.length) {
      const key = `ul-${blocks.length}`;
      blocks.push(
        <ul key={key} className={classes.ul} style={classes.style?.text}>
          {list.map((item, index) => (
            <li key={index}>{inline(item, classes, `${key}-${index}`)}</li>
          ))}
        </ul>
      );
      list = [];
    }
  };

  for (const raw of lines) {
    const line = raw.trim();
    if (!line) {
      flush();
    } else if (line.startsWith("### ") || line.startsWith("## ")) {
      flush();
      const level = line.startsWith("### ") ? 3 : 2;
      const text = line.slice(level + 1).trim();
      if (level === 2 && skipHeading && text === skipHeading) continue;
      const key = `h-${blocks.length}`;
      blocks.push(
        level === 2 ? (
          <h2 key={key} className={classes.h2} style={classes.style?.heading}>{inline(text, classes, key)}</h2>
        ) : (
          <h3 key={key} className={classes.h3} style={classes.style?.heading}>{inline(text, classes, key)}</h3>
        )
      );
    } else if (line.startsWith("- ")) {
      if (paragraph.length) {
        const pending = list;
        list = [];
        flush();
        list = pending;
      }
      list.push(line.slice(2));
    } else {
      if (list.length) flush();
      paragraph.push(line);
    }
  }
  flush();
  return <Fragment>{blocks}</Fragment>;
}
