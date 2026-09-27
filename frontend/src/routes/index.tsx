import { Navigate, type RouteObject } from "react-router-dom";

import { AppShell } from "../components/AppShell";
import { RouteError } from "../components/RouteError";
import Home from "./Home";
import NotFound from "./NotFound";
import Person from "./Person";
import Review from "./Review";
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
      { path: "/r/:id/review", element: <Review /> },
      { path: "*", element: <NotFound /> },
    ],
  },
];
