---
name: workspace-presentations
description: Read, create, and edit Google Slides presentations through structured Workspace API updates. Use for slide creation, text or layout changes, and presentation inspection.
---

# Slides workflow

1. Read an existing deck with `workspace_slides_get_presentation` and identify slide and page-element object IDs before editing.
2. Create a new deck with `workspace_slides_create_presentation` only when no existing presentation is the target.
3. Use `workspace_slides_batch_update` for all edits. Build requests against verified object IDs and keep each batch coherent.
4. Preserve untouched slides and elements. Do not recreate an entire deck to change one element.
5. Read the presentation again after editing and verify the changed slide text and structure. Return its preview metadata for the task UI.

Ask when the target deck or slide is ambiguous. If Slides access is missing, report it rather than switching to browser automation.
