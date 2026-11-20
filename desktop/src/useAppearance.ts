import { useEffect, useLayoutEffect, useState } from "react";
import { APPEARANCE_STORAGE_KEY, parseAppearance, resolveAppearance, type Appearance } from "./appearance";

const mediaQuery = "(prefers-color-scheme: dark)";

function savedAppearance(): Appearance {
  if (typeof window === "undefined") return "system";
  try { return parseAppearance(window.localStorage.getItem(APPEARANCE_STORAGE_KEY)); }
  catch { return "system"; } // Storage may be unavailable under an enterprise policy.
}

function systemPrefersDark(): boolean {
  return typeof window !== "undefined" && typeof window.matchMedia === "function"
    && window.matchMedia(mediaQuery).matches;
}

export function useAppearance() {
  const [appearance, setAppearance] = useState<Appearance>(savedAppearance);
  const [systemIsDark, setSystemIsDark] = useState(systemPrefersDark);

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return;
    const query = window.matchMedia(mediaQuery);
    const update = () => setSystemIsDark(query.matches);
    update();
    if (typeof query.addEventListener === "function") {
      query.addEventListener("change", update);
      return () => query.removeEventListener("change", update);
    }
    query.addListener(update);
    return () => query.removeListener(update);
  }, []);

  useLayoutEffect(() => {
    if (typeof document === "undefined") return;
    document.documentElement.dataset.whyfiTheme = resolveAppearance(appearance, systemIsDark);
  }, [appearance, systemIsDark]);

  function updateAppearance(next: Appearance) {
    setAppearance(next);
    try { window.localStorage.setItem(APPEARANCE_STORAGE_KEY, next); }
    catch { /* Theme still works for this session. */ }
  }

  return { appearance, updateAppearance };
}
