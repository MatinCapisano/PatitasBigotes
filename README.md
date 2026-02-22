# PatitasBigotes

## Backend env vars

1. Copy `backend/.env.example` to `backend/.env`.
2. Replace placeholder values with your local configuration.
3. Never commit `backend/.env` (it is ignored by git).
4. For Mercado Pago integration, set `MERCADOPAGO_ACCESS_TOKEN` and keep `MERCADOPAGO_ENV=sandbox` for test mode.

## Initialize database tables

Run from `backend/`:

```bash
python -m source.db.init_db
```
