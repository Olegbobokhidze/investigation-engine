import {
  keepPreviousData,
  type QueryClient,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { apiRequest } from "@/shared/api/client";

import type { CorpusDocument, DocumentListParams, DocumentPage, UploadResponse } from "./types";

export const documentsPageSize = 20;

export const documentKeys = {
  all: ["documents"] as const,
  lists: () => [...documentKeys.all, "list"] as const,
  list: (params: DocumentListParams) => [...documentKeys.lists(), params] as const,
};

const emptyPage = (page: number): DocumentPage => ({
  items: [],
  total: 0,
  page,
  pageSize: documentsPageSize,
});

/**
 * True when a shorter search inside this one already found nothing. The API matches a
 * substring of the title or id, so adding characters can't bring results back, and the
 * request is skipped while the user keeps typing. Uploads and changes invalidate the list
 * queries, so an empty result from before them is not trusted.
 */
export function hasEmptyNarrowerSearch(queryClient: QueryClient, search: string): boolean {
  const needle = search.toLowerCase();
  return queryClient
    .getQueriesData<DocumentPage>({ queryKey: documentKeys.lists() })
    .some(([queryKey, data]) => {
      // Keys under documentKeys.lists() are only made by documentKeys.list.
      const [, , params] = queryKey as ReturnType<typeof documentKeys.list>;
      return (
        data?.total === 0 &&
        params.search !== "" &&
        needle.includes(params.search.toLowerCase()) &&
        queryClient.getQueryState(queryKey)?.isInvalidated === false
      );
    });
}

export function listDocuments({ search, page }: DocumentListParams): Promise<DocumentPage> {
  const query = new URLSearchParams({ page: String(page), pageSize: String(documentsPageSize) });
  if (search !== "") query.set("search", search);
  return apiRequest(`/documents?${query.toString()}`);
}

export function uploadDocuments(files: File[]): Promise<UploadResponse> {
  const formData = new FormData();
  for (const file of files) formData.append("files", file);
  return apiRequest("/documents", { method: "POST", body: formData });
}

export function replaceDocument({ id, file }: { id: string; file: File }): Promise<CorpusDocument> {
  const formData = new FormData();
  formData.append("file", file);
  return apiRequest(`/documents/${encodeURIComponent(id)}`, { method: "PUT", body: formData });
}

export function deleteDocument(id: string): Promise<void> {
  return apiRequest(`/documents/${encodeURIComponent(id)}`, { method: "DELETE" });
}

export function useDocuments(params: DocumentListParams) {
  const queryClient = useQueryClient();
  return useQuery({
    queryKey: documentKeys.list(params),
    queryFn: () =>
      params.search !== "" && hasEmptyNarrowerSearch(queryClient, params.search)
        ? Promise.resolve(emptyPage(params.page))
        : listDocuments(params),
    placeholderData: keepPreviousData,
  });
}

/** Mutations that change the document list refetch it when they finish. */
function useInvalidateDocuments() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: documentKeys.all });
}

export function useUploadDocuments() {
  const invalidateDocuments = useInvalidateDocuments();
  return useMutation({ mutationFn: uploadDocuments, onSettled: invalidateDocuments });
}

export function useReplaceDocument() {
  const invalidateDocuments = useInvalidateDocuments();
  return useMutation({ mutationFn: replaceDocument, onSettled: invalidateDocuments });
}

export function useDeleteDocument() {
  const invalidateDocuments = useInvalidateDocuments();
  return useMutation({ mutationFn: deleteDocument, onSettled: invalidateDocuments });
}
