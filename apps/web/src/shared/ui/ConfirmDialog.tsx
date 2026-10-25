import { TriangleAlert } from "lucide-react";
import { useEffect, useId, useRef, type ReactNode } from "react";

import { Button } from "./Button";

interface ConfirmDialogProps {
  isOpen: boolean;
  title: string;
  description: ReactNode;
  confirmLabel: string;
  /** Keeps the dialog open with a spinner while the confirmed action runs. */
  isConfirming?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/**
 * Modal that asks the user to confirm a destructive action.
 *
 * Built on `<dialog>` + `showModal()`, which traps focus, closes on Escape and makes the
 * rest of the page inert. Cancel comes first, so it gets the initial focus — the safe choice.
 */
export function ConfirmDialog({
  isOpen,
  title,
  description,
  confirmLabel,
  isConfirming = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const descriptionId = useId();

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (isOpen && !dialog.open) dialog.showModal();
    if (!isOpen && dialog.open) dialog.close();
  }, [isOpen]);

  function cancel() {
    if (!isConfirming) onCancel();
  }

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby={titleId}
      aria-describedby={descriptionId}
      // Escape: let React state decide when the dialog closes.
      onCancel={(event) => {
        event.preventDefault();
        cancel();
      }}
      // A click on the dialog element itself (not its content) is a click on the backdrop.
      onClick={(event) => {
        if (event.target === event.currentTarget) cancel();
      }}
      className="m-auto w-[calc(100%-2rem)] max-w-md scale-95 overflow-hidden rounded-2xl border border-border bg-surface p-0 text-ink opacity-0 shadow-xl transition-[opacity,scale,display,overlay] transition-discrete duration-150 ease-out backdrop:bg-ink/30 open:scale-100 open:opacity-100 starting:open:scale-95 starting:open:opacity-0"
    >
      <div className="flex gap-4 p-6">
        <span className="inline-flex size-10 shrink-0 items-center justify-center rounded-full bg-danger-soft text-danger">
          <TriangleAlert aria-hidden className="size-5" />
        </span>
        <div className="flex min-w-0 flex-col gap-1.5 pt-1.5">
          <h2 id={titleId} className="text-lg font-semibold">
            {title}
          </h2>
          <p id={descriptionId} className="text-md leading-relaxed text-ink-tertiary">
            {description}
          </p>
        </div>
      </div>
      <div className="flex justify-end gap-3 border-t border-border-subtle bg-canvas px-6 py-4">
        <Button variant="secondary" disabled={isConfirming} onClick={cancel}>
          Cancel
        </Button>
        <Button variant="danger" isLoading={isConfirming} onClick={onConfirm}>
          {confirmLabel}
        </Button>
      </div>
    </dialog>
  );
}
