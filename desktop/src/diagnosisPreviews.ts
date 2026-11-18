import type { Diagnosis } from "./diagnosticTypes";

export const DEV_PREVIEW_DIAGNOSES: Diagnosis[] = [
  {
    code: "no_connection",
    title: "No active network connection.",
    confidence: 98,
    summary:
      "WHYFI could not find an active physical network connection on this computer.",
    evidence: [
      "No active Wi-Fi or Ethernet connection was detected.",
      "No usable IPv4 connection was available.",
      "The network investigation could not continue upstream.",
    ],
    recommendation:
      "Connect to Wi-Fi or Ethernet, then run WHYFI again.",
  },
  {
    code: "local_config_issue",
    title: "Your device has a network configuration problem.",
    confidence: 94,
    summary:
      "Your computer is connected to a network adapter, but its local IP configuration does not look usable.",
    evidence: [
      "The active adapter does not have a normal usable IPv4 configuration.",
      "A DHCP or automatic addressing problem may have occurred.",
      "The issue appears before traffic reaches your router.",
    ],
    recommendation:
      "Reconnect the adapter or renew its network configuration, then diagnose again.",
  },
  {
    code: "gateway_issue",
    title: "Your router is not responding.",
    confidence: 93,
    summary:
      "Your computer appears connected, but WHYFI cannot reliably reach the local gateway.",
    evidence: [
      "The active network adapter is available.",
      "A default gateway was discovered.",
      "Gateway reachability checks failed or showed severe packet loss.",
    ],
    recommendation:
      "Check your router connection and Wi-Fi link. Restarting or reconnecting to the router may help.",
  },
  {
    code: "internet_issue",
    title: "Your local network works, but the internet does not.",
    confidence: 92,
    summary:
      "Your computer can reach the router, but multiple independent internet targets are not responding.",
    evidence: [
      "Your local gateway is reachable.",
      "Local network communication appears healthy.",
      "Multiple public internet targets could not be reached.",
    ],
    recommendation:
      "Check your modem or ISP connection. The problem is likely beyond your local device.",
  },
  {
    code: "dns_issue",
    title: "DNS looks like the problem.",
    confidence: 91,
    summary:
      "Your internet connection appears reachable, but your configured DNS resolver is not resolving names correctly.",
    evidence: [
      "Direct internet connectivity is working.",
      "The configured DNS resolver failed its lookup.",
      "An alternate public resolver successfully answered the same request.",
    ],
    recommendation:
      "Try reconnecting to the network or switching to a working DNS resolver.",
  },
  {
    code: "wifi_issue",
    title: "Your Wi-Fi connection looks unstable.",
    confidence: 89,
    summary:
      "WHYFI found evidence that the wireless link between your computer and router is degrading the connection.",
    evidence: [
      "Wi-Fi signal quality is weak.",
      "Packet loss was observed between this computer and the local gateway.",
      "The evidence points to the local wireless connection rather than the ISP.",
    ],
    recommendation:
      "Move closer to the router, reduce interference, or try another Wi-Fi band or access point.",
  },
  {
    code: "unstable_connection",
    title: "Your connection is unstable.",
    confidence: 87,
    summary:
      "The connection is working, but WHYFI detected instability across multiple measurements.",
    evidence: [
      "Repeated network samples showed inconsistent response times.",
      "Packet loss or elevated jitter was detected.",
      "The instability was reproduced across more than one measurement.",
    ],
    recommendation:
      "Run another diagnosis after a few minutes and compare the results. Persistent instability may require router or ISP troubleshooting.",
  },
  {
    code: "unknown",
    title: "WHYFI could not isolate one clear cause.",
    confidence: 48,
    summary:
      "Some measurements look unusual, but the available evidence is not strong enough to blame one part of the connection.",
    evidence: [
      "The connection produced mixed diagnostic signals.",
      "No single failure condition had enough supporting evidence.",
      "WHYFI avoided making a low-confidence diagnosis.",
    ],
    recommendation:
      "Run the diagnosis again or use the technical details to inspect the measurements more closely.",
  },
];
