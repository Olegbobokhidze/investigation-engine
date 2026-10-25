import { CircleCheck, CircleHelp } from "lucide-react";

import { Badge } from "@/shared/ui/Badge";

import { splitParagraphs } from "../citations";
import type { Investigation } from "../types";
import { CitedText } from "./CitedText";
import { ConflictNotice } from "./ConflictNotice";
import { InvestigationSteps } from "./InvestigationSteps";

interface AnswerCardProps {
  investigation: Investigation;
  onSelectSource: (sourceNumber: number) => void;
}

export function AnswerCard({ investigation, onSelectSource }: AnswerCardProps) {
  const { status, answer, sources, conflicts, steps } = investigation;
  const sourceNumbers = new Set(sources.map((source) => source.number));

  return (
    <section
      aria-label="Answer"
      className="flex min-w-0 flex-[999_1_600px] flex-col gap-6 rounded-2xl border border-border bg-surface p-7"
    >
      <div className="flex items-center gap-3">
        {status === "answered" ? (
          <>
            <Badge tone="success" size="md" icon={CircleCheck}>
              Answered
            </Badge>
            <span className="text-sm text-ink-muted">
              Grounded in {sources.length} {sources.length === 1 ? "source" : "sources"}
            </span>
          </>
        ) : (
          <>
            <Badge tone="neutral" size="md" icon={CircleHelp}>
              Not enough evidence
            </Badge>
            <span className="text-sm text-ink-muted">No answer given</span>
          </>
        )}
      </div>

      <div className="flex flex-col gap-3.5 text-base leading-[1.7] text-ink-body">
        {splitParagraphs(answer).map((paragraph) => (
          <p key={paragraph}>
            <CitedText
              text={paragraph}
              sourceNumbers={sourceNumbers}
              onSelectSource={onSelectSource}
            />
          </p>
        ))}
      </div>

      {conflicts.length > 0 && (
        <ConflictNotice
          conflicts={conflicts}
          sourceNumbers={sourceNumbers}
          onSelectSource={onSelectSource}
        />
      )}

      {steps.length > 0 && <InvestigationSteps steps={steps} />}
    </section>
  );
}
