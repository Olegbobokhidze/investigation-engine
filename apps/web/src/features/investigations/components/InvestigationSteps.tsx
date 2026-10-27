import { Check, ListChecks } from "lucide-react";

import type { InvestigationStep } from "../types";

interface InvestigationStepsProps {
  steps: InvestigationStep[];
}

/** The engine's trace: how it planned, which tools it called, and how it verified. */
export function InvestigationSteps({ steps }: InvestigationStepsProps) {
  return (
    <div className="flex flex-col gap-1 border-t border-border-subtle pt-5">
      <div className="mb-2 flex items-center gap-2">
        <ListChecks aria-hidden className="size-4.5 text-ink-tertiary" />
        <h3 className="text-md font-semibold">Investigation steps</h3>
        <span className="text-sm text-ink-muted">{steps.length}</span>
      </div>
      <ol className="flex flex-col">
        {steps.map((step, index) => (
          // Steps are an append-only log, so the position is a stable key.
          <li key={index} className="flex animate-enter gap-3.5 py-2.5 motion-reduce:animate-none">
            <span className="inline-flex size-6 shrink-0 items-center justify-center rounded-full bg-success-soft text-success">
              <Check aria-hidden className="size-3.5" strokeWidth={2.25} />
            </span>
            <div className="flex min-w-0 flex-1 flex-col gap-0.75">
              <span className="text-md font-medium">{step.title}</span>
              <span className="font-mono text-xs wrap-anywhere text-ink-tertiary">
                {step.detail}
              </span>
            </div>
            {step.result !== null && (
              <span className="text-sm whitespace-nowrap text-ink-muted">{step.result}</span>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}
