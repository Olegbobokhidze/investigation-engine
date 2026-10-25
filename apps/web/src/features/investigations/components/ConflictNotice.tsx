import { TriangleAlert } from "lucide-react";

import type { Conflict } from "../types";
import { CitedText } from "./CitedText";

interface ConflictNoticeProps {
  conflicts: Conflict[];
  sourceNumbers: ReadonlySet<number>;
  onSelectSource: (sourceNumber: number) => void;
}

export function ConflictNotice({ conflicts, sourceNumbers, onSelectSource }: ConflictNoticeProps) {
  return (
    <div
      role="note"
      className="flex gap-3.5 rounded-xl border border-warning-border bg-warning-soft px-4.5 py-4"
    >
      <TriangleAlert aria-hidden className="mt-0.5 size-4.5 shrink-0 text-warning-icon" />
      <div className="flex flex-col gap-1">
        <strong className="text-md font-semibold text-warning">Conflicting evidence</strong>
        {conflicts.map((conflict) => (
          <p key={conflict.summary} className="text-md leading-relaxed text-warning-body">
            <CitedText
              text={conflict.summary}
              sourceNumbers={sourceNumbers}
              onSelectSource={onSelectSource}
            />
          </p>
        ))}
      </div>
    </div>
  );
}
