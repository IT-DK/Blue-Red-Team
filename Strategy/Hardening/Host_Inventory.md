# Host Inventory & Audit Log

| Hostname | IP Address | Role | Auditor | Hardened? | Audit Report Path | Notes |
|----------|------------|------|---------|-----------|-------------------|-------|
|          |            |      |         | [ ]       |                   |       |
|          |            |      |         | [ ]       |                   |       |
|          |            |      |         | [ ]       |                   |       |

## Audit Report Storage
Run the `10_hardening_core.sh` on each machine. Collect the generated text files (e.g., via scp) and store them in a local directory `evidence/` for review.

## Manual Checks
- [ ] Check `ps aux` for suspicious python/perl scripts.
- [ ] Check `ss -tulnp` for unknown listening ports (e.g., 4444, 9999).
- [ ] Check `/etc/passwd` for UID 0 users other than root.
ania 