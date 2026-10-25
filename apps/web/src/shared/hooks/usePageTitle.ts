import { useEffect } from "react";

const appName = "Investigation Engine";

/** Sets the browser tab title to "<pageTitle> · Investigation Engine". */
export function usePageTitle(pageTitle: string): void {
  useEffect(() => {
    document.title = `${pageTitle} · ${appName}`;
  }, [pageTitle]);
}
