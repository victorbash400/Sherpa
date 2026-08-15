---
name: workspace-documents
description: Find and organize Google Drive files and create, read, or edit Google Docs through Workspace APIs. Use for document workflows, Drive file lookup, folders, and Docs content changes.
---

# Drive and Docs workflow

1. When editing an existing item, find it with `workspace_drive_search_files`, disambiguate by name, type, owner, and modification time, then confirm its metadata with `workspace_drive_get_file`.
2. Read a Doc with `workspace_docs_read_doc` before changing it. Preserve existing content unless replacement is explicit.
3. Create with `workspace_docs_create_doc`; use `workspace_docs_append_text` only for a literal append. Use `workspace_docs_batch_update` for insertion, replacement, or formatting that needs exact indices.
4. For folders or file organization, use the Drive tools and verify the returned ID, name, parent, or trashed state.
5. Re-read changed Docs when correctness depends on content. Use the returned preview metadata so the task UI can show the artifact.

Do not use Chrome to type into Docs when the API supports the requested operation. If Docs or Drive permission is absent, identify the exact missing capability and stop that dependent step.

For a task that starts in Gmail or ends in WhatsApp, keep the document operation inside the same task and follow the other selected skills before and after this workflow.
