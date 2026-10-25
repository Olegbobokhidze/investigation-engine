import { ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "@/shared/ui/Button";

interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
}

const numberFormat = new Intl.NumberFormat("en-US");

export function Pagination({ page, pageSize, total, onPageChange }: PaginationProps) {
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const firstItem = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const lastItem = Math.min(page * pageSize, total);

  return (
    <nav aria-label="Pagination" className="flex shrink-0 flex-wrap items-center gap-3">
      <span className="mr-auto text-sm text-ink-muted">
        {total === 0
          ? "No documents"
          : `Showing ${numberFormat.format(firstItem)}–${numberFormat.format(lastItem)} of ${numberFormat.format(total)} documents`}
      </span>
      <Button
        variant="secondary"
        disabled={page <= 1}
        onClick={() => {
          onPageChange(page - 1);
        }}
      >
        <ChevronLeft aria-hidden className="size-4.5" />
        Previous
      </Button>
      <Button
        variant="secondary"
        disabled={page >= pageCount}
        onClick={() => {
          onPageChange(page + 1);
        }}
      >
        Next
        <ChevronRight aria-hidden className="size-4.5" />
      </Button>
    </nav>
  );
}
