/** Appearance values are presentation-only; no diagnosis data is persisted. */
export type Appearance = "system" | "light" | "dark";
export type ResolvedAppearance = "light" | "dark";
export const APPEARANCE_STORAGE_KEY = "whyfi.appearance";

export function parseAppearance(value: unknown): Appearance {
  return value === "light" || value === "dark" ? value : "system";
}

export function resolveAppearance(appearance: Appearance, systemIsDark: boolean): ResolvedAppearance {
  return appearance === "system" ? (systemIsDark ? "dark" : "light") : appearance;
}
