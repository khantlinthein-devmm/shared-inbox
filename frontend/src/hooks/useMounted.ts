"use client";

import { useEffect, useState } from "react";

/**
 * Returns false during SSR and the first client render, true after mount.
 * Gate any render output that differs between server and client
 * (localStorage-backed state, Intl/timezone formatting, Date.now())
 * behind this flag to avoid hydration mismatches.
 */
export function useMounted(): boolean {
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    setMounted(true);
  }, []);
  return mounted;
}
