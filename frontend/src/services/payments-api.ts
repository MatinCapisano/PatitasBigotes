import { http } from "./http";

export type PublicPaymentStatus = {
  order_status: string | null;
  status: "pending" | "paid" | "cancelled" | "expired";
  updated_at: string | null;
  paid_at: string | null;
};

type PublicPaymentStatusEnvelope = {
  data: PublicPaymentStatus;
};

export async function fetchPublicPaymentStatus(params: {
  externalRef?: string | null;
  preferenceId?: string | null;
}): Promise<PublicPaymentStatus> {
  const query = new URLSearchParams();
  if (params.externalRef) query.set("external_ref", params.externalRef);
  if (params.preferenceId) query.set("preference_id", params.preferenceId);
  const response = await http.get<PublicPaymentStatusEnvelope>(`/payments/public/status?${query.toString()}`);
  return response.data.data;
}
