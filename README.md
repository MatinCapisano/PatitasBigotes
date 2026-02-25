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

### Troubleshooting

- No llegan webhooks:
  - URL vieja en panel MP.
  - Tunnel ngrok cerrado o caido.
  - `MERCADOPAGO_NOTIFICATION_URL` no coincide con la URL publicada.
- Respuesta `401` en webhook:
  - `MERCADOPAGO_WEBHOOK_SECRET` incorrecto.
  - Se actualizo configuracion en MP y no se reviso si el secret cambio.
- URL `localhost` en panel MP:
  - Mercado Pago no puede alcanzar tu maquina desde internet.

### Nota para recruiters

- Para ver funcionalidades generales sin configurar Mercado Pago, usar flujo de pago no real (si el proyecto lo ofrece).
- Para validar pagos reales sandbox con Mercado Pago, es obligatorio completar el setup de credenciales, cuentas de prueba y webhook descrito arriba.
