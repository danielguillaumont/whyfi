function displayText(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value : undefined;
}

function validNotes(entries: unknown) {
  if (!Array.isArray(entries)) return [];
  return entries.flatMap(entry => {
    if (typeof entry !== "object" || entry === null || Array.isArray(entry)) return [];
    const { check, target, message } = entry as Record<string, unknown>;
    const value = displayText(message);
    if (value === undefined) return [];
    const kind = displayText(check);
    const name = kind ?? "Check";
    const detail = displayText(target);
    return [{ kind, label: detail ? `${name} \u2022 ${detail}` : name, value }];
  });
}

export function collectionNotes(entries: unknown, error: unknown) {
  const rows = validNotes(entries).map(({ label, value }) => ({ label, value }));
  return { rows, fallback: rows.length ? undefined : displayText(error) };
}

type NoteSection = "device" | "local-network" | "internet" | "dns" | "unscoped";

const sectionByCheck = new Map<string, NoteSection>([
  ["route", "device"], ["route_consistency", "device"], ["local_config", "device"],
  ["gateway", "local-network"], ["wifi", "local-network"], ["internet", "internet"], ["dns", "dns"],
]);

export function evidenceCollectionNotes(entries: unknown, error: unknown) {
  const groups: Record<NoteSection,
    ReturnType<typeof validNotes>> = {
      device: [], "local-network": [], internet: [], dns: [], unscoped: [],
    };
  const notes = validNotes(entries);
  for (const note of notes) {
    const section = note.kind ? sectionByCheck.get(note.kind) : undefined;
    groups[section ?? "unscoped"].push(note);
  }
  const fallback = displayText(error);
  if (!notes.length && fallback) groups.unscoped.push({ kind: undefined, label: "Investigation", value: fallback });
  return groups;
}
