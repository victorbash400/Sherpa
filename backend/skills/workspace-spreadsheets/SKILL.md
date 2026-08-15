---
name: workspace-spreadsheets
description: Read, create, append, update, and format Google Sheets with precise ranges. Use for spreadsheet data entry, table creation, calculations, formatting, and verification.
---

# Sheets workflow

1. Resolve the spreadsheet and exact sheet/range. Read the relevant range with `workspace_sheets_read_range` before editing existing data.
2. Use `workspace_sheets_create_spreadsheet` for a new workbook, `workspace_sheets_append_rows` for new records, and `workspace_sheets_update_range` for replacing known cells.
3. Use `workspace_sheets_batch_update` for structure or formatting. Keep requests scoped to the intended sheet and cells.
4. Preserve the table's headers, formulas, and column order unless the request changes them. Never overwrite a broader range merely because it is easier.
5. Read the affected range after writing and compare the returned values with the requested result.

If the target range, units, or overwrite intent is ambiguous, ask before writing. Do not substitute the Sheets website for missing API access.
