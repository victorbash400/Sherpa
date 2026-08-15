---
name: google-cloud-operations
description: Inspect and operate Google Cloud projects and resources with explicit project scoping. Use for cloud inventory, configuration, deployment, logs, and infrastructure actions.
---

# Google Cloud workflow

1. Resolve the exact project and account before querying or changing resources. When similarly named projects exist, list the candidates and disambiguate.
2. Inspect current state first with the narrowest Google Cloud tool. Record resource names, regions, and identifiers instead of relying on display labels.
3. Apply only the requested scoped action. Do not infer permission for destructive changes, broad IAM changes, or operations in adjacent projects.
4. Re-query the same resource after mutation and report the verified state.
5. If the required Cloud tool or permission is unavailable, name it explicitly. Do not use Console browser automation as a silent fallback.

For deletions, state the exact target and what remains untouched, obtain confirmation when intent is not already explicit, then verify each deleted service independently.
