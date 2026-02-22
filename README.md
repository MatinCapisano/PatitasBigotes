# PatitasBigotes

## Backend env vars

1. Copy `backend/.env.example` to `backend/.env`.
2. Replace placeholder values with your local configuration.
3. Never commit `backend/.env` (it is ignored by git).

## Initialize database tables

Run from `backend/`:

```bash
python -m source.db.init_db
```
