import { useState } from "react";

import { usePageTitle } from "@/shared/hooks/usePageTitle";
import { ErrorNotice } from "@/shared/ui/ErrorNotice";
import { PageContainer } from "@/shared/ui/PageContainer";

import { useInvestigationStream } from "./api";
import { sourceElementId } from "./citations";
import { AnswerCard } from "./components/AnswerCard";
import { InvestigationProgress } from "./components/InvestigationProgress";
import { QuestionForm } from "./components/QuestionForm";
import { SourceList } from "./components/SourceList";

const minQuestionLength = 10;

export function InvestigationPage() {
  usePageTitle("Investigate");
  const [question, setQuestion] = useState("");
  const [validationError, setValidationError] = useState<string>();
  const [activeSourceNumber, setActiveSourceNumber] = useState<number | null>(null);
  const investigationMutation = useInvestigationStream();

  function submitQuestion() {
    const trimmedQuestion = question.trim();
    if (trimmedQuestion.length < minQuestionLength) {
      setValidationError(`Ask a question of at least ${String(minQuestionLength)} characters.`);
      return;
    }
    setValidationError(undefined);
    setActiveSourceNumber(null);
    investigationMutation.mutate({ question: trimmedQuestion });
  }

  function selectSource(sourceNumber: number) {
    setActiveSourceNumber(sourceNumber);
    document
      .getElementById(sourceElementId(sourceNumber))
      ?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  const investigation = investigationMutation.data;

  return (
    <PageContainer className="gap-7">
      <QuestionForm
        question={question}
        onQuestionChange={(nextQuestion) => {
          setQuestion(nextQuestion);
          setValidationError(undefined);
        }}
        onSubmit={submitQuestion}
        error={validationError}
        isPending={investigationMutation.isPending}
      />

      {investigationMutation.isPending ? (
        <InvestigationProgress steps={investigationMutation.steps} />
      ) : investigationMutation.error ? (
        <ErrorNotice title="The investigation failed" error={investigationMutation.error} />
      ) : investigation ? (
        <div className="flex flex-wrap items-start gap-6">
          {/* Keyed so a new answer is written out from the start again. */}
          <AnswerCard
            key={investigation.id}
            investigation={investigation}
            onSelectSource={selectSource}
          />
          {investigation.sources.length > 0 && (
            <SourceList
              sources={investigation.sources}
              activeSourceNumber={activeSourceNumber}
              onSelectSource={selectSource}
            />
          )}
        </div>
      ) : (
        <p className="rounded-2xl border border-dashed border-border-dashed px-6 py-10 text-center text-md text-ink-muted">
          Ask a question to start. The answer appears here with the sources it is based on.
        </p>
      )}
    </PageContainer>
  );
}
