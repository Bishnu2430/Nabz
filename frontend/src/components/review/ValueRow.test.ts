import { describe, expect, it } from "vitest";

import { displayValue } from "./ValueRow";

describe("displayValue", () => {
  it("keeps the printed precision when the value was not converted", () => {
    expect(displayValue({ raw_value: "14.0", value: "14.0000" })).toEqual({ value: "14.0", converted: false });
  });

  it("shows the canonical value when the unit was converted", () => {
    expect(displayValue({ raw_value: "4,803", value: "4.8030" })).toEqual({ value: "4.803", converted: true });
  });

  it("rounds a computed value to a readable precision", () => {
    expect(displayValue({ raw_value: "4.4", value: "79.2704" })).toEqual({ value: "79.27", converted: true });
  });

  it("drops thousands separators from an unconverted value", () => {
    expect(displayValue({ raw_value: "1,50,000", value: "150000" })).toEqual({ value: "150000", converted: false });
  });

  it("falls back to the printed text when nothing could be parsed", () => {
    expect(displayValue({ raw_value: "Nil", value: null })).toEqual({ value: "Nil", converted: false });
  });
});
