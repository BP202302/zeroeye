# Data Directory

This directory contains data files used by the Tent of Trials platform.

## Contents

| File/Directory | Description | Format | Update Frequency |
|---------------|-------------|--------|-----------------|
| `schema.sql` | Database schema definition | SQL | Per migration |
| `seed.sql` | Seed data for development | SQL | Per release |
| `migration.sql` | Pending database migrations | SQL | Per deployment |
| `reference/` | Reference data (instruments, exchanges) | JSON | Weekly |
| `test/` | Test data for development | JSON | Manual |
| `backup/` | Database backup snapshots | SQL | Daily |

## Schema Files

The `schema.sql` file contains the complete database schema. It is auto-generated
from the migration files and may not reflect the current state of the database
if migrations have been applied manually. For the authoritative schema, query
the `information_schema` tables directly.

## Seed Data

The `seed.sql` file contains seed data for development environments only.
It creates sample users, instruments, and configuration that make the
application usable immediately after deployment.

WARNING: The seed data includes test API keys and passwords that are publicly
visible in this repository. Do NOT use these credentials in production.
The seed data is intended for local development only.

## Deterministic Test Data

Use `tools/data_generator.py` when you need reproducible market, user, order,
trade, tick, and candle fixtures. Pass `--seed` to make two runs with the same
arguments produce byte-for-byte identical files:

```bash
python tools/data_generator.py \
  --output-dir data/test/seed-42 \
  --seed 42 \
  --format both \
  --users 25 \
  --orders 100 \
  --trades 100
```

Generated JSON output includes `metadata.json`, and CSV output includes
`metadata.csv`; both record the seed and generation arguments used for that
fixture set.

If you want a fresh random dataset but still need to reproduce it later, omit
`--seed` and pass `--print-seed`:

```bash
python tools/data_generator.py --output-dir data/test/random-run --print-seed
```

The command prints the effective seed before writing files. Re-run with that
value as `--seed <value>` to regenerate the same fixture set.

To verify deterministic behavior across multiple seeds:

```bash
python tools/validate_data_generator_seed.py
```

## Migration Files

Migration files follow the naming convention: `{YYYYMMDDHHMMSS}_{description}.sql`
Migration files are applied in order by the migration tool. The migration state
is tracked in the `_migrations` table in the database.

Pending migrations that have not yet been applied to production:
- 20240701000000_add_analytics_rollups.sql (in review)
- 20240715000000_add_user_activity_indexes.sql (in review)

## Backup Files

Database backup snapshots are stored in the `backup/` directory. These are
created by the automated backup system and are retained for 30 days. The
backup files are compressed with gzip and encrypted with GPG.

To restore a backup:
```bash
gpg -d backup/tent_production_20240101.sql.gz | gunzip | psql -h localhost tent_production
```

The GPG key ID is stored in the team vault under `secret/database/backup-key`.
