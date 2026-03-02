---
status: awaiting_human_verify
trigger: "Quality model profile does not cause subagents to use Opus - they all inherit Sonnet from the orchestrator instead"
created: 2026-03-03T00:00:00.000Z
updated: 2026-03-03T00:02:00.000Z
---

## Current Focus

hypothesis: CONFIRMED AND FIXED.
test: All 11 agents tested across quality/balanced/budget profiles + model_overrides
expecting: N/A
next_action: Awaiting human verification that subagents now run on Opus in real workflow

## Symptoms

expected: With model_profile "quality" in .planning/config.json, key agents (gsd-phase-researcher, gsd-planner, gsd-executor, gsd-debugger) should run on Opus 4.6.
actual: All subagents run on Sonnet 4.6 (inherited from the orchestrator). The orchestrator is always Sonnet because Claude Code users start sessions on Sonnet by default.
errors: No error - silent quality degradation. User noticed because researcher output seemed lower quality.
reproduction: node "$HOME/.claude/get-shit-done/bin/gsd-tools.cjs" resolve-model gsd-phase-researcher --raw returns "inherit"
started: Has affected all phases since project start. Just discovered.

## Eliminated

## Evidence

- timestamp: 2026-03-03T00:00:30Z
  checked: resolve-model CLI output for quality-profile agents
  found: gsd-phase-researcher="inherit", gsd-planner="inherit", gsd-research-synthesizer="sonnet" (correct)
  implication: All opus-mapped agents get "inherit" instead of explicit opus

- timestamp: 2026-03-03T00:00:40Z
  checked: resolveModelInternal in core.cjs lines 354-369
  found: Line 368 converts opus to inherit. Line 360 does same for overrides.
  implication: Both profile lookup and override paths are affected

- timestamp: 2026-03-03T00:00:50Z
  checked: model-profiles.md and model-profile-resolution.md design docs
  found: Design assumed parent session runs Opus, so inherit=Opus. But Claude Code defaults to Sonnet.
  implication: The inherit approach only works if user manually switches to Opus first

- timestamp: 2026-03-03T00:00:55Z
  checked: init.cjs consumption pattern
  found: Models pass directly as model="{xxx_model}" to Task calls
  implication: Task(model="inherit") uses parent model (Sonnet). Task(model="opus") maps to current opus version.

## Resolution

root_cause: resolveModelInternal (core.cjs:360,368) converted "opus" to "inherit", assuming orchestrator is Opus. But Claude Code defaults to Sonnet, so inherit=Sonnet. The Task tool accepts "opus" directly and maps it to the current opus version.
fix: Removed the opus-to-inherit conversion in resolveModelInternal. Now returns "opus" directly for both profile lookup and override paths. Updated reference docs (model-profiles.md, model-profile-resolution.md) to reflect the new behavior.
verification: All 11 agents tested across 3 profiles (quality/balanced/budget) + model_overrides. All results match MODEL_PROFILES table exactly. gsd-phase-researcher now returns "opus" (was "inherit"). Non-opus agents unaffected.
files_changed:
  - /home/inshal-rauf/.claude/get-shit-done/bin/lib/core.cjs (resolveModelInternal: removed opus->inherit conversion)
  - /home/inshal-rauf/.claude/get-shit-done/references/model-profile-resolution.md (updated docs)
  - /home/inshal-rauf/.claude/get-shit-done/references/model-profiles.md (updated design rationale)
