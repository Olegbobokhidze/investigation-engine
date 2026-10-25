import { ArrowRight, Search } from "lucide-react";
import type { SubmitEvent } from "react";

import { Button } from "@/shared/ui/Button";
import { TextField } from "@/shared/ui/TextField";

interface QuestionFormProps {
  question: string;
  onQuestionChange: (question: string) => void;
  onSubmit: () => void;
  error?: string;
  isPending: boolean;
}

export function QuestionForm({
  question,
  onQuestionChange,
  onSubmit,
  error,
  isPending,
}: QuestionFormProps) {
  function handleSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit();
  }

  return (
    <div className="flex flex-col gap-2.5">
      <form aria-label="Ask a question" onSubmit={handleSubmit} className="flex flex-wrap gap-3">
        <TextField
          size="lg"
          label="Ask an investigative question"
          icon={Search}
          autoComplete="off"
          value={question}
          onChange={(event) => {
            onQuestionChange(event.target.value);
          }}
          error={error}
          className="min-w-0 flex-[999_1_420px]"
        />
        <Button type="submit" size="lg" isLoading={isPending} className="flex-[1_0_auto]">
          {isPending ? "Investigating…" : "Investigate"}
          {!isPending && <ArrowRight aria-hidden className="size-4.5" />}
        </Button>
      </form>
      <p className="ml-1 text-sm text-ink-muted">
        Searches every document in the collection. Every claim cites its source, and when the
        documents don’t support an answer, the engine says so.
      </p>
    </div>
  );
}
