import "./index.css";
import "./styles/polish.css";
import "./i18n";

import { QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";

import { makeQueryClient } from "./api/queryClient";
import { routes } from "./routes";

const queryClient = makeQueryClient();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={createBrowserRouter(routes)} />
    </QueryClientProvider>
  </StrictMode>,
);
