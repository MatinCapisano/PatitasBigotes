import { Link } from "react-router-dom";
import { type PaymentReturnVariant, usePaymentReturnStatus } from "../features/checkout";

const CONTENT: Record<PaymentReturnVariant, { title: string; subtitle: string }> = {
  success: {
    title: "Pago aprobado",
    subtitle: "MercadoPago informo que tu pago fue aprobado. Si el estado tarda en actualizar, refresca en unos segundos."
  },
  failure: {
    title: "Pago rechazado",
    subtitle: "MercadoPago informo que el pago fue rechazado o no pudo completarse. Podes reintentar desde tu checkout."
  },
  pending: {
    title: "Pago pendiente",
    subtitle: "MercadoPago dejo el pago en estado pendiente. Te avisaremos cuando cambie el estado."
  }
};

export function PaymentReturnPage({ variant }: { variant: PaymentReturnVariant }) {
  const { location, status, loading, error, loadStatus } = usePaymentReturnStatus();
  const { title, subtitle } = CONTENT[variant];

  return (
    <section>
      <h1 className="page-title">{title}</h1>
      <p className="page-subtitle">{subtitle}</p>
      {loading && <p className="muted">Consultando estado de pago...</p>}
      {error && <p className="error">{error}</p>}
      {status && (
        <div className="card">
          <p><strong>Estado del pago:</strong> {status.status}</p>
          <p className="muted">Estado de orden: {status.order_status ?? "-"}</p>
        </div>
      )}
      {location.search && (
        <p className="muted">Parametros de retorno: {location.search}</p>
      )}
      <div className="checkout-actions">
        <button className="btn btn-small btn-ghost" type="button" onClick={() => void loadStatus()} disabled={loading}>
          Reconsultar estado
        </button>
        <Link className="btn btn-small" to="/checkout">
          Volver al checkout
        </Link>
        <Link className="btn btn-small btn-ghost" to="/home">
          Ir a tienda
        </Link>
      </div>
    </section>
  );
}
