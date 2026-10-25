export type CitedTextSegment =
  { kind: "text"; text: string } | { kind: "citation"; sourceNumber: number };

const citationPattern = /\[(\d+)\]/g;

/** Splits text such as `"Pool reduced [1][2]."` into plain text and citation segments. */
export function parseCitations(text: string): CitedTextSegment[] {
  const segments: CitedTextSegment[] = [];
  let textStart = 0;

  for (const match of text.matchAll(citationPattern)) {
    if (match.index > textStart) {
      segments.push({ kind: "text", text: text.slice(textStart, match.index) });
    }
    segments.push({ kind: "citation", sourceNumber: Number(match[1]) });
    textStart = match.index + match[0].length;
  }

  if (textStart < text.length) {
    segments.push({ kind: "text", text: text.slice(textStart) });
  }
  return segments;
}

/** DOM id of a source card, so a citation can scroll to it. */
export function sourceElementId(sourceNumber: number): string {
  return `source-${String(sourceNumber)}`;
}

/** Splits an answer into paragraphs at blank lines. */
export function splitParagraphs(text: string): string[] {
  return text
    .split(/\n\s*\n/)
    .map((paragraph) => paragraph.trim())
    .filter((paragraph) => paragraph !== "");
}
