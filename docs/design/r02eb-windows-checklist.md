# Windows accessibility and display checks

Use a Windows test profile and the matching WHYFI build. Ask the tester to make and restore any OS accessibility or display changes. Use a stable connection. Do not change adapter, DNS, or routing settings to force outcomes.

## Narrator and keyboard

1. Enable Narrator from Windows Accessibility settings. Open WHYFI and verify that the native window is titled WHYFI. In scan mode, visit the Workspace navigation and main landmark. Confirm that the decorative icon is silent and that Result and Evidence are unavailable before a result.
2. Turn scan mode off for direct keyboard interaction. Tab to Start diagnosis and use Enter. Verify focus moves to “Investigating connection,” Cancel becomes available after startup, and progress is announced politely without interrupting focused content on every update.
3. Tab to Cancel and use Space. Verify focus remains on Cancel while it is unavailable. On cancellation, listen for “Investigation cancelled.” Tab to Start diagnosis and retry. Confirm the terminal heading is announced once. Where a test harness supplies a cleanup notice, verify the notice can be read.
4. After a real result, listen for the engine conclusion and the Healthy, Problem found, or Inconclusive description. Use test fixtures to cover the remaining outcome labels. Confirm that failure and timeout focus their distinct headings and expose Try again.
5. Use View evidence, then Tab through Back to result and the four section jump buttons. Activate each with Enter or Space. Verify Narrator reads the focused heading and that it is visible. In Internet, use Narrator's table navigation to verify target and metric headers for both desktop and stacked layouts. Read DNS in order through Windows DNS client, direct queries, and interface inventory.
6. Activate Back to result and verify focus returns to View evidence. Repeat in reverse with Shift+Tab. Enable a Windows contrast theme on the test profile and confirm the current location and focus are clear.

## Windows scaling and installer

1. At 100%, 150%, and 200% Windows display scale, launch the matching build and check the normal 800×600 window and a 480×560 compact window, or their closest attainable snapped sizes. Repeat with Windows text size increased. Browser device scale and root-font emulation are separate checks.
2. Confirm Start, Cancel, Run again, View evidence, and Back to result remain reachable by keyboard. At compact widths and short heights the header scrolls with the page. Check that jumping to DNS leaves its heading visible and that long IPv6 addresses and collection notes wrap and remain selectable.
3. Test MSI and NSIS separately on a clean test profile when installer testing is authorized. Launch from the installed shortcut. Verify title, icon, keyboard navigation, a real diagnosis, cancellation, immediate retry, and Result ↔ Evidence focus restoration. Restore the test profile after verification.
