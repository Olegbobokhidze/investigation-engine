import { useEffect, useState } from "react";

import { usePrefersReducedMotion } from "./usePrefersReducedMotion";

/** A word with the whitespace after it, so joining the words gives back the text. */
const wordPattern = /\S+\s*/g;

interface RevealedText {
  revealedText: string;
  isRevealing: boolean;
}

/**
 * Reveals `text` a word at a time, as if it were being written. The text is already
 * complete; this only paces how it appears. Shown at once under reduced motion.
 */
export function useRevealedText(text: string, wordsPerSecond: number): RevealedText {
  const prefersReducedMotion = usePrefersReducedMotion();
  // The count belongs to one text; a new text starts again from zero.
  const [progress, setProgress] = useState({ text, wordCount: 0 });
  const words = text.match(wordPattern) ?? [];
  const wordCount = progress.text === text ? progress.wordCount : 0;
  const isRevealing = !prefersReducedMotion && wordCount < words.length;

  useEffect(() => {
    if (!isRevealing) return;
    const intervalId = setInterval(() => {
      setProgress((current) => ({
        text,
        wordCount: current.text === text ? current.wordCount + 1 : 1,
      }));
    }, 1000 / wordsPerSecond);
    return () => {
      clearInterval(intervalId);
    };
  }, [isRevealing, text, wordsPerSecond]);

  return {
    revealedText: isRevealing ? words.slice(0, wordCount).join("") : text,
    isRevealing,
  };
}
