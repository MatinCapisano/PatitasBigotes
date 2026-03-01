import logging

from fastapi import FastAPI
from source.routes.auth_r import router as auth_router
from source.routes.discounts_r import router as discounts_router
from source.routes.mercadopago_r import router as mercadopago_router
from source.routes.orders_r import router as orders_router
from source.routes.payments_r import router as payments_router
from source.routes.products_r import router as products_router
from source.routes.stock_reservations_r import router as stock_reservations_router
from source.routes.turns_r import router as turns_router
from source.routes.users_r import router as users_router

app = FastAPI(
    title="Sales API",
    version="0.1.0",
    description="API para página de ventas. Etapa inicial."
)
logger = logging.getLogger(__name__)
app.include_router(products_router)
app.include_router(mercadopago_router)
app.include_router(orders_router)
app.include_router(users_router)
app.include_router(auth_router)
app.include_router(turns_router)
app.include_router(discounts_router)
app.include_router(payments_router)
app.include_router(stock_reservations_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}


