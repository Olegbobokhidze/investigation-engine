import clsx from "clsx";

interface CitationButtonProps {
  sourceNumber: number;
  onSelect: (sourceNumber: number) => void;
  className?: string;
}

export function CitationButton({ sourceNumber, onSelect, className }: CitationButtonProps) {
  return (
    <button
      type="button"
      aria-label={`Show source ${String(sourceNumber)}`}
      onClick={() => {
        onSelect(sourceNumber);
      }}
      className={clsx(
        "inline-flex h-5 min-w-5.5 cursor-pointer items-center justify-center rounded-md border border-accent-border bg-accent-soft px-1.5 font-mono text-2xs leading-none font-medium text-accent focus-ring transition-colors",
        "hover:border-accent hover:bg-accent hover:text-white",
        className,
      )}
    >
      {sourceNumber}
    </button>
  );
}
