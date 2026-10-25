import clsx from "clsx";
import type { ComponentProps } from "react";

type IconButtonTone = "default" | "danger";

interface IconButtonProps extends Omit<ComponentProps<"button">, "aria-label"> {
  /** Accessible name; also shown as a tooltip. */
  label: string;
  tone?: IconButtonTone;
}

const toneClasses: Record<IconButtonTone, string> = {
  default: "hover:bg-subtle hover:text-ink",
  danger: "hover:bg-danger-soft hover:text-danger",
};

export function IconButton({
  label,
  tone = "default",
  type = "button",
  className,
  children,
  ...buttonProps
}: IconButtonProps) {
  return (
    <button
      type={type}
      aria-label={label}
      title={label}
      className={clsx(
        "inline-flex size-11 cursor-pointer items-center justify-center rounded-control text-ink-tertiary focus-ring transition-colors",
        "disabled:cursor-not-allowed disabled:bg-transparent disabled:text-border-hover",
        toneClasses[tone],
        className,
      )}
      {...buttonProps}
    >
      {children}
    </button>
  );
}
