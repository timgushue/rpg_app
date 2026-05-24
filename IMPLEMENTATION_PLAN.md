# RPG App Stabilization Plan

## Phase 1

- Add persistent story arcs to campaigns.
- Inject the active arc and current beat into every turn prompt.
- Refresh the arc when it breaks or completes while keeping the same hero.

## Phase 2

- Replace prose-only state tracking with structured turn resolution.
- Let AI propose deltas and let Python validate and apply them.
- Persist roll data, proposed turn data, and applied deltas for debugging.

## Phase 3

- Expand classes and ancestries from a user-provided markdown source.
- Update data tables, prompt exports, and validation rules together.

## Phase 4

- Use the stabilized backend as the foundation for the Claude Design UI overhaul.
