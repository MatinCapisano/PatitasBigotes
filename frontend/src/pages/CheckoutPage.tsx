import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { formatArs, useCheckoutPage } from "../features/checkout";
import type { CheckoutPaymentMethod } from "../services/checkout-api";

export function CheckoutPage() {
  const { isLoading: authLoading, isAuthenticated } = useAuth();
  const checkout = useCheckoutPage({ authLoading, isAuthenticated });

  return (
    <section>
      <h1 className="page-title">Finalizar compra</h1>
      {authLoading && <p className="muted">Verificando sesion...</p>}
      <p className="page-subtitle">
        {authLoading
          ? "Estamos validando tu sesion antes de continuar."
          : isAuthenticated
          ? "Checkout de cuenta: se crea orden del usuario y se envia a submitted."
          : "Checkout invitado: completa tus datos para enviar la orden."}
      </p>

      {checkout.items.length === 0 ? (
        <div className="card">
          <p>Tu carrito esta vacio.</p>
          <Link className="btn btn-small" to="/home">
            Ir a tienda
          </Link>
        </div>
      ) : (
        <div className="checkout-grid">
          <div className="card">
            {checkout.items.map((item) => (
              <div key={`${item.product_id}-${item.variant_id}`} className="checkout-row">
                <div>
                  <strong>{item.product_name}</strong>
                  <p className="muted">Opcion: {item.option_label}</p>
                </div>
                <div>
                  <p>{item.quantity} x {formatArs(item.unit_price)}</p>
                </div>
              </div>
            ))}
          </div>
          <div className="card">
            <h2>Total</h2>
            <p className="checkout-total">{formatArs(checkout.total)}</p>
            <label>
              Metodo de pago
              <select className="input" value={checkout.paymentMethod} onChange={(event) => checkout.setPaymentMethod(event.target.value as CheckoutPaymentMethod)}>
                <option value="bank_transfer">Transferencia</option>
                <option value="mercadopago">MercadoPago</option>
                <option value="cash">Efectivo</option>
              </select>
            </label>
            {!authLoading && !isAuthenticated && (
              <div className="checkout-guest-grid">
                <label>
                  Nombre
                  <input className="input" value={checkout.guestFirstName} onChange={(event) => checkout.setGuestFirstName(event.target.value)} />
                </label>
                <label>
                  Apellido
                  <input className="input" value={checkout.guestLastName} onChange={(event) => checkout.setGuestLastName(event.target.value)} />
                </label>
                <label>
                  Email
                  <input className="input" type="email" value={checkout.guestEmail} onChange={(event) => checkout.setGuestEmail(event.target.value)} />
                </label>
                <label>
                  Telefono
                  <input className="input" value={checkout.guestPhone} onChange={(event) => checkout.setGuestPhone(event.target.value)} />
                </label>
              </div>
            )}
            <div className="checkout-actions">
              <button
                className="btn"
                type="button"
                onClick={() => void checkout.onFinalizeCheckout()}
                disabled={checkout.loading || authLoading}
              >
                {checkout.loading ? "Procesando..." : "Finalizar compra"}
              </button>
            </div>
            {checkout.error && <p className="error">{checkout.error}</p>}
            {checkout.success && <p className="success">{checkout.success}</p>}
          </div>
        </div>
      )}
    </section>
  );
}
