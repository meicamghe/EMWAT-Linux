# EMWAT Linux Project Instructions

## Project Identity
This project focuses on running the Windows EMWAT application and its
GAM Virtual Printer workflow on Linux, primarily using Wine and Linux printing
infrastructure.

## Independence
- EMWAT Linux is independent from Winux and ApnaWin.
- Do not merge project repositories, histories, roadmaps or instructions.
- Winux may be consulted only when a concrete technical dependency exists.
- Keep EMWAT-specific findings and test results in this project.

## Related Working Resources
When relevant, inspect these existing resources:
- ~/EMWAT-Linux
- ~/emwat-printer-capture
- ~/emwat-dlls
- ~/gam-printer-analysis
- ~/.wine-emwat

These paths may contain important working state and evidence.
Do not recreate or replace them unnecessarily.

## Technical Continuity
- Continue from the latest verified state in the existing project.
- Do not repeat completed investigations without new evidence.
- Preserve previously successful fixes and working configurations.
- Do not reintroduce Wine versions explicitly rejected by the user.
- The currently selected target is Wine 11.
- Treat the existing Wine prefix as valuable test state; back it up before
  risky modifications.
- Preserve the real EMWAT workflow, including interactions with Word and
  returning control to the GAM application.
- Distinguish confirmed behavior from hypotheses.

## Development and Testing
- Analyze installer, service, printer driver, monitor, spooler and CUPS
  integration as separate components.
- Prefer reproducible tests and preserve logs and diagnostic evidence.
- Use parallel workstreams for independent investigations where useful.
- Coordinate changes to shared files, Wine prefix and printer configuration.

## Permissions and Safety
- Read, write, build and test project files and related resources.
- Do not delete prefixes, source data, logs or backups without approval.
- Ask before destructive system changes, package removal or operations
  outside the project scope.

## Reporting
Maintain technical findings, current blockers, completed work and test results.
Never report an unverified printer workflow as working.
