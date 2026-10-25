import clsx from "clsx";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

export type BadgeTone = "success" | "neutral" | "danger" | "warning" | "accent";
type BadgeSize = "sm" | "md";

interface BadgeProps {
  tone: BadgeTone;
  size?: BadgeSize;
  /** Leading icon; when omitted, a status dot is shown instead (except for `accent`). */
  icon?: LucideIcon;
  className?: string;
  children: ReactNode;
}

const toneClasses: Record<BadgeTone, { badge: string; dot: string | null }> = {
  success: { badge: "bg-success-soft text-success", dot: "bg-success-dot" },
  neutral: { badge: "bg-subtle text-ink-secondary", dot: "bg-neutral-dot" },
  danger: { badge: "bg-danger-soft text-danger", dot: "bg-danger-dot" },
  warning: { badge: "bg-warning-soft text-warning", dot: "bg-warning-icon" },
  accent: { badge: "bg-accent-soft text-accent", dot: null },
};

const sizeClasses: Record<BadgeSize, { badge: string; icon: string }> = {
  sm: { badge: "h-6 rounded-[7px] px-2.25 text-xs", icon: "size-3.5" },
  md: { badge: "h-7 rounded-lg px-2.5 text-sm", icon: "size-4" },
};

export function Badge({ tone, size = "sm", icon: Icon, className, children }: BadgeProps) {
  const classes = toneClasses[tone];

  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 font-medium whitespace-nowrap",
        sizeClasses[size].badge,
        classes.badge,
        className,
      )}
    >
      {Icon ? (
        <Icon aria-hidden className={sizeClasses[size].icon} />
      ) : (
        classes.dot !== null && (
          <span aria-hidden className={clsx("size-1.5 rounded-full", classes.dot)} />
        )
      )}
      {children}
    </span>
  );
}
