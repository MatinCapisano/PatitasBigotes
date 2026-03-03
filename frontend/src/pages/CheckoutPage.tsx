import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { clearCart, readCart } from "../lib/cart-storage";
import {
  getMercadoPagoCheckoutUrl,
  type CheckoutPaymentMethod,
  submitAuthenticatedCheckoutFromCart,
  submitGuestCheckoutFromCart
} from "../services/checkout-api";

function formatArs(cents: number) {
  return new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
    maximumFractionDigits: 0
  }).format(cents / 100);
}

function readApiErrorMessage(apiError: unknown): string {
  if (
    typeof apiError === "object" &&
    apiError !== null &&
    "code" in apiError &&
    (apiError as { code?: unknown }).code === "ERR_NETWORK"
  ) {
    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
    return `No se pudo conectar con el backend (${apiBaseUrl}). Verifica que el servidor este levantado y que CORS/origen esten permitidos.`;
  }
  if (apiError instanceof Error && apiError.message.trim()) {
    return apiError.message.trim();
  }
  if (
    typeof apiError === "object" &&
    apiError !== null &&
    "response" in apiError &&
    typeof apiError.response === "object" &&
    apiError.response !== null &&
    "data" in apiError.response &&
    typeof apiError.response.data === "object" &&
    apiError.response.data !== null &&
    "detail" in apiError.response.data
  ) {
    const detail = (apiError.response.data as { detail: unknown }).detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail.trim();
    }
    if (Array.isArray(detail)) {
      const joined = detail
        .map((item) => {
          if (typeof item === "string") return item.trim();
          if (typeof item === "object" && item !== null && "msg" in item) {
            const msg = (item as { msg?: unknown }).msg;
            return typeof msg === "string" ? msg.trim() : "";
          }
          return "";
        })
        .filter(Boolean)
        .join(" | ");
      if (joined) return joined;
    }
    if (typeof detail === "object" && detail !== null) {
      if ("message" in detail) {
        const message = (detail as { message?: unknown }).message;
        if (typeof message === "string" && message.trim()) {
          return message.trim();
        }
      }
    }
  }
  return "No se pudo finalizar la compra.";
}

export function CheckoutPage() {
  const { isAuthenticated } = useAuth();
  const items = readCart();
  const total = items.reduce((sum, item) => sum + item.unit_price * item.quantity, 0);
  const [guestFirstName, setGuestFirstName] = useState("");
  const [guestLastName, setGuestLastName] = useState("");
  const [guestEmail, setGuestEmail] = useState("");
  const [guestPhone, setGuestPhone] = useState("");
  const [paymentMethod, setPaymentMethod] = useState<CheckoutPaymentMethod>("bank_transfer");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function onFinalizeCheckout() {
    if (items.length === 0 || loading) return;
    setLoading(true);
    setError("");
    setSuccess("");
    try {
      const result = isAuthenticated
        ? await submitAuthenticatedCheckoutFromCart(items, paymentMethod)
        : await submitGuestCheckoutFromCart(items, {
            first_name: guestFirstName.trim(),
            last_name: guestLastName.trim(),
            email: guestEmail.trim(),
            phone: guestPhone.trim()
          }, paymentMethod);
      const mercadoPagoCheckoutUrl = getMercadoPagoCheckoutUrl(result.payment);
      clearCart();
      if (paymentMethod === "mercadopago") {
        if (!mercadoPagoCheckoutUrl) {
          throw new Error("No se pudo obtener la URL de MercadoPago para continuar el pago.");
        }
        window.location.assign(mercadoPagoCheckoutUrl);
        return;
      }
      if (result.payment) {
        setSuccess(
          `Compra enviada. Orden #${result.order.id} (${result.order.status}). Pago #${result.payment.id} creado por ${result.payment.method}.`
        );
      } else {
        setSuccess(`Compra enviada. Orden #${result.order.id} en estado ${result.order.status}. Pago acordado en efectivo.`);
      }
    } catch (apiError: unknown) {
      setError(readApiErrorMessage(apiError));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section>
      <h1 className="page-title">Finalizar compra</h1>
      <p className="page-subtitle">
        {isAuthenticated
          ? "Checkout de cuenta: se crea orden del usuario y se envia a submitted."
          : "Checkout invitado: completa tus datos para enviar la orden."}
      </p>

      {items.length === 0 ? (
        <div className="card">
          <p>Tu carrito esta vacio.</p>
          <Link className="btn btn-small" to="/home">
            Ir a tienda
          </Link>
        </div>
      ) : (
        <div className="checkout-grid">
          <div className="card">
            {items.map((item) => (
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
            <p className="checkout-total">{formatArs(total)}</p>
            <label>
              Metodo de pago
              <select className="input" value={paymentMethod} onChange={(event) => setPaymentMethod(event.target.value as CheckoutPaymentMethod)}>
                <option value="bank_transfer">Transferencia</option>
                <option value="mercadopago">MercadoPago</option>
                <option value="cash">Efectivo</option>
              </select>
            </label>
            {!isAuthenticated && (
              <div className="checkout-guest-grid">
                <label>
                  Nombre
                  <input className="input" value={guestFirstName} onChange={(event) => setGuestFirstName(event.target.value)} />
                </label>
                <label>
                  Apellido
                  <input className="input" value={guestLastName} onChange={(event) => setGuestLastName(event.target.value)} />
                </label>
                <label>
                  Email
                  <input className="input" type="email" value={guestEmail} onChange={(event) => setGuestEmail(event.target.value)} />
                </label>
                <label>
                  Telefono
                  <input className="input" value={guestPhone} onChange={(event) => setGuestPhone(event.target.value)} />
                </label>
              </div>
            )}
            <div className="checkout-actions">
              <button
                className="btn"
                type="button"
                onClick={() => void onFinalizeCheckout()}
                disabled={loading}
              >
                {loading ? "Procesando..." : "Finalizar compra"}
              </button>
            </div>
            {error && <p className="error">{error}</p>}
            {success && <p className="success">{success}</p>}
          </div>
        </div>
      )}
    </section>
  );
}
