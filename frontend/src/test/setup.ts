import "@testing-library/jest-dom/vitest";
import "../i18n";

import { cleanup, configure } from "@testing-library/react";
import { afterEach, vi } from "vitest";

// the whole suite runs in parallel in a container: a page that pulls in the 3D body can take a few seconds to appear
configure({ asyncUtilTimeout: 5000 });

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});
