import type { RouteObject } from "react-router-dom";

import { AppShell } from "../components/AppShell";
import { RequireAuth } from "../components/RequireAuth";
import { RouteError } from "../components/RouteError";
import ForgotPassword from "./account/ForgotPassword";
import Login from "./account/Login";
import ResetPassword from "./account/ResetPassword";
import Settings from "./account/Settings";
import Signup from "./account/Signup";
import VerifyEmail from "./account/VerifyEmail";
import AllTests from "./AllTests";
import Compare from "./Compare";
import Home from "./Home";
import Insights from "./Insights";
import Landing from "./Landing";
import Legal from "./Legal";
import NotFound from "./NotFound";
import Person from "./Person";
import Review from "./Review";
import Story from "./Story";
import Summary from "./Summary";
import TestHistory from "./TestHistory";
import Upload from "./Upload";

// Page map: docs/12-ux-and-access-design.md §6.
export const routes: RouteObject[] = [
  {
    element: <AppShell />,
    errorElement: <RouteError />,
    children: [
      { path: "/", element: <Landing /> },
      { path: "/login", element: <Login /> },
      { path: "/signup", element: <Signup /> },
      { path: "/verify-email", element: <VerifyEmail /> },
      { path: "/forgot-password", element: <ForgotPassword /> },
      { path: "/reset-password", element: <ResetPassword /> },
      { path: "/privacy", element: <Legal page="privacy" /> },
      { path: "/safety", element: <Legal page="safety" /> },
      {
        element: <RequireAuth />,
        children: [
          { path: "/home", element: <Home /> },
          { path: "/p/:id", element: <Person /> },
          { path: "/p/:id/upload", element: <Upload /> },
          { path: "/p/:id/tests", element: <AllTests /> },
          { path: "/p/:id/tests/:code", element: <TestHistory /> },
          { path: "/p/:id/story", element: <Story /> },
          { path: "/p/:id/summary", element: <Summary /> },
          { path: "/p/:id/compare", element: <Compare /> },
          { path: "/r/:id", element: <Insights /> },
          { path: "/r/:id/review", element: <Review /> },
          { path: "/settings", element: <Settings /> },
        ],
      },
      { path: "*", element: <NotFound /> },
    ],
  },
];
