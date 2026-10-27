import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useRevealedText } from "./useRevealedText";

/** jsdom has no matchMedia; this one answers the reduced-motion query. */
function stubReducedMotion(prefersReducedMotion: boolean) {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: prefersReducedMotion,
    media: query,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }));
}

describe("useRevealedText", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("reveals the text a word at a time", () => {
    stubReducedMotion(false);
    const { result } = renderHook(() => useRevealedText("Pool cut [1]. Then reverted.", 10));

    expect(result.current).toEqual({ revealedText: "", isRevealing: true });
    act(() => {
      vi.advanceTimersByTime(200);
    });
    expect(result.current.revealedText).toBe("Pool cut ");
    act(() => {
      vi.advanceTimersByTime(300);
    });
    expect(result.current).toEqual({
      revealedText: "Pool cut [1]. Then reverted.",
      isRevealing: false,
    });
  });

  it("starts again from the first word for a new text", () => {
    stubReducedMotion(false);
    const { result, rerender } = renderHook(({ text }) => useRevealedText(text, 10), {
      initialProps: { text: "First answer." },
    });
    act(() => {
      vi.advanceTimersByTime(1000);
    });

    rerender({ text: "Second answer here." });

    expect(result.current).toEqual({ revealedText: "", isRevealing: true });
  });

  it("shows the whole text at once under reduced motion", () => {
    stubReducedMotion(true);
    const { result } = renderHook(() => useRevealedText("Pool cut [1].", 10));

    expect(result.current).toEqual({ revealedText: "Pool cut [1].", isRevealing: false });
  });
});
