"use client";

import { useCallback, useEffect, useState } from "react";

export type Theme = "light" | "dark";

const STORAGE_KEY = "theme";

export function useTheme() {
  const [theme, setTheme] = useState<Theme>("light");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    let initial: Theme = "light";
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY) as Theme | null;
      initial =
        stored ??
        (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    } catch {
      initial = "light";
    }
    setTheme(initial);
    document.documentElement.classList.toggle("dark", initial === "dark");
    setMounted(true);
  }, []);

  const toggle = useCallback(() => {
    setTheme((current) => {
      const next: Theme = current === "dark" ? "light" : "dark";
      document.documentElement.classList.toggle("dark", next === "dark");
      try {
        window.localStorage.setItem(STORAGE_KEY, next);
      } catch {
        /* private mode — theme just won't persist */
      }
      return next;
    });
  }, []);

  return { theme, toggle, mounted };
}
