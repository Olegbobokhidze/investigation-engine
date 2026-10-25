import clsx from "clsx";
import { LoaderCircle } from "lucide-react";
import type { ComponentProps } from "react";

type ButtonVariant = "primary" | "secondary" | "danger";
type ButtonSize = "md" | "lg";

interface ButtonProps extends ComponentProps<"button"> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  /** Shows a spinner and disables the button while an action runs. */
  isLoading?: boolean;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary: "bg-accent text-white hover:bg-accent-hover",
  secondary: "border-border-strong bg-surface text-ink hover:bg-canvas",
  danger: "bg-danger text-white hover:bg-danger-hover",
};

const sizeClasses: Record<ButtonSize, string> = {
  md: "h-11 rounded-control px-4.5 text-md",
  lg: "h-16 rounded-xl px-6 text-base",
};

export function Button({
  variant = "primary",
  size = "md",
  isLoading = false,
  type = "button",
  disabled,
  className,
  children,
  ...buttonProps
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled === true || isLoading}
      aria-busy={isLoading || undefined}
      className={clsx(
        "inline-flex cursor-pointer items-center justify-center gap-2 border border-transparent font-medium whitespace-nowrap focus-ring transition-colors",
        "disabled:cursor-not-allowed disabled:border-subtle disabled:bg-subtle disabled:text-ink-disabled",
        variantClasses[variant],
        sizeClasses[size],
        className,
      )}
      {...buttonProps}
    >
      {isLoading && <LoaderCircle aria-hidden className="size-4.5 animate-spin" />}
      {children}
    </button>
  );
}
