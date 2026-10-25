import clsx from "clsx";

import { FileTypeTag } from "@/shared/ui/FileTypeTag";

import { sourceElementId } from "../citations";
import type { Source } from "../types";
import { CitationButton } from "./CitationButton";

interface SourceListProps {
  sources: Source[];
  activeSourceNumber: number | null;
  onSelectSource: (sourceNumber: number) => void;
}

export function SourceList({ sources, activeSourceNumber, onSelectSource }: SourceListProps) {
  return (
    <aside aria-label="Sources" className="flex min-w-0 flex-[1_1_340px] flex-col gap-3">
      <div className="flex items-baseline gap-2 px-1">
        <h2 className="text-base font-semibold">Sources</h2>
        <span className="text-sm text-ink-muted">{sources.length} cited</span>
      </div>
      {sources.map((source) => (
        <article
          key={source.number}
          id={sourceElementId(source.number)}
          className={clsx(
            "flex scroll-mt-6 flex-col gap-2.5 rounded-xl border bg-surface p-4 transition-[border-color,box-shadow]",
            source.number === activeSourceNumber
              ? "border-accent ring-3 ring-accent/10"
              : "border-border",
          )}
        >
          <div className="flex items-center gap-2.5">
            <CitationButton sourceNumber={source.number} onSelect={onSelectSource} />
            <FileTypeTag fileType={source.fileType} />
          </div>
          <h3 className="text-md font-semibold wrap-anywhere">{source.documentTitle}</h3>
          <p className="text-sm leading-relaxed text-ink-secondary">{source.excerpt}</p>
        </article>
      ))}
      <p className="mx-1 mt-1 text-xs text-ink-muted">
        Select a citation number to highlight its source.
      </p>
    </aside>
  );
}
