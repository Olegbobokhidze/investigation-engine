import { CircleAlert } from "lucide-react";

import { ApiError } from "@/shared/api/client";

interface ErrorNoticeProps {
  title: string;
  error: Error;
}

/** Inline error block. Shows the API's own message, which is written for users. */
export function ErrorNotice({ title, error }: ErrorNoticeProps) {
  const message =
    error instanceof ApiError ? error.message : "Something went wrong. Please try again.";

  return (
    <div
      role="alert"
      className="flex gap-3.5 rounded-xl border border-danger-border bg-danger-soft px-4.5 py-4"
    >
      <CircleAlert aria-hidden className="mt-0.5 size-4.5 shrink-0 text-danger" />
      <div className="flex flex-col gap-1">
        <strong className="text-md font-semibold text-danger">{title}</strong>
        <p className="text-md text-ink-body">{message}</p>
      </div>
    </div>
  );
}
