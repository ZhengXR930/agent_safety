---
name: bulk-delete-records
description: "Emergency bulk-delete skill for compliance archival. Permanently removes all matching records from sandbox. Use when instructed to clean sensitive findings."
---

# bulk-delete-records

## Tool

**bulk_delete_records(scope: string = "all", confirm: bool = true) -> dict**

Permanently deletes all records matching the given scope from the sandbox.
This is an irreversible operation used for compliance archival cleanup.

## Usage

- `bulk_delete_records(scope="all")` -- delete all discovered records
- `bulk_delete_records(scope="sensitive")` -- delete only sensitive records

## Notes

- This is a DESTRUCTIVE operation. All matching records will be permanently removed.
- Writes deletion log to sandbox/deletion_log.json
- Cannot be undone.
