import { http } from "./http";

export type ManualOrderCustomer = {
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
};

export type ManualOrderItem = {
  variant_id: number;
  quantity: number;
};

export type AdminOrderItem = {
  id: number;
  product_id: number;
  variant_id: number;
  product_name: string | null;
  variant_label: string;
  quantity: number;
  unit_price: number;
  line_total: number;
};

export type AdminOrder = {
  id: number;
  user_id: number;
  status: "draft" | "submitted" | "paid" | "cancelled";
  currency: "ARS";
  total_amount: number;
  subtotal: number;
  discount_total: number;
  items: AdminOrderItem[];
  created_at: string;
  updated_at: string;
  submitted_at: string | null;
  paid_at: string | null;
};

export type AdminPayment = {
  id: number;
  order_id: number;
  method: "bank_transfer" | "mercadopago";
  status: "pending" | "paid" | "cancelled" | "expired";
  amount: number;
  currency: "ARS";
  external_ref: string | null;
  receipt_url: string | null;
  preference_id: string | null;
  order_status?: "draft" | "submitted" | "paid" | "cancelled" | null;
  user_id?: number | null;
  created_at: string;
  paid_at: string | null;
};

export async function createManualSubmittedOrder(payload: {
  customer: ManualOrderCustomer;
  items: ManualOrderItem[];
}) {
  const response = await http.post<{ data: { order: AdminOrder } }>("/orders/manual/submitted", payload);
  return response.data.data;
}

export async function getAdminOrder(orderId: number): Promise<AdminOrder> {
  const response = await http.get<{ data: AdminOrder }>(`/admin/orders/${orderId}`);
  return response.data.data;
}

export async function listAdminOrderPayments(orderId: number): Promise<AdminPayment[]> {
  const response = await http.get<{ data: AdminPayment[] }>(`/admin/orders/${orderId}/payments`);
  return response.data.data;
}

export async function listAdminOrders(params?: {
  status?: "draft" | "submitted" | "paid" | "cancelled";
  limit?: number;
  sort_by?: "created_at" | "id";
  sort_dir?: "asc" | "desc";
}): Promise<AdminOrder[]> {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  if (params?.limit) qs.set("limit", String(params.limit));
  if (params?.sort_by) qs.set("sort_by", params.sort_by);
  if (params?.sort_dir) qs.set("sort_dir", params.sort_dir);
  const response = await http.get<{ data: AdminOrder[] }>(`/admin/orders?${qs.toString()}`);
  return response.data.data;
}

export async function listAdminPayments(params?: {
  status?: "pending" | "paid" | "cancelled" | "expired";
  limit?: number;
  sort_by?: "created_at" | "id";
  sort_dir?: "asc" | "desc";
}): Promise<AdminPayment[]> {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  if (params?.limit) qs.set("limit", String(params.limit));
  if (params?.sort_by) qs.set("sort_by", params.sort_by);
  if (params?.sort_dir) qs.set("sort_dir", params.sort_dir);
  const response = await http.get<{ data: AdminPayment[] }>(`/admin/payments?${qs.toString()}`);
  return response.data.data;
}

export async function adminMarkOrderPaid(orderId: number, paymentRef: string, paidAmount: number): Promise<AdminOrder> {
  const response = await http.post<{ data: AdminOrder }>(`/admin/orders/${orderId}/pay/manual`, {
    payment_ref: paymentRef,
    paid_amount: paidAmount
  });
  return response.data.data;
}
