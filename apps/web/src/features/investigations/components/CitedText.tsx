import { parseCitations } from "../citations";
import { CitationButton } from "./CitationButton";

interface CitedTextProps {
  text: string;
  /** Numbers of the sources that exist; any other `[n]` is shown as plain text. */
  sourceNumbers: ReadonlySet<number>;
  onSelectSource: (sourceNumber: number) => void;
}

/** Renders text with its `[n]` markers turned into citation buttons. */
export function CitedText({ text, sourceNumbers, onSelectSource }: CitedTextProps) {
  return parseCitations(text).map((segment, index) => {
    if (segment.kind === "text") return segment.text;
    if (!sourceNumbers.has(segment.sourceNumber)) return `[${String(segment.sourceNumber)}]`;
    return (
      <CitationButton
        // Segments never reorder, so the position is a stable key.
        key={index}
        sourceNumber={segment.sourceNumber}
        onSelect={onSelectSource}
        className="mx-px align-[2px]"
      />
    );
  });
}
