import { BorderBeam } from "border-beam";
import { ThinkingOrb, type OrbState } from "thinking-orbs";

import { usePrefersReducedMotion } from "@/shared/hooks/usePrefersReducedMotion";

import type { InvestigationStep } from "../types";
import { InvestigationSteps } from "./InvestigationSteps";

interface InvestigationProgressProps {
  /** The steps streamed so far. */
  steps: InvestigationStep[];
}

interface Activity {
  orbState: OrbState;
  label: string;
}

/**
 * What the agent is doing now, from the last step it reported: it plans first, searches
 * the sub-questions of the plan, then reads the results and searches more or answers.
 */
function currentActivity(steps: InvestigationStep[]): Activity {
  const lastStep = steps.at(-1);
  if (lastStep === undefined) {
    return { orbState: "weaving", label: "Planning the investigation…" };
  }
  if (lastStep.title === "Planned the investigation") {
    return { orbState: "searching", label: "Searching the documents…" };
  }
  return { orbState: "composing", label: "Reading the evidence and writing the answer…" };
}

/** The live view of a running investigation: its current activity and the steps so far. */
export function InvestigationProgress({ steps }: InvestigationProgressProps) {
  const prefersReducedMotion = usePrefersReducedMotion();
  const activity = currentActivity(steps);

  return (
    // The beam only runs CSS motion, which it doesn't stop by itself under reduced motion.
    <BorderBeam theme="light" colorVariant="ocean" active={!prefersReducedMotion}>
      <div className="flex flex-col gap-5 rounded-2xl border border-border bg-surface p-7">
        <div role="status" className="flex items-center gap-3 text-md text-ink-secondary">
          <ThinkingOrb state={activity.orbState} size={20} theme="light" aria-hidden />
          <span key={activity.label} className="animate-enter motion-reduce:animate-none">
            {activity.label}
          </span>
        </div>
        {steps.length > 0 && <InvestigationSteps steps={steps} />}
      </div>
    </BorderBeam>
  );
}
