# PatitasBigotes

## Backend env vars

1. Copy `backend/.env.example` to `backend/.env`.
2. Replace placeholder values with your local configuration.
3. Never commit `backend/.env` (it is ignored by git).
4. For Mercado Pago integration, set `MERCADOPAGO_ACCESS_TOKEN` and keep `MERCADOPAGO_ENV=sandbox` for test mode.
5. JWT defaults for auth are `ACCESS_TOKEN_EXPIRE_MINUTES=120` and `REFRESH_TOKEN_EXPIRE_DAYS=30`.
6. Set `JWT_ISSUER` consistently between token creation and validation.
7. For auth emails, configure SMTP (`SMTP_*`) and `MAIL_FROM`.
8. Set `APP_BASE_URL` so verification/reset links point to your frontend.

## Initialize database tables

Run from `backend/`:

```bash
python -m source.db.init_db
```

## Auth email verification + password reset migration

For existing databases, apply:

```sql
\i backend/scripts/sql/2026_03_03_auth_email_verification_and_reset.sql
```

New auth endpoints:

1. `POST /auth/register`
2. `POST /auth/email/verify/request`
3. `POST /auth/email/verify/confirm`
4. `POST /auth/password/reset/request`
5. `POST /auth/password/reset/confirm`
6. `POST /auth/password/change`

Behavior:

1. Login is blocked until email verification is completed.
2. Verification/reset tokens are one-time and persisted as hashes in DB.
3. Password reset/change bumps `token_version` and invalidates refresh session.

## Guest checkout idempotency

`POST /checkout/guest` now requires header `Idempotency-Key`.

Behavior:

1. New key in scope `checkout_guest:<normalized_email>`: creates order (`201`).
2. Same key + same payload in same scope: replays original response (`201`), no new order.
3. Same key + different payload in same scope: returns `409 Conflict`.
4. Same key while the first request is still being processed: returns `409 Conflict`.

Idempotency records are stored in `idempotency_records` and expire after 24 hours.

## Stock reservations expiration job

For production-like latency, reservation expiration should run outside request paths.

Run once:

```bash
python -m source.jobs.expire_stock_reservations_job --once
```

Run periodically (default every 180 minutes):

```bash
python -m source.jobs.expire_stock_reservations_job
```

Override interval:

```bash
python -m source.jobs.expire_stock_reservations_job --interval-minutes 240
```

Or via env var:

```bash
STOCK_RESERVATIONS_JOB_INTERVAL_MINUTES=240
```

## Product price migration (product -> variants)

Catalog product endpoints now expose `min_var_price` instead of `price`.

### SQL migration

Backfill is not required because prices already live in `product_variants.price`.
To drop `products.price` in PostgreSQL:

```sql
ALTER TABLE products DROP COLUMN price;
```

For SQLite (without direct DROP COLUMN support), recreate the table:

```sql
PRAGMA foreign_keys=off;

CREATE TABLE products_new (
  id INTEGER PRIMARY KEY,
  name VARCHAR NOT NULL,
  description VARCHAR,
  category_id INTEGER NOT NULL,
  FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE RESTRICT
);

INSERT INTO products_new (id, name, description, category_id)
SELECT id, name, description, category_id
FROM products;

DROP TABLE products;
ALTER TABLE products_new RENAME TO products;

PRAGMA foreign_keys=on;
```

## Webhook inbox migration (MercadoPago idempotency)

Webhook events are now deduplicated with a DB inbox table (`webhook_events`).
Webhook signature freshness is also enforced with `x-signature ts`:
requests older than `MERCADOPAGO_WEBHOOK_MAX_AGE_SECONDS` (default 300s)
or too far in the future are rejected.

### SQL migration

```sql
CREATE TABLE webhook_events (
  id INTEGER PRIMARY KEY,
  provider VARCHAR NOT NULL,
  event_key VARCHAR NOT NULL UNIQUE,
  status VARCHAR NOT NULL DEFAULT 'processing',
  payload TEXT,
  received_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  processed_at TIMESTAMP,
  last_error TEXT,
  attempt_count INTEGER NOT NULL DEFAULT 0,
  next_retry_at TIMESTAMP,
  dead_letter_at TIMESTAMP
);

CREATE INDEX ix_webhook_events_provider ON webhook_events(provider);
CREATE UNIQUE INDEX ux_webhook_events_event_key ON webhook_events(event_key);
CREATE INDEX ix_webhook_events_provider_status_retry
  ON webhook_events(provider, status, next_retry_at);
CREATE INDEX ix_webhook_events_dead_letter_at ON webhook_events(dead_letter_at);
```

If `webhook_events` already exists, apply:

```sql
ALTER TABLE webhook_events ADD COLUMN attempt_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE webhook_events ADD COLUMN next_retry_at TIMESTAMP;
ALTER TABLE webhook_events ADD COLUMN dead_letter_at TIMESTAMP;

CREATE INDEX ix_webhook_events_provider_status_retry
  ON webhook_events(provider, status, next_retry_at);
CREATE INDEX ix_webhook_events_dead_letter_at ON webhook_events(dead_letter_at);
```

## Failed webhook reprocess job

If webhook processing fails (`webhook_events.status='failed'`), you can reprocess
those events in background without waiting for provider retries.

Run once:

```bash
python -m source.jobs.reprocess_failed_webhooks_job --once
```

Run periodically (default every 60 minutes, batch 25):

```bash
python -m source.jobs.reprocess_failed_webhooks_job
```

Dead-letter + retry policy defaults (small store profile):

