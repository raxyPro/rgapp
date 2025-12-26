# SQL migrations (no Alembic)

This app uses **plain SQL migration scripts** (instead of Alembic).

## How it works
- Each migration is a `.sql` file in this folder.
- Migrations are applied in filename order.
- Applied migrations are tracked in a database table: `rb_schema_migrations`.

## Apply migrations
From the project root:

```bash
python apply_sql_migrations.py
```

It will:
1. Ensure `rb_schema_migrations` exists
2. Apply any new `migrations_sql/*.sql` scripts
3. Record each applied filename + timestamp

## Naming convention
Use a sortable prefix, e.g.

- `0001_baseline.sql`
- `0002_add_chat_indexes.sql`
- `0003_add_some_table.sql`
