# Design

## Context

See proposal.md. SakuraPet inherits shared interaction and chat from main.py. Single click and pickup call the same bubble mechanism that supplies useful balance/import feedback. The project has no Git repository yet; GitHub account 78percent is reachable with network permission.

## Goals / Non-Goals

Goals: unify visible branding, remove only click/pickup speech code, preserve functional notifications and publish a runnable source checkout.
Non-goals: artwork changes, new persona, animation tuning, Godot integration, re-enabling V4 or changing document import/API behavior.

## Decisions

- Delete click/pickup dialogue selection and calls at their shared source; retain SpeechBubble for functional notifications. A global no-op would hide useful errors and balances.
- Compose Sakura menus directly, grouped by purpose, rather than finding a translated upstream action by its visible text. Tray reuses the same builder.
- Always use the existing PERSONA for chat. Leave its definition and rendering modules unchanged.
- Back up edited local files and hash protected assets under ignored .bootstrap before editing. Keep historical artifacts locally, exclude unpublished work and personal environment from Git; publish only runtime assets and reproducible tests/tool helpers.
- Keep all local source/assets available, including historical assets. Git exclusion is not file deletion.
- Preserve upstream LICENSE unchanged and add concise attribution. Do not claim ownership of upstream code or confer unverified rights on character artwork.
- UI skill queries had no specific native menu match; apply general concise-label guidance and native Qt grouping, with no visual theme redesign.

## Risks / Trade-offs

- Removing all bubbles would break feedback → remove only click/pickup producers and their unused text constants.
- Grouping menus can break text-based tests → check each existing callback via Qt actions and preserve feature access.
- Generated historical preview tests need local files → keep them locally, publish a dedicated reproducible test command.
- Public Git history can expose data → initialize with reviewed paths, scan staged bytes and verify ignored secrets before push.

## Migration Plan

Run interaction, chat/transport, single-instance and startup checks; compare hashes. Create public repository only after source review, then verify remote visibility and commit. Restart only the exact project instance if one is running. Rollback uses the local backup; no automatic archival or new visual acceptance claim.
