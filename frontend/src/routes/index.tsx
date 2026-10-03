import type { RouteObject } from "react-router-dom";

import { AppShell } from "../components/AppShell";
import { RequireAuth, RequireRole } from "../components/RequireAuth";
import { RouteError } from "../components/RouteError";
import ForgotPassword from "./account/ForgotPassword";
import Login from "./account/Login";
import ResetPassword from "./account/ResetPassword";
import Settings from "./account/Settings";
import Signup from "./account/Signup";
import VerifyEmail from "./account/VerifyEmail";
import About from "./About";
import AllTests from "./AllTests";
import ClinicianHome from "./clinician/ClinicianHome";
import ClinicianReport from "./clinician/ClinicianReport";
import Compare from "./Compare";
import EmergencyCard from "./EmergencyCard";
import Help from "./Help";
import Home from "./Home";
import Insights from "./Insights";
import Landing from "./Landing";
import Legal from "./Legal";
import NotFound from "./NotFound";
import Person from "./Person";
import Readings from "./Readings";
import Review from "./Review";
import Shared from "./Shared";
import Admin from "./staff/Admin";
import SafetyReview from "./staff/SafetyReview";
import Story from "./Story";
import Summary from "./Summary";
import TestHistory from "./TestHistory";
import Upload from "./Upload";
import Welcome from "./Welcome";

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
      { path: "/terms", element: <Legal page="terms" /> },
      { path: "/about", element: <About /> },
      { path: "/help", element: <Help /> },
      { path: "/s/:token", element: <Shared /> },
      {
        element: <RequireAuth />,
        children: [
          { path: "/home", element: <Home /> },
          { path: "/welcome", element: <Welcome /> },
          { path: "/p/:id", element: <Person /> },
          { path: "/p/:id/upload", element: <Upload /> },
          { path: "/p/:id/tests", element: <AllTests /> },
          { path: "/p/:id/tests/:code", element: <TestHistory /> },
          { path: "/p/:id/story", element: <Story /> },
          { path: "/p/:id/summary", element: <Summary /> },
          { path: "/p/:id/compare", element: <Compare /> },
          { path: "/p/:id/readings", element: <Readings /> },
          { path: "/p/:id/card", element: <EmergencyCard /> },
          { path: "/r/:id", element: <Insights /> },
          { path: "/r/:id/review", element: <Review /> },
          { path: "/settings", element: <Settings /> },
          {
            element: <RequireRole roles={["clinician"]} title="clinician.forbidden_title" />,
            children: [{ path: "/clinician", element: <ClinicianHome /> }, { path: "/clinician/r/:id", element: <ClinicianReport /> }],
          },
          { element: <RequireRole roles={["reviewer"]} />, children: [{ path: "/review", element: <SafetyReview /> }] },
          { element: <RequireRole roles={["reviewer", "admin"]} />, children: [{ path: "/admin", element: <Admin /> }] },
        ],
      },
      { path: "*", element: <NotFound /> },
    ],
  },
];
