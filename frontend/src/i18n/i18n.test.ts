import { describe, expect, it } from "vitest";

import en from "./en.json";
import hi from "./hi.json";
import or from "./or.json";

type Tree = { [key: string]: string | Tree };

function flat(tree: Tree, prefix = ""): Record<string, string> {
  return Object.entries(tree).reduce<Record<string, string>>((out, [key, value]) => (
    typeof value === "string" ? { ...out, [prefix + key]: value } : { ...out, ...flat(value, `${prefix}${key}.`) }
  ), {});
}

const placeholders = (text: string) => [...text.matchAll(/{{\s*(\w+)\s*}}/g)].map((m) => m[1]).sort();
const english = flat(en as Tree);

describe.each([["Hindi", hi], ["Odia", or]])("%s", (_, strings) => {
  const translated = flat(strings as Tree);

  it("has every string the English interface has", () => {
    expect(Object.keys(english).filter((key) => !(key in translated))).toEqual([]);
  });

  it("keeps each string's placeholders, so no value goes missing", () => {
    const broken = Object.keys(english).filter((key) => key in translated
      && placeholders(translated[key]).join() !== placeholders(english[key]).join());
    expect(broken).toEqual([]);
  });

  it("has nothing English doesn't", () => {
    expect(Object.keys(translated).filter((key) => key !== "_note" && !(key in english))).toEqual([]);
  });
});
