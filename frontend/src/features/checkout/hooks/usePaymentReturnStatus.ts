import { useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import { fetchPublicPaymentStatus, type PublicPaymentStatus } from "../../../services/payments-api";

export function usePaymentReturnStatus() {
  const location = useLocation();
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
  }, [lookup.externalRef, lookup.preferenceId]);

  return {
    location,
    status,
    loading,
    error,
    loadStatus
  };
}
