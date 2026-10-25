# Validation · 2026-10-25

## Implementation

- Removed click/pickup dialogue selection, unused constants and bubble calls in shared input handlers; retained touch/pickup state transitions, drag positioning and saved coordinates.
- Chat always uses the existing Sakura PERSONA. Updated visible names, concise busy state and document feedback; removed repeated welcome/instruction text. Reference usage appears when documents are loaded.
- Sakura menu now groups documents and DeepSeek settings and retains all active controls. Tray uses the same menu builder, including live hide/reveal labels.
- README describes installation, supported controls, upstream derivation, document move behavior and transmission to DeepSeek. Original upstream MIT license is retained byte-for-byte.

## Checks

- 40 related local checks passed in 45.384 seconds: public-release interactions, configuration, local HTTP transport, startup, single-instance IPC, double click, rollback boundaries, expressions and chat identity. No real DeepSeek chat was sent this round.
- A fresh export of the Git index decoded 9 compatibility images and 11 Sakura parts, reported `key_configured: false`, and passed the README command's complete 23-test suite in 43.410 seconds. This export reused installed dependencies through a local virtual-environment junction; it was not a fresh network dependency install.
- All 185 protected files matched pre-change SHA-256 values, including image/authoring assets and the animation, face and material source files. Persona remains in the unchanged animation source. No new performance measurement or visual-animation acceptance claim.
- Initial index audit covered 66 files / 9,456,889 bytes; the pre-commit audit, including this record, covered 67 files / 9,460,021 bytes. Both found no configured secret values, credential-shaped values, private runtime paths, machine user paths or over-limit files. Real `.env`, RAG, config, caches and historical local artifacts are excluded.
- OpenSpec strict validation passed.

## Limitations and diagnostic history

- The first new drag test started at the top-left screen boundary; the existing clamp correctly prevented a negative move. The fixture was moved inside the screen. A later assertion used `x/y` instead of existing `window_x/window_y` keys; only the assertion was corrected.
- Sandbox denied atomic replacement of temporary test `.env` files. Rerunning the isolated suite with normal Windows permissions passed; no real configuration was changed by tests.
- Offscreen widget captures rendered Chinese as missing-glyph boxes. A native fixture opened with title `与三叶聊天`, but Computer Use capture returned `Computer Use app approval timed out`. Native visual appearance is therefore not marked verified. Qt interaction and label checks passed independently.
- Existing whitespace in disabled historical modules is unrelated to this change; those source files were preserved.
- No historical animation acceptance or Godot task has been changed; this change is not archived.

## Publication

Repository: <https://github.com/78percent/SakuraMitsuha_Desktop_Pet>

GitHub confirmed `PUBLIC`, default branch `main`, and initial implementation commit `55d628e1ffe00c0abca153b7baada1893cc79f86`, matching the local commit after successful push. This publication record is a subsequent documentation-only update.

The normal desktop instance restarted at 2026-10-25 14:10:31 +08:00. Parent PID 35396 and window PID 39180 were checked against the project process; window title `佐仓三叶`, responding true, stderr length zero. This confirms startup, not a completed native visual or new performance acceptance.
