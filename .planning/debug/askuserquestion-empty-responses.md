---
status: awaiting_human_verify
trigger: "Investigate why AskUserQuestion tool calls always return empty answers in this Claude Code session"
created: 2026-03-03T00:17:00Z
updated: 2026-03-03T00:35:00Z
---

## Current Focus

hypothesis: AskUserQuestion returns empty because it is being called from contexts where Claude Code auto-approves it without showing the interactive UI (acceptEdits mode + Skill-injected prompts). This is a known Claude Code bug where AskUserQuestion is treated like a permission-based tool and auto-approved, skipping the interactive UI.
test: Compare debug log patterns between working calls (with executePermissionRequestHooks) and broken calls (without)
expecting: Broken calls skip the permission/interaction prompt entirely and return instantly
next_action: Document root cause and propose workaround

## Symptoms

expected: When AskUserQuestion is called with options, user sees the UI, makes selections, submits -- and the tool result contains the selected answers in the `answers` field.
actual: The tool returns immediately with empty `answers: {}` and `annotations: {}` on every call. No matter what the user selects, nothing is captured.
errors: No error messages -- tool returns successfully with empty data. Additionally: InputValidationError when >4 questions passed (settings workflow).
reproduction: Every AskUserQuestion call in recent sessions returned empty -- /gsd:settings (7 questions -> InputValidationError, then empty), /gsd:discuss-phase 6, /gsd:discuss-phase 7
started: Intermittent -- worked on Mar 1 13:20-15:39 (main thread), broken from Mar 1 19:00 onwards (after Skills injected prompts)

## Eliminated

- hypothesis: PostToolUse hooks (gsd-context-monitor.js) cause interference
  evidence: The context-monitor hook ERRORS on every AskUserQuestion call (MODULE_NOT_FOUND for CWD-relative path) but this is a PostToolUse hook -- it fires AFTER the tool completes. The tool already returned empty BEFORE the hook ran. The hook error is unrelated noise.
  timestamp: 2026-03-03T00:25:00Z

- hypothesis: PreToolUse hooks intercept AskUserQuestion
  evidence: Debug logs show "Found 0 hook matchers in settings" for PreToolUse on AskUserQuestion consistently. No PreToolUse hooks match AskUserQuestion.
  timestamp: 2026-03-03T00:26:00Z

- hypothesis: InputValidationError from 7-question settings call corrupted session state
  evidence: The broken pattern (no executePermissionRequestHooks, instant return) appears BEFORE the InputValidationError (Mar 1 19:00 vs Mar 2 17:06). The InputValidationError is a separate issue (GSD settings.md specifies 7 questions, but AskUserQuestion max is 4).
  timestamp: 2026-03-03T00:27:00Z

## Evidence

- timestamp: 2026-03-03T00:20:00Z
  checked: Debug log ca2e64b0 -- compared working vs broken AskUserQuestion lifecycle
  found: |
    WORKING calls (68 instances) follow: PreToolUse -> executePermissionRequestHooks -> [user interaction, 5s-13min] -> PostToolUse
    BROKEN calls (16 instances) follow: PreToolUse -> PostToolUse [0-2ms gap, NO executePermissionRequestHooks]
    The executePermissionRequestHooks step IS the interactive UI. When skipped, tool returns empty instantly.
  implication: The bug is that AskUserQuestion's interactive prompt is being auto-approved/skipped

- timestamp: 2026-03-03T00:22:00Z
  checked: Permission mode at time of broken calls
  found: Session switched to `acceptEdits` mode at 13:47:04 on Mar 1. But AskUserQuestion STILL WORKED for 2+ hours after that (13:47 through 15:39). Broken calls start at 19:00.
  implication: acceptEdits mode alone does not cause the bug. Something else changes between 15:39 and 19:00.

