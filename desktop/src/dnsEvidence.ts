export type DnsResolverEvidence = {
  interface_index: number;
  interface_alias: string;
  address_family: string;
  resolver: string;
  scope: string | null;
  primary: boolean;
  route_on_interface: boolean | null;
  provenance: string;
};

export type SystemDnsQuery = {
  success?: boolean | null;
  error?: string | null;
};

export function systemDnsSummary(query: SystemDnsQuery) {
  if (query.success === true) {
    return "Resolved. Windows may have used its cache or DNS policy.";
  }
  return [
    query.success === false ? "Lookup failed" : "Unavailable",
    typeof query.error === "string" ? query.error : null,
  ].filter(Boolean).join(" — ");
}

export function resolverEvidenceRows(items: DnsResolverEvidence[] | null | undefined) {
  if (!Array.isArray(items)) return [];
  return items.flatMap((item) => {
    if (!item || typeof item.resolver !== "string" || typeof item.interface_alias !== "string"
        || typeof item.interface_index !== "number" || !Number.isInteger(item.interface_index) || typeof item.address_family !== "string") {
      return [];
    }
    return [{
      label: `${item.interface_alias} #${item.interface_index} · ${item.resolver}`,
      value: [
        item.address_family,
        item.primary === true ? "Primary interface" : item.primary !== false ? "Interface association unavailable" : "Other interface · direct query skipped",
        item.route_on_interface === true ? "Matching interface route"
          : item.route_on_interface === false ? "No matching interface route" : "Route evidence unavailable",
        typeof item.scope === "string" ? `Scope ${item.scope}` : null,
        `Provenance: ${typeof item.provenance === "string" ? item.provenance : "unknown"}`,
      ].filter(Boolean).join(" — "),
    }];
  });
}
