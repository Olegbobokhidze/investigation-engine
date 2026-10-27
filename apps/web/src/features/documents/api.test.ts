import { QueryClient } from "@tanstack/react-query";
import { describe, expect, it } from "vitest";

import { documentKeys, hasEmptyNarrowerSearch } from "./api";

function clientWith(search: string, total: number): QueryClient {
  const queryClient = new QueryClient();
  queryClient.setQueryData(documentKeys.list({ search, page: 1 }), {
    items: [],
    total,
    page: 1,
    pageSize: 20,
  });
  return queryClient;
}

describe("hasEmptyNarrowerSearch", () => {
  it("is true when a search inside this one found nothing", () => {
    expect(hasEmptyNarrowerSearch(clientWith("zzq", 0), "ZZQX")).toBe(true);
  });

  it("is false when the earlier search found documents", () => {
    expect(hasEmptyNarrowerSearch(clientWith("inc", 3), "incident")).toBe(false);
  });

  it("is false when the new search doesn't contain the empty one", () => {
    expect(hasEmptyNarrowerSearch(clientWith("zzq", 0), "zz")).toBe(false);
  });

  it("doesn't trust an empty result after the list was invalidated", async () => {
    const queryClient = clientWith("zzq", 0);
    await queryClient.invalidateQueries({ queryKey: documentKeys.all });

    expect(hasEmptyNarrowerSearch(queryClient, "zzqx")).toBe(false);
  });
});
