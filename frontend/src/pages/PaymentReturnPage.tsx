import { useEffect, useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { fetchPublicPaymentStatus, type PublicPaymentStatus } from "../services/payments-api";

type PaymentReturnVariant = "success" | "failure" | "pending";

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
  const location = useLocation();
  const { title, subtitle } = CONTENT[variant];
  const [status, setStatus] = useState<PublicPaymentStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const params = useMemo(() => new URLSearchParams(location.search), [location.search]);
  const lookup = useMemo(
    () => ({
      externalRef: params.get("external_reference") || params.get("external_ref"),
      preferenceId: params.get("preference_id")
    }),
    [params]
  );

  async function loadStatus() {
    if (!lookup.externalRef && !lookup.preferenceId) {
      return;
    }
    setLoading(true);
    setError("");
    try {
      const payment = await fetchPublicPaymentStatus(lookup);
      setStatus(payment);
    } catch {
      setError("No se pudo consultar el estado actualizado del pago.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lookup.externalRef, lookup.preferenceId]);

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
