import clsx from "clsx";
import type { ReactNode } from "react";

interface PageContainerProps {
  /**
   * Fit the page to the viewport instead of letting it grow, so a child with
   * `min-h-0 overflow-auto` (e.g. a long table) scrolls inside the page.
   */
  fillViewport?: boolean;
  /** Layout classes only, such as the gap between sections. */
  className?: string;
  children: ReactNode;
}

/** Centered, padded column for a page's content inside `AppLayout`'s scrolling `<main>`. */
export function PageContainer({ fillViewport = false, className, children }: PageContainerProps) {
  return (
    <div
      className={clsx(
        "mx-auto flex w-full max-w-7xl flex-col px-8 pt-10",
        fillViewport ? "min-h-0 flex-1 pb-8" : "pb-14",
        className,
      )}
    >
      {children}
    </div>
  );
}
