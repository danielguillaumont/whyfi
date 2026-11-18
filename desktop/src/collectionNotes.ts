function displayText(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value : undefined;
}

export function collectionNotes(entries: unknown, error: unknown) {
  const rows: { label: string; value: string }[] = [];
  if (Array.isArray(entries)) {
    for (const entry of entries) {
      if (typeof entry !== "object" || entry === null || Array.isArray(entry)) continue;
      const { check, target, message } = entry as Record<string, unknown>;
      const value = displayText(message);
      if (value === undefined) continue;
      const label = displayText(check) ?? "Check";
      const detail = displayText(target);
      rows.push({ label: detail ? `${label} \u2022 ${detail}` : label, value });
    }
  }
  return { rows, fallback: rows.length ? undefined : displayText(error) };
}
