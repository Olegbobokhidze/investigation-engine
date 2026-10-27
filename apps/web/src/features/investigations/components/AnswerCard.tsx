import { CircleCheck, CircleHelp } from "lucide-react";

import { useRevealedText } from "@/shared/hooks/useRevealedText";
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

/** Fast enough not to keep a reader waiting, slow enough to read as being written. */
const answerWordsPerSecond = 30;

export function AnswerCard({ investigation, onSelectSource }: AnswerCardProps) {
  const { status, answer, sources, conflicts, steps } = investigation;
  const sourceNumbers = new Set(sources.map((source) => source.number));
  const { revealedText, isRevealing } = useRevealedText(answer, answerWordsPerSecond);
  const paragraphs = splitParagraphs(revealedText);

  return (
    <section
      aria-label="Answer"
      aria-busy={isRevealing}
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
        {paragraphs.map((paragraph, index) => (
          // Paragraphs grow while the answer is written, so the position is the stable key.
          <p key={index}>
            <CitedText
              text={paragraph}
              sourceNumbers={sourceNumbers}
              onSelectSource={onSelectSource}
            />
            {isRevealing && index === paragraphs.length - 1 && (
              <span
                aria-hidden
                className="ml-0.5 inline-block h-[1.1em] w-0.5 translate-y-0.75 animate-caret bg-accent"
              />
            )}
          </p>
        ))}
      </div>

      {/* The rest follows once the answer is written out. */}
      {!isRevealing && conflicts.length > 0 && (
        <div className="animate-enter motion-reduce:animate-none">
          <ConflictNotice
            conflicts={conflicts}
            sourceNumbers={sourceNumbers}
            onSelectSource={onSelectSource}
          />
        </div>
      )}

      {!isRevealing && steps.length > 0 && <InvestigationSteps steps={steps} />}
    </section>
  );
}
