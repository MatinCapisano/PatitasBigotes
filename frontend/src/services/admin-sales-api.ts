import { http } from "./http";
import type { AdminOrder, AdminPayment, ManualOrderItem } from "./admin-orders-api";

export type AdminSearchUser = {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  dni: string | null;
  phone: string | null;
  has_account: boolean;
};

export type AdminSalesCustomerPayload =
  | {
      mode: "existing";
      user_id: number;
    }
  | {
      mode: "new";
      first_name: string;
      last_name: string;
      email: string;
      phone: string;
      dni?: string | null;
    };

export type AdminSalesPaymentPayload = {
  method: "cash" | "bank_transfer";
  amount_paid: number;
  change_amount?: number | null;
  payment_ref?: string | null;
};

export type CreateAdminSalePayload = {
  customer: AdminSalesCustomerPayload;
  items: ManualOrderItem[];
  register_payment: boolean;
  payment?: AdminSalesPaymentPayload | null;
};

export type CreateAdminSaleResponse = {
  customer: AdminSearchUser;
  order: AdminOrder;
  payment: AdminPayment | null;
  meta: {
    customer_created: boolean;
    payment_registered: boolean;
  };
};

export async function searchAdminUsers(params: {
  email?: string;
  dni?: string;
  first_name?: string;
  last_name?: string;
  phone?: string;
  limit?: number;
}): Promise<AdminSearchUser[]> {
  const response = await http.get<{ data: AdminSearchUser[] }>("/users/search", {
    params
  });
  return response.data.data;
}

export async function createAdminSale(payload: CreateAdminSalePayload): Promise<CreateAdminSaleResponse> {
  const response = await http.post<{ data: CreateAdminSaleResponse }>("/admin/sales", payload);
  return response.data.data;
}