1. `WEBHOOK_REPROCESS_INTERVAL_MINUTES=60`
2. `WEBHOOK_REPROCESS_BATCH_SIZE=25`
3. `WEBHOOK_REPROCESS_MAX_ATTEMPTS=4`
4. `WEBHOOK_REPROCESS_BASE_DELAY_MINUTES=30`
5. `WEBHOOK_REPROCESS_MAX_DELAY_MINUTES=720` (12h cap)

Override runtime values:

```bash
python -m source.jobs.reprocess_failed_webhooks_job --interval-minutes 120 --batch-size 100 --max-attempts 5 --base-delay-minutes 20 --max-delay-minutes 360
```

Or via env vars:

```bash
WEBHOOK_REPROCESS_INTERVAL_MINUTES=120
WEBHOOK_REPROCESS_BATCH_SIZE=100
WEBHOOK_REPROCESS_MAX_ATTEMPTS=5
WEBHOOK_REPROCESS_BASE_DELAY_MINUTES=20
WEBHOOK_REPROCESS_MAX_DELAY_MINUTES=360
```

## Auth action tokens prune job

Run once:

```bash
python -m source.jobs.prune_auth_action_tokens_job --once
```

Run periodically (default daily):

```bash
python -m source.jobs.prune_auth_action_tokens_job
```

## Stock reservations migration (orders submitted)

Stock reservations reserve inventory on `submitted`, consume on `paid`, and expire after 42 hours.
When a `submitted` reservation expires:
1. it can be reactivated only once for 12 hours (`reactivation_count=1`) if stock still exists,
2. after that second expiration (or if stock is missing), the order is cancelled.

### SQL migration

```sql
CREATE TABLE stock_reservations (
  id SERIAL PRIMARY KEY,
  order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  order_item_id INTEGER NOT NULL REFERENCES order_items(id) ON DELETE CASCADE,
  variant_id INTEGER NOT NULL REFERENCES product_variants(id) ON DELETE RESTRICT,
  quantity INTEGER NOT NULL,
  status VARCHAR NOT NULL DEFAULT 'active',
  reactivation_count INTEGER NOT NULL DEFAULT 0,
  expires_at TIMESTAMP NOT NULL,
  consumed_at TIMESTAMP NULL,
  released_at TIMESTAMP NULL,
  reason VARCHAR NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT ck_stock_reservations_quantity_positive CHECK (quantity > 0)
);

CREATE INDEX ix_stock_reservations_variant_status_expires
  ON stock_reservations(variant_id, status, expires_at);
CREATE INDEX ix_stock_reservations_order_status
  ON stock_reservations(order_id, status);
CREATE INDEX ix_stock_reservations_status_expires
  ON stock_reservations(status, expires_at);
CREATE UNIQUE INDEX uq_stock_reservation_active_per_item
  ON stock_reservations(order_item_id)
  WHERE status = 'active';
```

### Quick validation

```sql
SELECT status, COUNT(*) FROM stock_reservations GROUP BY status ORDER BY status;
```

If `stock_reservations` already exists, add the new column:

```sql
ALTER TABLE stock_reservations
ADD COLUMN reactivation_count INTEGER NOT NULL DEFAULT 0;
```

## Pagos MP en local (Uvicorn + ngrok fijo)

### Requisitos

1. Python y dependencias del backend instaladas.
2. `uvicorn` disponible en PATH (`pip install uvicorn`).
3. `ngrok` disponible en PATH (Windows: `winget install --id Ngrok.Ngrok -e`).
4. Cuenta de Mercado Pago Developers con una integracion de prueba.
5. Credenciales sandbox (`MERCADOPAGO_ACCESS_TOKEN`) y `MERCADOPAGO_WEBHOOK_SECRET`.
6. Cuentas de prueba de Mercado Pago (comprador/vendedor) para pruebas reales.
7. `ngrok` vinculado a tu cuenta (`ngrok config add-authtoken <tu_token>`).

### Configuracion inicial de `.env`

1. Copia `backend/.env.example` a `backend/.env`.
2. Completa:
   - `MERCADOPAGO_ACCESS_TOKEN=...` (de prueba/sandbox).
   - `MERCADOPAGO_WEBHOOK_SECRET=...` (de prueba/sandbox).
   - `MERCADOPAGO_ENV=sandbox`.
3. Usa la URL fija:
   - `MERCADOPAGO_NOTIFICATION_URL=https://terpenic-dampishly-reda.ngrok-free.dev/payments/webhook/mercadopago`

### Arranque local (2 terminales)

Terminal 1 (backend):

```powershell
.\backend\scripts\start-backend.ps1
```

Terminal 2 (tunnel ngrok fijo):

```powershell
.\backend\scripts\start-tunnel.ps1
```

El dominio esperado es:
`https://terpenic-dampishly-reda.ngrok-free.dev`

### Paso manual obligatorio en Mercado Pago (panel web)

Debes pegar esta URL en:

`Mercado Pago Developers > Tus integraciones > App de prueba > Webhooks/Notificaciones > URL de notificacion`

`https://terpenic-dampishly-reda.ngrok-free.dev/payments/webhook/mercadopago`

Despues de guardar la URL, verifica si Mercado Pago muestra un `webhook secret` nuevo para esa configuracion. Si cambio, actualiza tambien `MERCADOPAGO_WEBHOOK_SECRET` en `backend/.env`.

### Nota sobre dominio fijo

- Con este dominio ngrok fijo no necesitas actualizar la URL por sesion.
- Solo vuelve a cambiarla si cambias de dominio en ngrok.

### Flujo de verificacion

1. Crear pago sandbox desde la app.
2. Pagar con comprador de prueba.
3. Confirmar que el webhook llega a `POST /payments/webhook/mercadopago`.
4. Confirmar que el estado interno se actualiza (`pending` -> `paid` u otro estado esperado).
