import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiRequest } from "@/shared/api/client";

import type { CorpusDocument, DocumentListParams, DocumentPage, UploadResponse } from "./types";

export const documentsPageSize = 20;

export const documentKeys = {
  all: ["documents"] as const,
  list: (params: DocumentListParams) => [...documentKeys.all, "list", params] as const,
};

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
  return useQuery({
    queryKey: documentKeys.list(params),
    queryFn: () => listDocuments(params),
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
