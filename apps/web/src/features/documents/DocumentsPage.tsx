import { Search } from "lucide-react";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router";

import { useDebouncedValue } from "@/shared/hooks/useDebouncedValue";
import { usePageTitle } from "@/shared/hooks/usePageTitle";
import { ConfirmDialog } from "@/shared/ui/ConfirmDialog";
import { ErrorNotice } from "@/shared/ui/ErrorNotice";
import { PageContainer } from "@/shared/ui/PageContainer";
import { TextField } from "@/shared/ui/TextField";

import {
  documentsPageSize,
  useDeleteDocument,
  useDocuments,
  useReplaceDocument,
  useUploadDocuments,
} from "./api";
import { DocumentTable } from "./components/DocumentTable";
import { Pagination } from "./components/Pagination";
import { UploadDropzone } from "./components/UploadDropzone";
import { UploadResultList } from "./components/UploadResultList";
import type { CorpusDocument } from "./types";

const searchDebounceMs = 300;

function parsePage(value: string | null): number {
  const page = Number(value);
  return Number.isInteger(page) && page > 0 ? page : 1;
}

/** URL query for the list; defaults (no search, page 1) are left out to keep URLs clean. */
function toSearchParams(search: string, page: number): URLSearchParams {
  const params = new URLSearchParams();
  if (search !== "") params.set("search", search);
  if (page > 1) params.set("page", String(page));
  return params;
}

export function DocumentsPage() {
  usePageTitle("Documents");
  const [searchParams, setSearchParams] = useSearchParams();
  const search = searchParams.get("search") ?? "";
  const page = parsePage(searchParams.get("page"));

  const [searchInput, setSearchInput] = useState(search);
  const debouncedSearch = useDebouncedValue(searchInput.trim(), searchDebounceMs);

  // Runs only when the typed search settles, so Back/Forward navigation isn't overwritten.
  useEffect(() => {
    setSearchParams(
      (current) => {
        if ((current.get("search") ?? "") === debouncedSearch) return current;
        return toSearchParams(debouncedSearch, 1);
      },
      { replace: true },
    );
  }, [debouncedSearch, setSearchParams]);

  function changePage(nextPage: number) {
    setSearchParams(toSearchParams(search, nextPage));
  }

  const documentsQuery = useDocuments({ search, page });
  // Previous rows stay on screen while a new search or page loads (keepPreviousData).
  const isRefreshing = documentsQuery.isPlaceholderData;
  // Also while the typed text waits for the debounce, so the field reacts at once.
  const isSearching = isRefreshing || searchInput.trim() !== debouncedSearch;
  const uploadMutation = useUploadDocuments();
  const replaceMutation = useReplaceDocument();
  const deleteMutation = useDeleteDocument();

  const busyDocumentId = replaceMutation.isPending
    ? replaceMutation.variables.id
    : deleteMutation.isPending
      ? deleteMutation.variables
      : null;
  const changeError = replaceMutation.error ?? deleteMutation.error;

  // Kept after the dialog closes so its text doesn't vanish during the closing animation.
  const [documentToDelete, setDocumentToDelete] = useState<CorpusDocument | null>(null);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);

  function requestDelete(corpusDocument: CorpusDocument) {
    setDocumentToDelete(corpusDocument);
    setIsDeleteDialogOpen(true);
  }

  function confirmDelete() {
    if (!documentToDelete) return;
    deleteMutation.mutate(documentToDelete.id, {
      onSettled: () => {
        setIsDeleteDialogOpen(false);
      },
    });
  }

  return (
    <PageContainer fillViewport className="gap-6">
      <div className="flex flex-col gap-1.5">
        <h1 className="text-2xl font-semibold tracking-tight">Documents</h1>
        <p className="text-md text-ink-tertiary">
          Every question searches all of these. Add your own files, or replace and remove the ones
          you added.
        </p>
      </div>

      <UploadDropzone
        onFilesSelected={(files) => {
          uploadMutation.mutate(files);
        }}
        uploadingFiles={uploadMutation.isPending ? uploadMutation.variables : []}
      >
        {uploadMutation.data && <UploadResultList results={uploadMutation.data.results} />}
      </UploadDropzone>
      {uploadMutation.error && <ErrorNotice title="Upload failed" error={uploadMutation.error} />}

      <TextField
        type="search"
        label="Search by name or ID"
        icon={Search}
        autoComplete="off"
        isLoading={isSearching}
        value={searchInput}
        onChange={(event) => {
          setSearchInput(event.target.value);
        }}
      />

      {changeError && <ErrorNotice title="Couldn’t change the document" error={changeError} />}

      {documentsQuery.error ? (
        <ErrorNotice title="Couldn’t load documents" error={documentsQuery.error} />
      ) : (
        // Takes the remaining height; the table scrolls inside it. On short screens the
        // minimum height wins and <main> scrolls instead, so the table never gets squashed.
        <div className="flex min-h-72 flex-1 flex-col gap-4">
          <p role="status" className="sr-only">
            {documentsQuery.isPending || isRefreshing ? "Loading documents…" : ""}
          </p>
          <DocumentTable
            documents={documentsQuery.data?.items ?? null}
            isRefreshing={isRefreshing}
            onReplace={(corpusDocument, file) => {
              replaceMutation.mutate({ id: corpusDocument.id, file });
            }}
            onDelete={requestDelete}
            busyDocumentId={busyDocumentId}
          />
          {documentsQuery.data && (
            <Pagination
              page={page}
              pageSize={documentsPageSize}
              total={documentsQuery.data.total}
              onPageChange={changePage}
            />
          )}
        </div>
      )}

      <ConfirmDialog
        isOpen={isDeleteDialogOpen}
        title="Delete this document?"
        description={
          <>
            <strong className="font-medium text-ink">{documentToDelete?.title}</strong> will be
            removed and no longer searched. This can’t be undone.
          </>
        }
        confirmLabel="Delete"
        isConfirming={deleteMutation.isPending}
        onConfirm={confirmDelete}
        onCancel={() => {
          setIsDeleteDialogOpen(false);
        }}
      />
    </PageContainer>
  );
}
