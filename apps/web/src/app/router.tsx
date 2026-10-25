import { createBrowserRouter, Navigate } from "react-router";

import { DocumentsPage } from "@/features/documents/DocumentsPage";
import { InvestigationPage } from "@/features/investigations/InvestigationPage";
import { paths } from "@/shared/config/paths";

import { AppLayout } from "./AppLayout";

export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      { path: paths.investigate, element: <InvestigationPage /> },
      { path: paths.documents, element: <DocumentsPage /> },
      { path: "*", element: <Navigate to={paths.investigate} replace /> },
    ],
  },
]);
