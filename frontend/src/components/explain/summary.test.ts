import { describe, expect, it } from "vitest";

import { bulletRest, matchBullet, parseSummary } from "./summary";

const SUMMARY = [
  "These results are outside the lab's range:",
  "• Creatinine is 1.32 mg/dL; the lab's range is 0.72–1.3. A high Creatinine result often causes no symptoms at first; it can go along with swelling in the legs or tiredness.",
  "• Globulin is 3.9 g/dL; the lab's range is 2–3.5.",
  "Talk to your doctor about these results.",
].join("\n");

describe("summary parts", () => {
  it("separates the opening line, the per-result lines and the closing line", () => {
    const parts = parseSummary(SUMMARY);
    expect(parts.intro).toEqual(["These results are outside the lab's range:"]);
    expect(parts.bullets).toHaveLength(2);
    expect(parts.bullets[0].startsWith("Creatinine is 1.32")).toBe(true);
    expect(parts.closing).toEqual(["Talk to your doctor about these results."]);
  });

  it("keeps a summary without bullets as paragraphs", () => {
    expect(parseSummary("All 26 results are within the lab's range.")).toEqual({
      intro: ["All 26 results are within the lab's range."], bullets: [], closing: [],
    });
  });

  it("drops the sentence that restates the value, without splitting at a decimal point", () => {
    const { bullets } = parseSummary(SUMMARY);
    expect(bulletRest(bullets[0])).toBe(
      "A high Creatinine result often causes no symptoms at first; it can go along with swelling in the legs or tiredness.");
    expect(bulletRest(bullets[1])).toBe("");
    expect(bulletRest("Creatinine 1.62 mg/dL; ଲ୍ୟାବର ସୀମା 0.61–1.1। Creatinine ଅଧିକ ହେଲେ ଥକାପଣ।")).toBe("Creatinine ଅଧିକ ହେଲେ ଥକାପଣ।");
  });

  it("matches a bullet to the result with the longest matching name", () => {
    const results = [{ test_name: "Bilirubin" }, { test_name: "Bilirubin, direct" }, { test_name: "Creatinine" }];
    expect(matchBullet("Bilirubin, direct is 0.5 mg/dL; …", results)?.test_name).toBe("Bilirubin, direct");
    expect(matchBullet("Sodium is 142", results)).toBeUndefined();
  });
});
