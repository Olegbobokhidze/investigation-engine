import clsx from "clsx";
import { CircleAlert, LoaderCircle, type LucideIcon } from "lucide-react";
import { useId, type ComponentProps } from "react";

type TextFieldSize = "md" | "lg";

interface TextFieldProps extends Omit<ComponentProps<"input">, "placeholder" | "size"> {
  label: string;
  icon?: LucideIcon;
  hint?: string;
  /** Replaces the hint and marks the field invalid. */
  error?: string;
  /** Shows a spinner at the end of the field, e.g. while a search runs. */
  isLoading?: boolean;
  size?: TextFieldSize;
}

const sizeClasses: Record<TextFieldSize, { input: string; label: string; icon: string }> = {
  md: {
    input: "h-14 pt-5.5 pb-1.5 pl-11.5 text-base",
    label: "top-4.25 left-11.5 text-base",
    icon: "left-4 size-4.5",
  },
  lg: {
    input: "h-16 pt-7 pb-2 pl-12.5 text-lg",
    label: "top-5 left-12.5 text-lg",
    icon: "left-4.5 size-5",
  },
};

/**
 * Text input with a floating label: the label sits inside the empty field and
 * moves above the text on focus or once the field has a value. Pure CSS — it relies
 * on a blank placeholder so `:placeholder-shown` tells whether the field is empty.
 */
export function TextField({
  label,
  icon: Icon,
  hint,
  error,
  isLoading = false,
  size = "md",
  id,
  className,
  ...inputProps
}: TextFieldProps) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const descriptionId = `${inputId}-description`;
  const description = error ?? hint;
  const classes = sizeClasses[size];

  return (
    <div className={className}>
      <div className="group relative">
        <input
          id={inputId}
          placeholder=" "
          aria-invalid={error !== undefined || undefined}
          aria-describedby={description === undefined ? undefined : descriptionId}
          className={clsx(
            "peer block w-full rounded-xl border bg-surface text-ellipsis text-ink transition-[border-color,box-shadow] outline-none",
            isLoading ? "pr-11" : "pr-4",
            "focus:ring-4 disabled:cursor-not-allowed disabled:border-border disabled:bg-subtle disabled:text-ink-disabled",
            error === undefined
              ? "border-border-strong hover:border-border-hover focus:border-accent focus:ring-accent/12"
              : "border-danger focus:ring-danger/12",
            classes.input,
          )}
          {...inputProps}
        />
        <label
          htmlFor={inputId}
          className={clsx(
            "pointer-events-none absolute origin-left -translate-y-1/2 scale-80 whitespace-nowrap transition-[top,scale,color] duration-150",
            "peer-disabled:text-ink-disabled peer-[:placeholder-shown:not(:focus)]:top-1/2 peer-[:placeholder-shown:not(:focus)]:scale-100",
            error === undefined ? "text-ink-muted peer-focus:text-accent" : "text-danger",
            classes.label,
          )}
        >
          {label}
        </label>
        {Icon && (
          <Icon
            aria-hidden
            className={clsx(
              "pointer-events-none absolute top-1/2 -translate-y-1/2 transition-colors",
              error === undefined ? "text-ink-muted group-focus-within:text-accent" : "text-danger",
              classes.icon,
            )}
          />
        )}
        {isLoading && (
          <LoaderCircle
            aria-hidden
            className="pointer-events-none absolute top-1/2 right-4 size-4.5 -translate-y-1/2 animate-spin text-ink-muted motion-reduce:animate-none"
          />
        )}
      </div>
      {description !== undefined && (
        <p
          id={descriptionId}
          className={clsx(
            "mt-1.5 ml-1 flex items-center gap-1.5 text-xs",
            error === undefined ? "text-ink-muted" : "text-danger",
          )}
        >
          {error !== undefined && <CircleAlert aria-hidden className="size-3.5 shrink-0" />}
          {description}
        </p>
      )}
    </div>
  );
}
