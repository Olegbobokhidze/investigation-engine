import { describe, expect, it } from "vitest";

import { parseCitations, splitParagraphs } from "./citations";

describe("parseCitations", () => {
  it("splits text around citation markers", () => {
    expect(parseCitations("Pool reduced [1][2], then lag [3].")).toEqual([
      { kind: "text", text: "Pool reduced " },
      { kind: "citation", sourceNumber: 1 },
      { kind: "citation", sourceNumber: 2 },
      { kind: "text", text: ", then lag " },
      { kind: "citation", sourceNumber: 3 },
      { kind: "text", text: "." },
    ]);
  });

  it("returns a single text segment when there are no citations", () => {
    expect(parseCitations("No sources here.")).toEqual([
      { kind: "text", text: "No sources here." },
    ]);
  });

  it("ignores brackets that do not hold a number", () => {
    expect(parseCitations("See [note] and [12]")).toEqual([
      { kind: "text", text: "See [note] and " },
      { kind: "citation", sourceNumber: 12 },
    ]);
  });
});

describe("splitParagraphs", () => {
  it("splits at blank lines and drops empty paragraphs", () => {
    expect(splitParagraphs("First.\n\nSecond.\n  \n\nThird.\n")).toEqual([
      "First.",
      "Second.",
      "Third.",
    ]);
  });
});
