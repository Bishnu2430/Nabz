import { Navigate, type RouteObject } from "react-router-dom";

import { AppShell } from "../components/AppShell";
import { RouteError } from "../components/RouteError";
import Home from "./Home";
import Insights from "./Insights";
import NotFound from "./NotFound";
import Person from "./Person";
import Review from "./Review";
import TestHistory from "./TestHistory";
import Upload from "./Upload";

// Page map: docs/12-ux-and-access-design.md §6. `/` becomes the public landing page with sign-in (Sprint 6).
export const routes: RouteObject[] = [
  {
    element: <AppShell />,
    errorElement: <RouteError />,
    children: [
      { path: "/", element: <Navigate to="/home" replace /> },
      { path: "/home", element: <Home /> },
      { path: "/p/:id", element: <Person /> },
      { path: "/p/:id/upload", element: <Upload /> },
      { path: "/p/:id/tests/:code", element: <TestHistory /> },
      { path: "/r/:id", element: <Insights /> },
      { path: "/r/:id/review", element: <Review /> },
      { path: "*", element: <NotFound /> },
    ],
  },
];
