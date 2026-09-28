import { describe, expect, it } from "vitest";

import {
  formatComputed, formatDate, formatPercent, formatRange, formatUnit, formatValue, ordinal, position, spanYears, trimDecimal,
} from "./format";

describe("trimDecimal", () => {
  it.each([
    ["4.8030", "4.803"],
    ["140.00", "140"],
    ["12", "12"],
    ["0.50", "0.5"],
    [null, ""],
  ])("%s -> %s", (input, expected) => {
    expect(trimDecimal(input)).toBe(expected);
  });
});

describe("formatComputed", () => {
  it.each([
    ["79.2704", "79.27"],
    ["1.821232", "1.821"],
    ["154.2933", "154.3"],
    ["4.8030", "4.803"],
    ["150000", "150000"],
    ["1234.6", "1235"],
    ["0.5", "0.5"],
  ])("%s -> %s", (input, expected) => {
    expect(formatComputed(input)).toBe(expected);
  });
});

describe("formatUnit", () => {
  it("writes powers of ten the way reports print them", () => {
    expect(formatUnit("10^6/µL")).toBe("×10⁶/µL");
    expect(formatUnit("10^3/µL")).toBe("×10³/µL");
    expect(formatUnit("g/dL")).toBe("g/dL");
    expect(formatUnit(null)).toBe("");
  });
});

describe("formatRange", () => {
  it("shows both ends, or the one that exists", () => {
    expect(formatRange("13.00", "17.00")).toBe("13 – 17");
    expect(formatRange(null, "200")).toBe("< 200");
    expect(formatRange("40", null)).toBe("> 40");
    expect(formatRange(null, null)).toBe("");
  });
});

describe("position", () => {
  it("places the value against its range", () => {
    expect(position("12.1", "13", "17")).toBe("low");
    expect(position("15", "13", "17")).toBe("normal");
    expect(position("17.5", "13", "17")).toBe("high");
    expect(position("17", "13", "17")).toBe("normal");
    expect(position("5", null, null)).toBe("unknown");
    expect(position(null, "1", "2")).toBe("unknown");
  });
});

describe("formatDate", () => {
  it("never shifts a calendar date across time zones", () => {
    expect(formatDate("2026-09-01", "en")).toBe("1 Sept 2026");
  });
});

describe("analysis formatting", () => {
  it("formats values, changes and ordinals", () => {
    expect(formatValue("1.1", 2)).toBe("1.10");
    expect(formatValue("79.2704", 0)).toBe("79");
    expect(formatPercent(0.1234)).toBe("+12 %");
    expect(formatPercent(-0.045)).toBe("−4.5 %");
    expect(formatPercent(0)).toBe("0.0 %");
    expect([1, 2, 3, 4, 11, 12, 13, 21, 52, 95].map(ordinal)).toEqual(
      ["1st", "2nd", "3rd", "4th", "11th", "12th", "13th", "21st", "52nd", "95th"]);
    expect(spanYears("2022-06-01", "2025-06-01")).toBeCloseTo(3, 1);
  });
});