- timestamp: 2026-03-03T00:24:00Z
  checked: Context around first broken call (line 14259, 17:17:13)
  found: This call was from a "Forked agent [prompt_suggestion]" -- a background subagent. It immediately got "AskUserQuestion tool permission denied". This is expected -- subagents can't show interactive UI.
  implication: Some broken calls are legitimately from subagents (expected behavior). But user-facing calls also broke.

- timestamp: 2026-03-03T00:26:00Z
  checked: Context around broken calls at 19:00 (lines 28265-28598)
  found: These 9 rapid-fire calls happen after `/gsd:discuss-phase 2` Skill was loaded (line 28036). The Skill injects messages into main thread. AskUserQuestion is called in main thread context BUT skips executePermissionRequestHooks.
  implication: After Skill injection, the main thread sometimes fails to show AskUserQuestion UI.

- timestamp: 2026-03-03T00:28:00Z
  checked: Known Claude Code bugs (GitHub issues)
  found: |
    Multiple open issues document this exact problem:
    - Issue #29733: AskUserQuestion completes without user input (Mar 2026)
    - Issue #12672: AskUserQuestion auto-completes with empty answers without showing UI
    - Issue #10400: Empty response when bypass permissions enabled
    - Issue #9846: Doesn't work in skill until plan mode toggled
    - Issue #10229: Returns empty results without displaying prompts
    All report the same symptom: tool returns immediately with empty answers.
  implication: This is a known, unresolved Claude Code bug affecting multiple users and versions.

- timestamp: 2026-03-03T00:29:00Z
  checked: CC version comparison
  found: |
    Working session (Feb 24): CC 2.1.50/51 -- AskUserQuestion worked even in bypassPermissions mode
    Broken session (Mar 1-2): CC 2.1.62/63 -- AskUserQuestion intermittently broken
    AskUserQuestion worked fine in early part of session (12:27-15:39) then stopped working.
  implication: Version upgrade from 2.1.50 to 2.1.62/63 may have introduced or worsened the bug.

- timestamp: 2026-03-03T00:29:30Z
  checked: GSD settings.md workflow specification
  found: The settings workflow specifies 7 questions in a single AskUserQuestion call, but the tool's hard limit is max 4 questions per call. This causes InputValidationError every time /gsd:settings is run.
  implication: The settings workflow has a separate bug (>4 questions) that needs fixing regardless.

## Resolution

root_cause: |
  **Two distinct issues:**

  1. **CLAUDE CODE BUG (external, unfixable in GSD):** AskUserQuestion tool intermittently auto-completes with empty answers without showing the interactive UI. This is a known bug in Claude Code 2.1.62/63, documented across multiple GitHub issues (#29733, #12672, #10400, #9846, #10229). The tool's executePermissionRequestHooks step (which shows the interactive UI) is sometimes skipped, causing the tool to return instantly with empty data. Triggers include: acceptEdits permission mode, skill-injected contexts, and race conditions in the TUI rendering.

  2. **GSD SETTINGS BUG (fixable):** The `/gsd:settings` workflow in `settings.md` specifies 7 questions in a single AskUserQuestion call, but the tool's hard limit is max 4 questions per call. This causes `InputValidationError: Too big: expected array to have <=4 items` every time, which then triggers the fallback empty-answer behavior.

fix: |
  For issue 1 (Claude Code bug): No fix possible in GSD codebase. Workarounds:
  - Ensure plan mode has been toggled at least once before using AskUserQuestion (issue #9846 workaround)
  - Use plain text conversation as fallback when AskUserQuestion returns empty
  - Report to Anthropic on existing issue #29733

  For issue 2 (GSD settings bug): APPLIED -- Split the 7-question settings.md workflow into 2 AskUserQuestion calls of 4 + 3 questions. Added fallback instruction for empty answers.

verification: Awaiting user confirmation that /gsd:settings no longer throws InputValidationError. The empty-answers bug is a Claude Code platform issue and cannot be verified through code changes alone.
files_changed:
  - /home/inshal-rauf/.claude/get-shit-done/workflows/settings.md
